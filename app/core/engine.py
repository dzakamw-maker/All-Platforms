import os
import uuid
from typing import Dict, Any, List, Optional, Callable
from app.config import DOWNLOADS_DIR
from app.core.detector import detect_platform, Platform, MediaType
from app.core.youtube import inspect_youtube, download_youtube_media
from app.core.spotify import inspect_spotify, download_spotify_track
from app.core.tiktok import inspect_tiktok, download_tiktok_media
from app.core.instagram import inspect_instagram, download_instagram_media
from app.core.pinterest import inspect_pinterest, download_pinterest_media
from app.core.generic import inspect_generic, download_generic_media
from app.core.zipper import create_zip_archive

def inspect_url(url: str) -> Dict[str, Any]:
    """Mendeteksi dan menganalisis metadata URL dari platform manapun."""
    detection = detect_platform(url)
    platform = detection["platform"]

    try:
        if platform in [Platform.YOUTUBE, Platform.YT_MUSIC]:
            data = inspect_youtube(url)
            data["platform_name"] = detection["name"]
            data["supported_formats"] = ["mp4", "mp3"]
            data["video_qualities"] = ["best", "1080", "720", "480"]
            data["audio_qualities"] = ["320", "256", "192"]
            return data

        elif platform == Platform.SPOTIFY:
            data = inspect_spotify(url)
            data["platform_name"] = "Spotify"
            data["supported_formats"] = ["mp3"]
            data["audio_qualities"] = ["320", "256", "192"]
            return data

        elif platform == Platform.TIKTOK:
            data = inspect_tiktok(url)
            data["platform_name"] = "TikTok"
            data["supported_formats"] = ["mp4", "mp3", "image"]
            data["video_qualities"] = ["best"]
            data["audio_qualities"] = ["320"]
            return data

        elif platform == Platform.INSTAGRAM:
            data = inspect_instagram(url)
            data["platform_name"] = "Instagram"
            data["supported_formats"] = ["mp4", "image", "mp3"]
            data["video_qualities"] = ["best"]
            data["audio_qualities"] = ["320"]
            return data

        elif platform == Platform.PINTEREST:
            data = inspect_pinterest(url)
            data["platform_name"] = "Pinterest"
            return data

        else:
            data = inspect_generic(url)
            data["platform_name"] = detection["name"]
            data["supported_formats"] = ["mp4", "mp3"]
            data["video_qualities"] = ["best", "1080", "720"]
            data["audio_qualities"] = ["320", "256", "192"]
            return data

    except Exception as e:
        # Jika inspektur khusus gagal, coba generic fallback
        try:
            fallback_data = inspect_generic(url)
            fallback_data["platform_name"] = detection["name"]
            fallback_data["supported_formats"] = ["mp4", "mp3"]
            return fallback_data
        except Exception:
            raise e

