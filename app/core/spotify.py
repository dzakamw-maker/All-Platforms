import os
import re
import json
import urllib.parse
import requests
import yt_dlp
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from app.config import DOWNLOADS_DIR, get_ffmpeg_path
from app.core.metadata_tagger import embed_mp3_metadata

def parse_spotify_url(url: str) -> Dict[str, str]:
    """Ekstrak tipe (track, album, playlist) dan ID dari URL Spotify."""
    match = re.search(r"spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)", url)
    if match:
        return {"type": match.group(1), "id": match.group(2)}
    
    # Format uri: spotify:track:id
    uri_match = re.search(r"spotify:(track|album|playlist):([a-zA-Z0-9]+)", url)
    if uri_match:
        return {"type": uri_match.group(1), "id": uri_match.group(2)}
        
    return {"type": "unknown", "id": ""}

def get_high_res_spotify_image(cover_obj: Any, fallback: Optional[str] = None) -> Optional[str]:
    """Mengambil URL gambar beresolusi tertinggi (640x640) dari objek coverArt atau sources Spotify."""
    url = None
    if isinstance(cover_obj, str) and cover_obj.startswith("http"):
        url = cover_obj
    elif isinstance(cover_obj, dict):
        sources = cover_obj.get("sources") or cover_obj.get("images")
        if isinstance(sources, list) and sources:
            valid = [s for s in sources if isinstance(s, dict) and s.get("url")]
            if valid:
                sorted_sources = sorted(valid, key=lambda s: s.get("width") or 0, reverse=True)
                url = sorted_sources[0].get("url")
        if not url:
            url = cover_obj.get("url")

    if not url:
        url = fallback

    if not url:
        return None

    # Normalisasi URL mosaic playlist Spotify ke resolusi 640px (default oEmbed / embed sering memberikan 60px atau 300px)
    if "mosaic.scdn.co" in url:
        url = re.sub(r"mosaic\.scdn\.co/(?:60|300)/", "mosaic.scdn.co/640/", url)

    # Normalisasi CDN Spotify track/album ke resolusi 640x640
    # ab67616d00004851 (64px) / ab67616d00001e02 (300px) -> ab67616d0000b273 (640px)
    if "ab67616d00004851" in url:
        url = url.replace("ab67616d00004851", "ab67616d0000b273")
    elif "ab67616d00001e02" in url:
        url = url.replace("ab67616d00001e02", "ab67616d0000b273")

    # Normalisasi CDN Spotify custom playlist ke resolusi tinggi
    # ab67706c00004851 (64px) / ab67706c0000bebb (300px) -> ab67706c0000da84 (640px)
    if "ab67706c00004851" in url:
        url = url.replace("ab67706c00004851", "ab67706c0000da84")
    elif "ab67706c0000bebb" in url:
        url = url.replace("ab67706c0000bebb", "ab67706c0000da84")

    return url

def extract_track_id(t: Dict[str, Any]) -> str:
    """Mengekstrak Spotify Track ID dari berbagai format data Spotify (URI, ID, atau URL)."""
    # 1. Properti id langsung
    raw_id = t.get("id")
    if raw_id and len(str(raw_id)) >= 15 and not str(raw_id).isdigit():
        return str(raw_id).strip()

    # 2. Format URI spotify:track:xxxx
    uri = t.get("uri") or ""
    match = re.search(r"spotify:track:([a-zA-Z0-9]+)", str(uri))
    if match:
        return match.group(1)

    # 3. Format nested di objek 'track'
    if isinstance(t.get("track"), dict):
        trk = t["track"]
        if trk.get("id") and len(str(trk["id"])) >= 15 and not str(trk["id"]).isdigit():
            return str(trk["id"]).strip()
        if trk.get("uri"):
            m = re.search(r"spotify:track:([a-zA-Z0-9]+)", str(trk["uri"]))
            if m:
                return m.group(1)

    # 4. Format URL
    url = t.get("url") or t.get("href") or ""
    match = re.search(r"track/([a-zA-Z0-9]+)", str(url))
    if match:
        return match.group(1)

    return ""

