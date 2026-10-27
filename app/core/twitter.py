import os
import re
import requests
import yt_dlp
import subprocess
from typing import Dict, Any, List, Optional, Callable
from app.config import DOWNLOADS_DIR, get_ffmpeg_path
from app.utils.cookies import get_cookies_path

def inspect_via_fxtwitter(url: str) -> Optional[Dict[str, Any]]:
    """Mengekstrak informasi tweet (foto/video/carousel) via FxTwitter / VxTwitter API."""
    m = re.search(r"(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/status/(\d+)", url)
    if not m:
        return None
    
    screen_name, tweet_id = m.group(1), m.group(2)
    api_endpoints = [
        f"https://api.fxtwitter.com/{screen_name}/status/{tweet_id}",
        f"https://api.vxtwitter.com/{screen_name}/status/{tweet_id}"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    data = None
    for ep in api_endpoints:
        try:
            resp = requests.get(ep, headers=headers, timeout=12)
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json and "tweet" in res_json and res_json["tweet"]:
                    data = res_json["tweet"]
                    break
        except Exception:
            continue

    if not data:
        return None

    author_obj = data.get("author") or {}
    author_name = author_obj.get("name") or screen_name
    author_handle = author_obj.get("screen_name") or screen_name
    uploader = f"{author_name} (@{author_handle})"

    text = data.get("text") or "Tweet on X"
    title = text[:80] + ("..." if len(text) > 80 else "")

    media_obj = data.get("media") or {}
    photos = media_obj.get("photos") or []
    videos = media_obj.get("videos") or []

    items: List[Dict[str, Any]] = []

    # 1. Tambahkan video jika ada
    for idx, v in enumerate(videos):
        v_url = v.get("url")
        # Jika ada variants dengan bitrate tertinggi, ambil itu
        variants = v.get("variants") or []
        best_variant = None
        best_bitrate = -1
        for var in variants:
            br = var.get("bitrate", 0) or 0
            if br > best_bitrate and var.get("url"):
                best_bitrate = br
                best_variant = var.get("url")
        final_v_url = best_variant or v_url
        if final_v_url:
            items.append({
                "id": str(len(items) + 1),
                "title": f"Video {len(items) + 1}",
                "type": "video",
                "thumbnail": v.get("thumbnail_url") or (photos[0]["url"] if photos else None),
                "url": final_v_url
            })

    # 2. Tambahkan foto jika ada
    for idx, p in enumerate(photos):
        p_url = p.get("url")
        if p_url:
            items.append({
                "id": str(len(items) + 1),
                "title": f"Foto {len(items) + 1}",
                "type": "image",
                "thumbnail": p_url,
                "url": p_url
            })

    if not items:
        return None

    has_video = any(it["type"] == "video" for it in items)
    has_image = any(it["type"] == "image" for it in items)

    supported_formats: List[str] = []
    if has_video:
        supported_formats.extend(["mp4", "mp3"])
    if has_image:
        supported_formats.append("image")
    if not supported_formats:
        supported_formats = ["image", "mp4"]

    thumbnail = items[0]["thumbnail"]

    return {
        "title": title,
        "uploader": uploader,
        "thumbnail": thumbnail,
        "duration": None,
        "is_playlist": len(items) > 1,
        "item_count": len(items),
        "items": items,
        "original_url": url,
        "platform": "twitter",
        "platform_name": "Twitter / X",
        "supported_formats": supported_formats,
        "video_qualities": ["best"],
        "audio_qualities": ["320"]
    }

class QuietLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def inspect_twitter(url: str) -> Dict[str, Any]:
    """Menganalisis link Twitter / X (Video, Foto tunggal, atau Multi-foto)."""
    cookie = get_cookies_path()

    # 1. Coba yt-dlp terlebih dahulu jika tweet berupa VIDEO
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "logger": QuietLogger(),
    }
    if cookie:
        opts["cookiefile"] = cookie

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and info.get("formats"):
                title = info.get("title") or info.get("description") or "Twitter Media"
                uploader = info.get("uploader") or info.get("creator") or "Twitter User"
                thumbnail = info.get("thumbnail")
                return {
                    "title": title[:80],
                    "uploader": uploader,
                    "thumbnail": thumbnail,
                    "duration": info.get("duration"),
                    "is_playlist": False,
                    "item_count": 1,
                    "items": [{
                        "id": info.get("id", "1"),
                        "title": title[:60],
                        "type": "video",
                        "thumbnail": thumbnail,
                        "duration": info.get("duration"),
                        "url": url
                    }],
                    "original_url": url,
                    "platform": "twitter",
                    "platform_name": "Twitter / X",
                    "supported_formats": ["mp4", "mp3"],
                    "video_qualities": ["best", "1080", "720", "480"],
                    "audio_qualities": ["320", "256", "192"]
                }
    except Exception:
        # Jika yt-dlp gagal (misal tweet berisi foto/gambar bukan video), lanjut ke FxTwitter
        pass

    # 2. Coba via FxTwitter / API tweet untuk foto atau carousel
    api_res = inspect_via_fxtwitter(url)
    if api_res:
        return api_res

    raise ValueError("Tidak dapat menemukan media (foto/video) pada tweet ini. Pastikan tweet bersifat publik dan memuat foto atau video.")

