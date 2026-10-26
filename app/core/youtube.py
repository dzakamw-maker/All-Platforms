import os
import yt_dlp
from typing import Dict, Any, Optional, Callable
from app.config import DOWNLOADS_DIR, get_ffmpeg_path
from app.utils.cookies import get_cookies_path

def get_base_ydl_opts(cookies_path: Optional[str] = None) -> Dict[str, Any]:
    cookie = cookies_path or get_cookies_path()
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
    }
    ffmpeg_loc = get_ffmpeg_path()
    if ffmpeg_loc:
        opts["ffmpeg_location"] = ffmpeg_loc
    if cookie:
        opts["cookiefile"] = cookie
    return opts

def inspect_youtube(url: str) -> Dict[str, Any]:
    """Mengambil metadata video atau playlist dari YouTube/YT Music."""
    opts = get_base_ydl_opts()
    opts["extract_flat"] = "in_playlist"
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
    if not info:
        raise ValueError("Gagal mengambil informasi dari YouTube.")

    is_playlist = "entries" in info and bool(info["entries"])
    items = []

    if is_playlist:
        for entry in info["entries"]:
            if entry:
                items.append({
                    "id": entry.get("id"),
                    "title": entry.get("title", "Unknown Title"),
                    "duration": entry.get("duration"),
                    "uploader": entry.get("uploader"),
                    "thumbnail": entry.get("thumbnail") or (entry.get("thumbnails", [{}])[-1].get("url") if entry.get("thumbnails") else None),
                    "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                })
        title = info.get("title", "YouTube Playlist")
        thumbnail = items[0]["thumbnail"] if items else None
    else:
        title = info.get("title", "YouTube Video")
        thumbnail = info.get("thumbnail")
        items.append({
            "id": info.get("id"),
            "title": title,
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
            "thumbnail": thumbnail,
            "url": url
        })

    return {
        "title": title,
        "uploader": info.get("uploader"),
        "thumbnail": thumbnail,
        "duration": info.get("duration"),
        "is_playlist": is_playlist,
        "item_count": len(items),
        "items": items,
        "original_url": url,
        "platform": "youtube"
    }

def download_youtube_media(
    url: str,
    format_type: str = "video",  # "video" atau "audio"
    quality: str = "1080",       # "1080", "720", "480", "best" untuk video; "320", "256", "192" untuk audio
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """Mengunduh video atau audio dari YouTube."""
    target_dir = output_dir or str(DOWNLOADS_DIR)
    opts = get_base_ydl_opts()
    opts["outtmpl"] = os.path.join(target_dir, "%(title).150B [%(id)s].%(ext)s")
    
    def internal_hook(d):
        if progress_callback and d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            percent = (downloaded / total * 100) if total > 0 else 0
            progress_callback({
                "status": "downloading",
                "percent": round(percent, 1),
                "speed": d.get("speed"),
                "eta": d.get("eta"),
                "filename": d.get("filename")
            })
        elif progress_callback and d.get("status") == "finished":
            progress_callback({
                "status": "processing",
                "percent": 100,
                "filename": d.get("filename")
            })

    opts["progress_hooks"] = [internal_hook]

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
            },
            {
                "key": "EmbedThumbnail",
                "already_have_thumbnail": False
            }
        ]
        opts["writethumbnail"] = True
    else:
        # Video MP4 (Prioritaskan codec H.264/AVC agar kompatibel dengan Windows Media Player)
        opts["format_sort"] = ["vcodec:h264", "res", "acodec:m4a"]
        if quality == "best":
            opts["format"] = "bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        else:
            opts["format"] = f"bestvideo[height<={quality}][vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best"
        opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Ambil nama file hasil
        final_filename = ydl.prepare_filename(info)
        if format_type == "audio":
            base, _ = os.path.splitext(final_filename)
            final_filename = base + ".mp3"
        elif not final_filename.endswith(".mp4"):
            base, _ = os.path.splitext(final_filename)
            final_filename = base + ".mp4"

    return {
        "success": True,
        "title": info.get("title"),
        "file_path": final_filename,
        "filename": os.path.basename(final_filename)
    }
