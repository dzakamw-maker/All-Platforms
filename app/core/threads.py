import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import requests
from bs4 import BeautifulSoup

from app.config import DOWNLOADS_DIR, get_ffmpeg_path
from app.utils.cookies import get_cookies_path

def parse_cookies_file(cookie_path: Optional[str]) -> Dict[str, str]:
    """Membaca cookies untuk Threads dan Instagram dari file format Netscape."""
    cookies: Dict[str, str] = {}
    if not cookie_path or not os.path.exists(cookie_path):
        return cookies
    try:
        with open(cookie_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 7:
                    domain = parts[0].lower()
                    if "threads" in domain or "instagram" in domain:
                        cookies[parts[5]] = parts[6]
    except Exception:
        pass
    return cookies

def extract_nested_keys(obj: Any, target_key: str) -> List[Any]:
    """Mencari semua value dengan target_key tertentu dalam struktur JSON bersarang."""
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == target_key:
                results.append(v)
            results.extend(extract_nested_keys(v, target_key))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(extract_nested_keys(item, target_key))
    return results

def inspect_threads(url: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
    """Menganalisis link Threads (Video, Foto tunggal, atau Carousel)."""
    c_path = cookies_path or get_cookies_path()
    cookies = parse_cookies_file(c_path)

    # Strategi permintaan:
    # 1. Crawler User-Agent (Googlebot / Facebookbot) TANPA cookies pengguna (karena crawler bot tidak memakai session cookies dan Meta mengembalikan HTML utuh).
    # 2. Browser Desktop User-Agent DENGAN cookies pengguna (jika postingan privat atau memerlukan login).
    strategies = [
        {
            "headers": {
                "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            "use_cookies": False
        },
        {
            "headers": {
                "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            "use_cookies": False
        },
        {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            "use_cookies": True
        }
    ]

    resp = None
    for strat in strategies:
        try:
            s = requests.Session()
            if strat["use_cookies"] and cookies:
                s.cookies.update(cookies)
            r = s.get(url, headers=strat["headers"], timeout=15, allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 3000:
                resp = r
                break
        except Exception:
            continue

    if not resp:
        raise ValueError("Gagal mengakses tautan Threads. Pastikan tautan aktif dan postingan bersifat publik.")

    final_url = resp.url
    soup = BeautifulSoup(resp.text, "html.parser")

    og_title = soup.find("meta", property="og:title")
    title_text = og_title.get("content") if og_title else ""

    og_desc = soup.find("meta", property="og:description")
    desc_text = og_desc.get("content") if og_desc else ""

    og_image = soup.find("meta", property="og:image")
    og_img_url = og_image.get("content") if og_image else None

    og_video = soup.find("meta", property="og:video") or soup.find("meta", property="og:video:secure_url")
    og_video_url = og_video.get("content") if og_video else None

    # Resolusi Pengunggah (Uploader)
    uploader = "Threads User"
    if title_text:
        m = re.search(r"^(.*?)(?:\s*\(@([a-zA-Z0-9_.-]+)\))?\s+on\s+Threads", title_text, re.IGNORECASE)
        if m:
            name, handle = m.group(1), m.group(2)
            uploader = f"{name} (@{handle})" if handle else name
    if uploader == "Threads User":
        m_user = re.search(r"/@([a-zA-Z0-9_.-]+)", final_url)
        if m_user:
            uploader = f"@{m_user.group(1)}"

    # Resolusi Judul Postingan
    title = desc_text or title_text or "Threads Post"
    if len(title) > 80:
        title = title[:80] + "..."

    items: List[Dict[str, Any]] = []
    seen_urls = set()

    # Ekstraksi media dari tag <script> JSON di halaman
    for s in soup.find_all("script"):
        content = s.string or ""
        if not content:
            continue
        if "video_versions" in content or "image_versions2" in content or "carousel_media" in content:
            try:
                data = json.loads(content)

                # 1. Cek Carousel Media
                carousels = extract_nested_keys(data, "carousel_media")
                for car_list in carousels:
                    if isinstance(car_list, list):
                        for c_item in car_list:
                            if isinstance(c_item, dict):
                                v_vers = c_item.get("video_versions", [])
                                img_vers = c_item.get("image_versions2", {}).get("candidates", [])
                                if v_vers and isinstance(v_vers, list):
                                    v_url = v_vers[0].get("url")
                                    if v_url and v_url not in seen_urls:
                                        seen_urls.add(v_url)
                                        t_url = img_vers[0].get("url") if img_vers else og_img_url
                                        items.append({
                                            "id": str(len(items) + 1),
                                            "title": f"Video {len(items) + 1}",
                                            "type": "video",
                                            "thumbnail": t_url,
                                            "url": v_url
                                        })
                                elif img_vers and isinstance(img_vers, list):
                                    i_url = img_vers[0].get("url")
                                    if i_url and i_url not in seen_urls:
                                        seen_urls.add(i_url)
                                        items.append({
                                            "id": str(len(items) + 1),
                                            "title": f"Foto {len(items) + 1}",
                                            "type": "image",
                                            "thumbnail": i_url,
                                            "url": i_url
                                        })

                # 2. Cek Video langsung jika belum ada di carousel
                v_nodes = extract_nested_keys(data, "video_versions")
                for v_list in v_nodes:
                    if isinstance(v_list, list) and v_list:
                        best_v = v_list[0].get("url")
                        if best_v and best_v not in seen_urls:
                            seen_urls.add(best_v)
                            items.append({
                                "id": str(len(items) + 1),
                                "title": f"Video {len(items) + 1}",
                                "type": "video",
                                "thumbnail": og_img_url,
                                "url": best_v
                            })

                # 3. Cek Gambar langsung jika belum ada di carousel
                img_nodes = extract_nested_keys(data, "image_versions2")
                for img_dict in img_nodes:
                    if isinstance(img_dict, dict):
                        cands = img_dict.get("candidates", [])
                        if cands:
                            best_img = cands[0].get("url")
                            # Filter icon kecil atau avatar
                            width = cands[0].get("width", 0)
                            height = cands[0].get("height", 0)
                            if (width > 200 or height > 200 or width == 0) and best_img and best_img not in seen_urls:
                                seen_urls.add(best_img)
                                items.append({
                                    "id": str(len(items) + 1),
                                    "title": f"Foto {len(items) + 1}",
                                    "type": "image",
                                    "thumbnail": best_img,
                                    "url": best_img
                                })
            except Exception:
                continue

    # Fallback ke meta OpenGraph jika script parsing tidak menemukan media
    if not items:
        if og_video_url:
            items.append({
                "id": "1",
                "title": title[:60],
                "type": "video",
                "thumbnail": og_img_url,
                "url": og_video_url
            })
        elif og_img_url:
            items.append({
                "id": "1",
                "title": title[:60],
                "type": "image",
                "thumbnail": og_img_url,
                "url": og_img_url
            })

    if not items:
        raise ValueError("Tidak dapat menemukan media (foto atau video) pada postingan Threads ini. Pastikan postingan memuat media publik.")

    has_video = any(it["type"] == "video" for it in items)
    has_image = any(it["type"] == "image" for it in items)

    supported_formats: List[str] = []
    if has_video:
        supported_formats.extend(["mp4", "mp3"])
    if has_image:
        supported_formats.append("image")
    if not supported_formats:
        supported_formats = ["mp4", "image"]

    thumbnail = items[0]["thumbnail"] or og_img_url

    return {
        "title": title,
        "uploader": uploader,
        "thumbnail": thumbnail,
        "duration": None,
        "is_playlist": len(items) > 1,
        "item_count": len(items),
        "items": items,
        "original_url": url,
        "platform": "threads",
        "platform_name": "Threads",
        "supported_formats": supported_formats,
        "video_qualities": ["best"],
        "audio_qualities": ["320"]
    }

def download_threads_media(
    url: str,
    format_type: str = "video", # "video", "image", "audio"
    quality: str = "best",
    selected_item: Optional[Dict[str, Any]] = None,
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """Mengunduh media (video, foto, atau konversi audio MP3) dari Threads."""
    target_dir = output_dir or str(DOWNLOADS_DIR)
    os.makedirs(target_dir, exist_ok=True)

    target_item = selected_item
    # Jika item belum dipilih atau url adalah halaman postingan threads
    if not target_item or not target_item.get("url"):
        inspect_data = inspect_threads(url)
        items = inspect_data.get("items", [])
        if not items:
            raise ValueError("Tidak ada media yang dapat diunduh dari tautan Threads ini.")
        
        # Cari item yang cocok dengan format_type
        if format_type == "image":
            img_item = next((it for it in items if it.get("type") == "image"), None)
            target_item = img_item or items[0]
        else:
            vid_item = next((it for it in items if it.get("type") == "video"), None)
            target_item = vid_item or items[0]

    media_url = target_item.get("url")
    item_type = target_item.get("type", "video")
    safe_title = "".join(c for c in (target_item.get("title") or "Threads_Media") if c.isalnum() or c in " ._-").strip() or "Threads_Media"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.threads.net/"
    }

    # Kasus 1: Unduh Gambar (Foto)
    if item_type == "image" or format_type == "image":
        filename = f"threads_{safe_title}_{os.urandom(3).hex()}.jpg"
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

    # Kasus 2: Unduh Video MP4 atau Ekstrak Audio MP3
    if format_type == "audio":
        # Unduh video sementara lalu konversi ke MP3 via FFmpeg
        temp_video_name = f"threads_temp_{os.urandom(4).hex()}.mp4"
        temp_video_path = os.path.join(target_dir, temp_video_name)
        mp3_name = f"threads_{safe_title}_{os.urandom(3).hex()}.mp3"
        mp3_path = os.path.join(target_dir, mp3_name)

        resp = requests.get(media_url, headers=headers, stream=True, timeout=30)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(temp_video_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=16384):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        progress_callback({
                            "status": "downloading",
                            "percent": round((downloaded / total) * 80, 1),
                            "speed": None,
                            "eta": None
                        })

        # Konversi ke MP3 dengan FFmpeg
        ffmpeg_bin = get_ffmpeg_path() or "ffmpeg"
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", temp_video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-ab", "320k",
            mp3_path
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if progress_callback:
                progress_callback({"status": "downloading", "percent": 100, "speed": None, "eta": None})
        finally:
            if os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except Exception:
                    pass

        return {
            "success": True,
            "title": safe_title,
            "file_path": mp3_path,
            "filename": mp3_name
        }
    else:
        # Video MP4 biasa
        filename = f"threads_{safe_title}_{os.urandom(3).hex()}.mp4"
        file_path = os.path.join(target_dir, filename)

        resp = requests.get(media_url, headers=headers, stream=True, timeout=30)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(file_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=16384):
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