def download_twitter_media(
    url: str,
    format_type: str = "video", # "video", "image", "audio"
    quality: str = "best",
    selected_item: Optional[Dict[str, Any]] = None,
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """Mengunduh media (foto atau video) dari Twitter / X."""
    target_dir = output_dir or str(DOWNLOADS_DIR)
    os.makedirs(target_dir, exist_ok=True)

    target_item = selected_item
    if not target_item or not target_item.get("url"):
        inspect_data = inspect_twitter(url)
        items = inspect_data.get("items", [])
        if not items:
            raise ValueError("Tidak ada media yang dapat diunduh dari tweet ini.")
        
        if format_type == "image":
            img_item = next((it for it in items if it.get("type") == "image"), None)
            target_item = img_item or items[0]
        else:
            vid_item = next((it for it in items if it.get("type") == "video"), None)
            target_item = vid_item or items[0]

    media_url = target_item.get("url")
    item_type = target_item.get("type", "video")
    safe_title = "".join(c for c in (target_item.get("title") or "Twitter_Media") if c.isalnum() or c in " ._-").strip() or "Twitter_Media"

    # Kasus 1: Unduh Gambar (Foto)
    is_direct_image = (
        item_type == "image" or 
        format_type == "image" or 
        "pbs.twimg.com" in media_url or 
        any(ext in media_url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"])
    )

    if is_direct_image and format_type != "video":
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://x.com/"
        }
        filename = f"twitter_{safe_title}_{os.urandom(3).hex()}.jpg"
        file_path = os.path.join(target_dir, filename)

        resp = requests.get(media_url, headers=headers, stream=True, timeout=25)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(file_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        progress_callback({
                            "status": "downloading",
                            "percent": round((downloaded / total) * 100, 1),
                            "speed": None,
                            "eta": None
                        })

        return {
            "success": True,
            "title": safe_title,
            "file_path": file_path,
            "filename": filename
        }

    # Kasus 2: Video MP4 atau Konversi Audio MP3 via yt-dlp
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "outtmpl": os.path.join(target_dir, "twitter_%(id)s.%(ext)s"),
    }
    
    cookie = get_cookies_path()
    if cookie:
        opts["cookiefile"] = cookie

    ffmpeg_loc = get_ffmpeg_path()
    if ffmpeg_loc:
        opts["ffmpeg_location"] = ffmpeg_loc

    def hook(d):
        if progress_callback and d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            percent = (downloaded / total * 100) if total > 0 else 0
            progress_callback({
                "status": "downloading",
                "percent": round(percent, 1),
                "speed": d.get("speed"),
                "eta": d.get("eta")
            })

    opts["progress_hooks"] = [hook]

    if format_type == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ]
    else:
        opts["format"] = "best"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(media_url, download=True)
        final_filename = ydl.prepare_filename(info)
        if format_type == "audio":
            base, _ = os.path.splitext(final_filename)
            final_filename = base + ".mp3"

    return {
        "success": True,
        "title": info.get("title", "Twitter Video"),
        "file_path": final_filename,
        "filename": os.path.basename(final_filename)
    }