def process_download(
    url: str,
    format_type: str = "video", # "video", "audio", "image"
    quality: str = "best",
    selected_item: Optional[Dict[str, Any]] = None,
    download_all_zip: bool = False,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """Menjalankan proses download sesuai platform dan parameter yang dipilih."""
    detection = detect_platform(url)
    platform = detection["platform"]

    # 1. Kasus Spotify
    if platform == Platform.SPOTIFY:
        inspect_data = inspect_spotify(url)
        is_playlist_or_multi = inspect_data.get("is_playlist", False) or len(inspect_data.get("items", [])) > 1

        if download_all_zip or (selected_item is None and is_playlist_or_multi):
            # Ambil semua track dan unduh ke dalam folder khusus playlist
            tracks = inspect_data.get("items", [])
            downloaded_files: List[str] = []
            total = len(tracks)
            collection_title = inspect_data.get("title", "Spotify_Collection")
            safe_folder_name = "".join(c for c in collection_title if c.isalnum() or c in " ._-").strip() or "Spotify_Playlist"

            # Buat folder khusus di dalam folder downloads/
            playlist_dir = DOWNLOADS_DIR / safe_folder_name
            playlist_dir.mkdir(parents=True, exist_ok=True)

            for idx, track in enumerate(tracks):
                if progress_callback:
                    progress_callback({
                        "status": "downloading",
                        "percent": round((idx / total) * 100, 1),
                        "item_current": idx + 1,
                        "item_total": total,
                        "current_title": track.get("title")
                    })
                # Unduh langsung ke folder playlist
                res = download_spotify_track(track, quality=quality, output_dir=str(playlist_dir))
                if res.get("file_path"):
                    downloaded_files.append(res["file_path"])

            # Kemas ke ZIP dengan struktur folder playlist di dalamnya
            zip_path = create_zip_archive(
                downloaded_files,
                f"{safe_folder_name}.zip",
                folder_in_archive=safe_folder_name
            )
            return {
                "success": True,
                "title": collection_title,
                "file_path": str(zip_path),
                "filename": zip_path.name,
                "folder_name": safe_folder_name,
                "folder_path": str(playlist_dir),
                "is_zip": True
            }
        else:
            # Download single track
            track_info = selected_item
            if not track_info:
                track_info = inspect_data["items"][0] if inspect_data.get("items") else None

            if not track_info:
                raise ValueError("Informasi track Spotify tidak ditemukan.")

            return download_spotify_track(track_info, quality=quality, progress_callback=progress_callback)

    # 2. Kasus TikTok
    elif platform == Platform.TIKTOK:
        target_url = selected_item.get("url") if selected_item else url
        f_type = format_type
        if selected_item and selected_item.get("type") == "image":
            f_type = "image"
        return download_tiktok_media(target_url, format_type=f_type, quality=quality, progress_callback=progress_callback)

    # 3. Kasus Instagram
    elif platform == Platform.INSTAGRAM:
        if download_all_zip:
            inspect_data = inspect_instagram(url)
            items = inspect_data.get("items", [])
            downloaded_files = []
            for idx, it in enumerate(items):
                item_url = it.get("url") or url
                item_format = "image" if it.get("type") == "image" else "video"
                res = download_instagram_media(item_url, format_type=item_format)
                if res.get("file_path"):
                    downloaded_files.append(res["file_path"])
            
            zip_path = create_zip_archive(downloaded_files, f"Instagram_{os.urandom(4).hex()}.zip")
            return {
                "success": True,
                "title": "Instagram Media Collection",
                "file_path": str(zip_path),
                "filename": zip_path.name,
                "is_zip": True
            }
        else:
            item_info = selected_item
            if not item_info:
                inspect_data = inspect_instagram(url)
                item_info = inspect_data["items"][0] if inspect_data.get("items") else None

            target_url = item_info.get("url") if item_info else url
            f_type = format_type
            if item_info and item_info.get("type") == "image":
                f_type = "image"
            elif item_info and item_info.get("type") == "video":
                f_type = "video"
            return download_instagram_media(target_url, format_type=f_type, progress_callback=progress_callback)

    # 4. Kasus YouTube & YT Music
    elif platform in [Platform.YOUTUBE, Platform.YT_MUSIC]:
        target_url = selected_item.get("url") if selected_item else url
        return download_youtube_media(target_url, format_type=format_type, quality=quality, progress_callback=progress_callback)

    # 5. Kasus Pinterest
    elif platform == Platform.PINTEREST:
        target_url = selected_item.get("url") if selected_item else url
        f_type = format_type
        if selected_item and selected_item.get("type") == "image":
            f_type = "image"
        elif selected_item and selected_item.get("type") == "video":
            f_type = "video"
        return download_pinterest_media(target_url, format_type=f_type, quality=quality, progress_callback=progress_callback)

    # 6. Generic Fallback
    else:
        target_url = selected_item.get("url") if selected_item else url
        return download_generic_media(target_url, format_type=format_type, quality=quality, progress_callback=progress_callback)
