import os
import requests
import yt_dlp
from typing import Dict, Any, Optional, Callable
from app.config import DOWNLOADS_DIR, get_ffmpeg_path
from app.utils.cookies import get_cookies_path

def inspect_generic(url: str) -> Dict[str, Any]:
    """Menganalisis link universal menggunakan yt-dlp."""
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "extract_flat": "in_playlist"
    }
    cookie = get_cookies_path()
    if cookie:
        opts["cookiefile"] = cookie

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("Tidak dapat mengekstrak informasi media dari link tersebut.")

    title = info.get("title", "Media File")
    uploader = info.get("uploader") or info.get("channel") or info.get("creator") or "Unknown"
    thumbnail = info.get("thumbnail")
    
    entries = info.get("entries")
    items = []
    is_playlist = entries is not None and len(entries) > 1

    if is_playlist:
        for idx, entry in enumerate(entries):
            items.append({
                "id": entry.get("id") or str(idx + 1),
                "title": entry.get("title") or f"Item {idx + 1}",
                "thumbnail": entry.get("thumbnail") or thumbnail,
                "duration": entry.get("duration"),
                "url": entry.get("url") or url
            })
    else:
        items.append({
            "id": info.get("id", "1"),
            "title": title,
            "thumbnail": thumbnail,
            "duration": info.get("duration"),
            "url": url
        })

    return {
        "title": title,
        "uploader": uploader,
        "thumbnail": thumbnail,
        "duration": info.get("duration"),
        "is_playlist": is_playlist,
        "item_count": len(items),
        "items": items,
        "original_url": url,
        "platform": info.get("extractor", "generic")
    }

def download_generic_media(
    url: str,
    format_type: str = "video", # "video" atau "audio"
    quality: str = "best",
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """Mengunduh media universal dengan yt-dlp."""
    target_dir = output_dir or str(DOWNLOADS_DIR)

    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "outtmpl": os.path.join(target_dir, "%(title).150B [%(id)s].%(ext)s"),
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
        bitrate = quality if quality in ["128", "192", "256", "320"] else "320"
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": bitrate,
            },
            {
                "key": "FFmpegMetadata",
                "add_metadata": True,
            }
        ]
    else:
        opts["format_sort"] = ["vcodec:h264", "res", "acodec:m4a"]
        opts["format"] = "bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        final_filename = ydl.prepare_filename(info)
        if format_type == "audio":
            base, _ = os.path.splitext(final_filename)
            final_filename = base + ".mp3"
        elif not final_filename.endswith(".mp4"):
            base, _ = os.path.splitext(final_filename)
            final_filename = base + ".mp4"

    return {
        "success": True,
        "title": info.get("title", "Media"),
        "file_path": final_filename,
        "filename": os.path.basename(final_filename)
    }