def fetch_track_cover_by_metadata(artist: str, title: str, track_id: Optional[str] = None) -> Optional[str]:
    """Mencari cover album asli lagu dari Spotify oEmbed, iTunes Music API, atau Deezer API."""
    # Tier 1: Coba dari Spotify oEmbed jika ID lagu Spotify tersedia
    if track_id and len(track_id) >= 15 and not track_id.isdigit():
        try:
            resp = requests.get(
                f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}",
                timeout=4
            )
            if resp.status_code == 200:
                thumb = resp.json().get("thumbnail_url")
                if thumb:
                    hi_res = get_high_res_spotify_image(thumb)
                    if hi_res:
                        return hi_res
        except Exception:
            pass

    # Bersihkan judul & artis untuk pencarian (hapus teks dalam kurung seperti feat, remaster, version)
    clean_title = re.sub(r"\(.*?\)|\[.*?\]|-.*", "", title).strip() or title
    clean_artist = artist.split(",")[0].strip() or artist
    search_term = f"{clean_artist} {clean_title}".strip()

    # Tier 2: Apple Music / iTunes Search API (Resmi, cepat, tanpa API key, resolusi hingga 600x600 HD)
    try:
        itunes_url = "https://itunes.apple.com/search"
        params = {
            "term": search_term,
            "media": "music",
            "entity": "song",
            "limit": 1
        }
        resp = requests.get(itunes_url, params=params, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("resultCount", 0) > 0:
                art = data["results"][0].get("artworkUrl100")
                if art:
                    # Upgrade ke 600x600 HD
                    return art.replace("100x100bb.jpg", "600x600bb.jpg").replace("100x100bb.png", "600x600bb.png")
    except Exception:
        pass

    # Tier 3: Deezer Public API (Fallback alternatif resolusi tinggi 500x500 / 1000x1000)
    try:
        deezer_url = f"https://api.deezer.com/search?q={urllib.parse.quote(search_term)}&limit=1"
        resp = requests.get(deezer_url, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data") and len(data["data"]) > 0:
                album_info = data["data"][0].get("album", {})
                cov = album_info.get("cover_xl") or album_info.get("cover_big") or album_info.get("cover_medium")
                if cov:
                    return cov
    except Exception:
        pass

    return None

def fetch_spotify_oembed(url: str) -> Optional[Dict[str, Any]]:
    """Ambil metadata dasar lewat oEmbed resmi Spotify."""
    try:
        resp = requests.get(f"https://open.spotify.com/oembed?url={url}", timeout=8)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

def fetch_spotify_embed_data(media_type: str, spotify_id: str) -> Dict[str, Any]:
    """Mengambil metadata lengkap (termasuk track list) dari embed page Spotify."""
    embed_url = f"https://open.spotify.com/embed/{media_type}/{spotify_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(embed_url, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise ValueError(f"Gagal mengakses halaman embed Spotify (HTTP {resp.status_code})")

    soup = BeautifulSoup(resp.text, "html.parser")
    next_script = soup.find("script", id="__NEXT_DATA__")
    
    if next_script and next_script.string:
        try:
            data = json.loads(next_script.string)
            page_props = data.get("props", {}).get("pageProps", {})
            entity = (
                page_props.get("state", {}).get("data", {}).get("entity")
                or page_props.get("entity")
                or page_props.get("state", {}).get("data")
                or page_props
            )
            if isinstance(entity, dict):
                return entity
        except Exception:
            pass

    return {}

def inspect_spotify(url: str) -> Dict[str, Any]:
    """Menganalisis link Spotify (track, album, atau playlist)."""
    parsed = parse_spotify_url(url)
    media_type = parsed["type"]
    spotify_id = parsed["id"]

    if not spotify_id:
        raise ValueError("URL Spotify tidak valid.")

    oembed = fetch_spotify_oembed(url) or {}
    embed_data = fetch_spotify_embed_data(media_type, spotify_id)

    title = embed_data.get("name") or oembed.get("title") or "Spotify Media"
    # Dapatkan thumbnail resolusi tinggi (640x640)
    thumbnail = get_high_res_spotify_image(embed_data.get("coverArt"), oembed.get("thumbnail_url"))
    uploader = embed_data.get("subtitle") or oembed.get("author_name") or "Spotify"

    items: List[Dict[str, Any]] = []

    if media_type == "track":
        artists = [a.get("name") for a in embed_data.get("artists", [])]
        artist_str = ", ".join(artists) if artists else uploader
        items.append({
            "id": spotify_id,
            "title": title,
            "artist": artist_str,
            "album": embed_data.get("album", {}).get("name") or title,
            "thumbnail": thumbnail,
            "duration": embed_data.get("duration"),
            "url": url,
            "query": f"{artist_str} - {title} audio"
        })
        is_playlist = False
    else:
        # Album atau Playlist
        track_list = embed_data.get("trackList", [])
        if not track_list and "tracks" in embed_data:
            track_list = embed_data["tracks"].get("items", [])

        for idx, t in enumerate(track_list):
            t_title = t.get("name") or t.get("title") or f"Track {idx + 1}"
            t_artists = t.get("subtitle") or ", ".join([a.get("name") for a in t.get("artists", [])]) or uploader
            t_id = extract_track_id(t) or t.get("id") or str(idx + 1)

            # Coba ekstrak cover langsung dari data track jika ada
            t_cover = get_high_res_spotify_image(
                t.get("album", {}).get("coverArt")
                or t.get("coverArt")
                or t.get("album", {}).get("images")
                or t.get("images")
            )
            # Jika album, semua lagu gunakan cover album tersebut
            if media_type == "album":
                t_cover = t_cover or thumbnail

            t_album_name = t.get("album", {}).get("name") or (title if media_type == "album" else "Spotify Single")

            items.append({
                "id": t_id,
                "title": t_title,
                "artist": t_artists,
                "album": t_album_name,
                "thumbnail": t_cover,
                "duration": t.get("duration"),
                "track_number": idx + 1,
                "url": f"https://open.spotify.com/track/{t_id}" if len(t_id) >= 15 else url,
                "query": f"{t_artists} - {t_title} audio"
            })
            
        # Jika tipe playlist, pastikan setiap lagu memiliki cover album asli (bukan cover collage playlist)
        if media_type == "playlist" and items:
            missing_items = []
            for idx, item in enumerate(items):
                cov = item.get("thumbnail")
                # Deteksi apakah cover belum ada, sama persis dengan thumbnail playlist, atau merupakan mosaic collage
                is_collage = not cov or cov == thumbnail or "mosaic.scdn.co" in (cov or "") or "ab67706c" in (cov or "")
                if is_collage:
                    missing_items.append((idx, item.get("artist", ""), item.get("title", ""), item.get("id", "")))

            if missing_items:
                def _fetch_track_cover(entry):
                    i, artist_name, song_title, tid = entry
                    real_cover = fetch_track_cover_by_metadata(artist=artist_name, title=song_title, track_id=tid)
                    return i, real_cover

                max_workers = min(12, len(missing_items))
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    for i, real_cov in executor.map(_fetch_track_cover, missing_items):
                        if real_cov:
                            items[i]["thumbnail"] = real_cov

            # Fallback untuk track yang sama sekali tidak ditemukan
            for item in items:
                if not item.get("thumbnail"):
                    item["thumbnail"] = thumbnail

        if not items and oembed:
            # Fallback jika tracklist kosong tapi ada oEmbed
            items.append({
                "id": spotify_id,
                "title": title,
                "artist": uploader,
                "album": title,
                "thumbnail": thumbnail,
                "url": url,
                "query": f"{uploader} - {title} audio"
            })
        is_playlist = len(items) > 1

    return {
        "title": title,
        "uploader": uploader,
        "thumbnail": thumbnail,
        "duration": None,
        "is_playlist": is_playlist,
        "item_count": len(items),
        "items": items,
        "original_url": url,
        "platform": "spotify"
    }

def download_spotify_track(
    track_info: Dict[str, Any],
    quality: str = "320",
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """Mencari audio track Spotify di YouTube Music/YouTube, mengunduh, dan menyematkan metadata."""
    query = track_info.get("query") or f"{track_info.get('artist', '')} - {track_info.get('title', '')} audio"
    search_target = f"ytsearch1:{query}"
    
    target_dir = output_dir or str(DOWNLOADS_DIR)
    bitrate = quality if quality in ["128", "192", "256", "320"] else "320"
    
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "format": "bestaudio/best",
        "outtmpl": os.path.join(target_dir, "%(title).150B [%(id)s].%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": bitrate,
            }
        ]
    }
    
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

    with yt_dlp.YoutubeDL(opts) as ydl:
        res = ydl.extract_info(search_target, download=True)
        if "entries" in res and res["entries"]:
            entry = res["entries"][0]
        else:
            entry = res
            
        temp_filename = ydl.prepare_filename(entry)
        base, _ = os.path.splitext(temp_filename)
        final_mp3 = base + ".mp3"

    # Ganti nama file agar lebih rapi: "{Artist} - {Title}.mp3"
    safe_artist = "".join(c for c in track_info.get("artist", "Artist") if c.isalnum() or c in " ._-").strip()
    safe_title = "".join(c for c in track_info.get("title", "Track") if c.isalnum() or c in " ._-").strip()
    clean_name = f"{safe_artist} - {safe_title}.mp3"
    clean_path = os.path.join(target_dir, clean_name)
    
    try:
        if os.path.exists(final_mp3) and final_mp3 != clean_path:
            if os.path.exists(clean_path):
                os.remove(clean_path)
            os.rename(final_mp3, clean_path)
            final_mp3 = clean_path
    except Exception:
        pass

    # Pastikan cover art yang disematkan adalah cover asli lagu, bukan cover playlist collage
    cover_url = track_info.get("thumbnail")
    track_id = track_info.get("id")
    artist = track_info.get("artist", "")
    title = track_info.get("title", "")
    is_playlist_cover = not cover_url or "mosaic.scdn.co" in cover_url or "ab67706c" in cover_url
    if is_playlist_cover:
        real_cover = fetch_track_cover_by_metadata(artist=artist, title=title, track_id=track_id)
        if real_cover:
            cover_url = real_cover
            track_info["thumbnail"] = real_cover

    cover_url = get_high_res_spotify_image(cover_url)

    # Sematkan tag ID3 resmi dari Spotify
    embed_mp3_metadata(
        file_path=final_mp3,
        title=track_info.get("title"),
        artist=track_info.get("artist"),
        album=track_info.get("album"),
        cover_url=cover_url,
        track_number=track_info.get("track_number")
    )

    return {
        "success": True,
        "title": track_info.get("title"),
        "artist": track_info.get("artist"),
        "file_path": final_mp3,
        "filename": os.path.basename(final_mp3)
    }
