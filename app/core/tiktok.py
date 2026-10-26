import os
import requests
import yt_dlp
from typing import Dict, Any, List, Optional, Callable
from app.config import DOWNLOADS_DIR, get_ffmpeg_path
from app.utils.cookies import get_cookies_path

def inspect_tiktok(url: str) -> Dict[str, Any]:
    """Menganalisis link TikTok (Video atau Slide Foto)."""
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
    }
    cookie = get_cookies_path()
    if cookie:
        opts["cookiefile"] = cookie

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("Gagal mengambil informasi dari TikTok.")

    title = info.get("title") or info.get("description") or "TikTok Post"
    uploader = info.get("uploader") or info.get("creator") or "TikTok Creator"
    thumbnail = info.get("thumbnail")

    # Cek apakah berupa slide foto
    entries = info.get("entries")
    thumbnails = info.get("thumbnails", [])
    
    # Deteksi carousel / photo post
    is_photo_slide = "/photo/" in url or info.get("_type") == "playlist" or (entries is not None and len(entries) > 0)
    items: List[Dict[str, Any]] = []

    if is_photo_slide and entries:
        for idx, entry in enumerate(entries):
            img_url = entry.get("url") or entry.get("thumbnail")
            items.append({
                "id": str(idx + 1),
                "title": f"Slide {idx + 1}",
                "type": "image",
                "thumbnail": img_url,
                "url": img_url
            })
    elif thumbnails and len(thumbnails) > 2 and "/photo/" in url:
        for idx, t in enumerate(thumbnails):
            img_url = t.get("url")
            if img_url:
                items.append({
                    "id": str(idx + 1),
                    "title": f"Slide {idx + 1}",
                    "type": "image",
                    "thumbnail": img_url,
                    "url": img_url
                })
    else:
        # Single Video
        items.append({
            "id": info.get("id", "video"),
            "title": title,
            "type": "video",
            "duration": info.get("duration"),
            "uploader": uploader,
            "thumbnail": thumbnail,
            "url": url
        })

    return {
        "title": title,
        "uploader": uploader,
        "thumbnail": thumbnail,
        "duration": info.get("duration"),
        "is_playlist": len(items) > 1,
        "item_count": len(items),
        "items": items,
        "original_url": url,
        "platform": "tiktok"
    }

def download_tiktok_media(
    url: str,
    format_type: str = "video", # "video", "audio", atau "image"
    quality: str = "best",
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """Mengunduh video TikTok tanpa watermark atau audio MP3."""
    target_dir = output_dir or str(DOWNLOADS_DIR)
    
    # Jika format_type adalah direct image
    if format_type == "image":
        resp = requests.get(url, stream=True, timeout=15)
        safe_id = "".join(c for c in url[-20:] if c.isalnum())
        filename = f"tiktok_image_{safe_id}.jpg"
        file_path = os.path.join(target_dir, filename)
        with open(file_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return {
            "success": True,
            "title": filename,
            "file_path": file_path,
            "filename": filename
        }

    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "outtmpl": os.path.join(target_dir, "tiktok_%(id)s.%(ext)s"),
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
        opts["format"] = "best[ext=mp4]/best"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        final_filename = ydl.prepare_filename(info)
        if format_type == "audio":
            base, _ = os.path.splitext(final_filename)
            final_filename = base + ".mp3"

    return {
        "success": True,
        "title": info.get("title", "TikTok Media"),
        "file_path": final_filename,
        "filename": os.path.basename(final_filename)
    }
