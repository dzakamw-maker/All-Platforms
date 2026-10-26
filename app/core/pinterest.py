import os
import re
import json
import requests
import yt_dlp
from typing import Dict, Any, List, Optional, Callable
from bs4 import BeautifulSoup
from app.config import DOWNLOADS_DIR, get_ffmpeg_path
from app.utils.cookies import get_cookies_path

def inspect_via_gallery_dl(url: str, cookies_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Mengekstrak gambar atau video Pinterest menggunakan gallery-dl."""
    try:
        from gallery_dl import extractor, config
        from gallery_dl.extractor.message import Message

        if cookies_path:
            config.set(("extractor", "pinterest"), "cookies", cookies_path)

        extr = extractor.find(url)
        if not extr:
            return None

        items: List[Dict[str, Any]] = []
        author = "Pinterest User"
        title = "Pinterest Pin"

        for msg in extr:
            if msg[0] == Message.Directory:
                meta = msg[2] if len(msg) > 2 and isinstance(msg[2], dict) else {}
                author = meta.get("user", {}).get("username") or meta.get("username") or author
                title = meta.get("description") or meta.get("title") or title
            elif msg[0] == Message.Url:
                m_url = msg[1]
                m_info = msg[2] if len(msg) > 2 and isinstance(msg[2], dict) else {}
                ext = (m_info.get("extension") or "").lower()
                is_video = ext in ["mp4", "webm", "mov"]
                items.append({
                    "id": str(len(items) + 1),
                    "title": f"Media {len(items) + 1}",
                    "type": "video" if is_video else "image",
                    "thumbnail": m_url,
                    "url": m_url
                })

        if items:
            return {
                "title": title[:80] if title else "Pinterest Pin",
                "uploader": author,
                "thumbnail": items[0]["thumbnail"],
                "duration": None,
                "is_playlist": len(items) > 1,
                "item_count": len(items),
                "items": items,
                "original_url": url,
                "platform": "pinterest",
                "platform_name": "Pinterest",
                "supported_formats": ["image"] if all(it["type"] == "image" for it in items) else ["image", "mp4"]
            }
    except Exception:
        pass
    return None

def inspect_via_web(url: str, cookies_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fallback mengekstrak info gambar/video Pinterest via OpenGraph / HTML scraping."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Referer": "https://www.pinterest.com/"
    }
    cookie_dict = {}
    if cookies_path and os.path.exists(cookies_path):
        try:
            with open(cookies_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#") or not line.strip():
                        continue
                    parts = line.strip().split("\t")
                    if len(parts) >= 7 and "pinterest" in parts[0]:
                        cookie_dict[parts[5]] = parts[6]
        except Exception:
            pass

    try:
        clean_url = url.replace("id.pinterest.com", "www.pinterest.com")
        resp = requests.get(clean_url, headers=headers, cookies=cookie_dict, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Cek og:title
            og_title = soup.find("meta", property="og:title")
            title = og_title.get("content") if og_title else "Pinterest Pin"
            
            # Cek og:description
            og_desc = soup.find("meta", property="og:description")
            description = og_desc.get("content") if og_desc else ""
            if description and title == "Pinterest Pin":
                title = description[:80]
                
            # Cek og:video (jika ada video)
            og_video = soup.find("meta", property="og:video")
            video_url = og_video.get("content") if og_video else None
            
            # Cek og:image
            og_img = soup.find("meta", property="og:image")
            img_url = og_img.get("content") if og_img else None
            
            # Coba cari JSON-LD
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "{}")
                    if isinstance(data, dict):
                        if data.get("name") and title == "Pinterest Pin":
                            title = data.get("name")
                        if data.get("image") and not img_url:
                            img_url = data.get("image")
                        if data.get("contentUrl") and not video_url:
                            video_url = data.get("contentUrl")
                except Exception:
                    continue

            # Jika img_url ada resolusi rendah/menengah, ganti ke /originals/
            if img_url:
                high_res_img = re.sub(r"/(?:236x|474x|564x|736x)/", "/originals/", img_url)
            else:
                high_res_img = None

            items = []
            if video_url:
                items.append({
                    "id": "1",
                    "title": title[:60],
                    "type": "video",
                    "thumbnail": high_res_img or img_url,
                    "url": video_url
                })
            elif high_res_img or img_url:
                final_img = high_res_img or img_url
                items.append({
                    "id": "1",
                    "title": title[:60],
                    "type": "image",
                    "thumbnail": final_img,
                    "url": final_img
                })

            if items:
                return {
                    "title": title[:80] if title else "Pinterest Pin",
                    "uploader": "Pinterest",
                    "thumbnail": items[0]["thumbnail"],
                    "duration": None,
                    "is_playlist": False,
                    "item_count": len(items),
                    "items": items,
                    "original_url": url,
                    "platform": "pinterest",
                    "platform_name": "Pinterest",
                    "supported_formats": ["mp4"] if video_url else ["image"]
                }
    except Exception:
        pass
    return None

def inspect_pinterest(url: str) -> Dict[str, Any]:
    """Menganalisis link Pinterest (Video, Foto, Carousel)."""
    cookie = get_cookies_path()

    # 1. Coba yt-dlp terlebih dahulu (jika pin tersebut adalah VIDEO)
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
    }
    if cookie:
        opts["cookiefile"] = cookie

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and info.get("formats"):
                title = info.get("title") or info.get("description") or "Pinterest Video"
                uploader = info.get("uploader") or "Pinterest User"
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
                    "platform": "pinterest",
                    "platform_name": "Pinterest",
                    "supported_formats": ["mp4", "mp3"]
                }
    except Exception:
        pass

    # 2. Jika yt-dlp gagal (umumnya karena Pin berupa FOTO/GAMBAR), coba via gallery-dl
    gdl_res = inspect_via_gallery_dl(url, cookie)
    if gdl_res:
        return gdl_res

    # 3. Fallback ke Web Scraping / OpenGraph
    web_res = inspect_via_web(url, cookie)
    if web_res:
        return web_res

    raise ValueError(
        "Gagal mengambil media dari Pinterest. Pastikan tautan dapat diakses atau periksa kembali link pin tersebut."
    )

def download_pinterest_media(
    url: str,
    format_type: str = "image", # "image", "video", "audio"
    quality: str = "best",
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """Mengunduh media dari Pinterest."""
    target_dir = output_dir or str(DOWNLOADS_DIR)

    # Jika URL adalah halaman Pinterest, coba inspect untuk mendapatkan direct URL
    if "pinterest.com/pin/" in url or "pin.it" in url:
        inspect_data = inspect_pinterest(url)
        if inspect_data.get("items"):
            item = inspect_data["items"][0]
            if item.get("type") == "image":
                format_type = "image"
            target_url = item.get("url") or url
        else:
            target_url = url
    else:
        target_url = url

    # Unduh Gambar Langsung (Direct Image)
    is_image = (
        format_type == "image" or
        "pinimg.com" in target_url or
        any(ext in target_url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])
    )

    if is_image and format_type != "video":
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.pinterest.com/"
        }
        resp = requests.get(target_url, stream=True, timeout=20, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Gagal mengunduh gambar Pinterest (HTTP {resp.status_code}).")

        ext = "jpg"
        content_type = resp.headers.get("content-type", "")
        if "png" in content_type:
            ext = "png"
        elif "webp" in content_type:
            ext = "webp"
        elif "gif" in content_type:
            ext = "gif"

        filename = f"pinterest_{os.urandom(4).hex()}.{ext}"
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

    # Jika Video / Audio (gunakan yt-dlp)
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "outtmpl": os.path.join(target_dir, "pinterest_%(id)s.%(ext)s"),
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
        info = ydl.extract_info(target_url, download=True)
        final_filename = ydl.prepare_filename(info)
        if format_type == "audio":
            base, _ = os.path.splitext(final_filename)
            final_filename = base + ".mp3"

    return {
        "success": True,
        "title": info.get("title", "Pinterest Video"),
        "file_path": final_filename,
        "filename": os.path.basename(final_filename)
    }
