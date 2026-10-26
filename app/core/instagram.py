import os
import re
import requests
import yt_dlp
from typing import Dict, Any, List, Optional, Callable
from bs4 import BeautifulSoup
from app.config import DOWNLOADS_DIR, get_ffmpeg_path
from app.utils.cookies import get_cookies_path

def inspect_via_gallery_dl(url: str, cookies_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Mengekstrak gambar atau carousel Instagram menggunakan gallery-dl."""
    try:
        from gallery_dl import extractor, config
        from gallery_dl.extractor.message import Message

        if cookies_path:
            config.set(("extractor", "instagram"), "cookies", cookies_path)

        extr = extractor.find(url)
        if not extr:
            return None

        items: List[Dict[str, Any]] = []
        author = "Instagram User"
        title = "Instagram Media"

        for msg in extr:
            if msg[0] == Message.Directory:
                meta = msg[2] if len(msg) > 2 and isinstance(msg[2], dict) else {}
                author = meta.get("username") or meta.get("user", {}).get("username") or author
                title = meta.get("description") or meta.get("caption") or title
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
                "title": title[:80] if title else "Instagram Post",
                "uploader": author,
                "thumbnail": items[0]["thumbnail"],
                "duration": None,
                "is_playlist": len(items) > 1,
                "item_count": len(items),
                "items": items,
                "original_url": url,
                "platform": "instagram"
            }
    except Exception:
        pass
    return None

def inspect_via_embed(url: str) -> Optional[Dict[str, Any]]:
    """Fallback mengekstrak info gambar dari halaman public embed Instagram."""
    shortcode_match = re.search(r"instagram\.com/(?:p|reel|reels|tv)/([a-zA-Z0-9_-]+)", url)
    if not shortcode_match:
        return None
    shortcode = shortcode_match.group(1)
    embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.instagram.com/"
    }
    try:
        resp = requests.get(embed_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            img_el = soup.find("img", class_="EmbeddedMediaImage")
            img_src = img_el.get("src") if img_el else None
            
            caption_el = soup.find("div", class_="Caption")
            caption = caption_el.get_text(strip=True) if caption_el else f"Instagram Post {shortcode}"
            
            username_el = soup.find("a", class_="EmbeddedUsername") or soup.find("span", class_="Username")
            username = username_el.get_text(strip=True) if username_el else "Instagram User"

            if img_src:
                items = [{
                    "id": "1",
                    "title": caption[:60] if caption else "Instagram Photo",
                    "type": "image",
                    "thumbnail": img_src,
                    "url": img_src
                }]
                return {
                    "title": caption[:80] if caption else "Instagram Post",
                    "uploader": username,
                    "thumbnail": img_src,
                    "duration": None,
                    "is_playlist": False,
                    "item_count": 1,
                    "items": items,
                    "original_url": url,
                    "platform": "instagram"
                }
    except Exception:
        pass
    return None

def inspect_instagram(url: str) -> Dict[str, Any]:
    """Menganalisis URL Instagram (Post, Carousel, Reel, Story)."""
    cookie = get_cookies_path()

    # 1. Coba via yt-dlp terlebih dahulu (sangat bagus untuk Video Reels & IGTV)
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "extract_flat": "in_playlist"
    }
    if cookie:
        opts["cookiefile"] = cookie

    yt_error_msg = ""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                title = info.get("title") or info.get("description") or "Instagram Media"
                uploader = info.get("uploader") or info.get("channel") or "Instagram User"
                thumbnail = info.get("thumbnail")
                entries = info.get("entries")
                items: List[Dict[str, Any]] = []

                if entries and len(entries) > 0:
                    for idx, entry in enumerate(entries):
                        e_thumb = entry.get("thumbnail") or entry.get("url")
                        e_type = "video" if entry.get("vcodec") != "none" and entry.get("ext") in ["mp4", "webm"] else "image"
                        items.append({
                            "id": str(idx + 1),
                            "title": f"Media {idx + 1}",
                            "type": e_type,
                            "thumbnail": e_thumb,
                            "url": entry.get("url") or url
                        })
                else:
                    is_video = info.get("vcodec") != "none" or "/reel/" in url or "/reels/" in url
                    items.append({
                        "id": info.get("id", "1"),
                        "title": title[:60] if title else "Instagram Media",
                        "type": "video" if is_video else "image",
                        "thumbnail": thumbnail,
                        "duration": info.get("duration"),
                        "url": url
                    })

                return {
                    "title": title[:80] if title else "Instagram Post",
                    "uploader": uploader,
                    "thumbnail": thumbnail or (items[0]["thumbnail"] if items else None),
                    "duration": info.get("duration"),
                    "is_playlist": len(items) > 1,
                    "item_count": len(items),
                    "items": items,
                    "original_url": url,
                    "platform": "instagram"
                }
    except Exception as e:
        yt_error_msg = str(e)

    # 2. Jika yt-dlp gagal (misal "No video formats found" pada postingan FOTO / Carousel), coba gallery-dl
    gdl_res = inspect_via_gallery_dl(url, cookie)
    if gdl_res:
        return gdl_res

    # 3. Coba fallback ke halaman Public Embed Instagram
    embed_res = inspect_via_embed(url)
    if embed_res:
        return embed_res

    # 4. Jika semua cara gagal
    if "No video formats found" in yt_error_msg:
        raise ValueError(
            "Postingan Instagram ini berupa Foto/Carousel dan dibatasi oleh Instagram. "
            "Silakan gunakan menu 'Pengaturan Cookies' di pojok kanan atas, lalu simpan cookies login Instagram Anda."
        )
    elif "login" in yt_error_msg.lower() or "redirect" in yt_error_msg.lower():
        raise ValueError(
            "Akun atau postingan Instagram ini bersifat privat / dibatasi login. "
            "Silakan buka menu 'Pengaturan Cookies' di pojok kanan atas untuk memasukkan cookies Instagram Anda."
        )
    else:
        raise ValueError(
            "Gagal mengambil informasi dari Instagram. Pastikan tautan publik atau pasang cookies di menu Pengaturan Cookies jika dibatasi."
        )

def download_instagram_media(
    url: str,
    format_type: str = "video", # "video", "image", "audio"
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """Mengunduh media dari Instagram."""
    target_dir = output_dir or str(DOWNLOADS_DIR)

    # Jika URL yang masuk adalah URL halaman postingan Instagram (bukan CDN gambar langsung)
    if "instagram.com/p/" in url or "instagram.com/reel/" in url or "instagram.com/reels/" in url:
        inspect_data = inspect_instagram(url)
        if inspect_data.get("items"):
            url = inspect_data["items"][0].get("url") or url

    # Jika target adalah direct image URL (dari gallery-dl, embed, atau cdn)
    is_direct_image = (
        "cdninstagram.com" in url or 
        "fbcdn.net" in url or 
        any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"])
    )
    if is_direct_image and format_type != "video":
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.instagram.com/"
        }
        resp = requests.get(url, stream=True, timeout=20, headers=headers)
        
        # Validasi: Jika Instagram merespons dengan HTML login/error
        content_type = resp.headers.get("content-type", "").lower()
        if "text/html" in content_type:
            raise ValueError(
                "Gagal mengunduh gambar: Instagram mengembalikan halaman login/HTML web, bukan file gambar. "
                "Pastikan Anda telah memasukkan cookies Instagram yang valid di Pengaturan Cookies."
            )

        filename = f"instagram_{os.urandom(4).hex()}.jpg"
        file_path = os.path.join(target_dir, filename)
        with open(file_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Periksa isi byte awal file untuk memastikan benar-benar gambar
        with open(file_path, "rb") as f:
            first_bytes = f.read(30)
            if b"<!DOCTYPE" in first_bytes or b"<html" in first_bytes:
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                raise ValueError(
                    "Instagram memblokir unduhan dan mengembalikan halaman login web HTML. "
                    "Silakan gunakan cookies Instagram Anda di Pengaturan Cookies."
                )

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
        "outtmpl": os.path.join(target_dir, "instagram_%(id)s.%(ext)s"),
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
        info = ydl.extract_info(url, download=True)
        final_filename = ydl.prepare_filename(info)
        if format_type == "audio":
            base, _ = os.path.splitext(final_filename)
            final_filename = base + ".mp3"

    return {
        "success": True,
        "title": info.get("title", "Instagram Media"),
        "file_path": final_filename,
        "filename": os.path.basename(final_filename)
    }
