import requests
from pathlib import Path
from typing import Optional

try:
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC, ID3NoHeaderError
except ImportError:
    ID3 = None

def embed_mp3_metadata(
    file_path: str | Path,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    album: Optional[str] = None,
    year: Optional[str] = None,
    track_number: Optional[int] = None,
    cover_url: Optional[str] = None,
    cover_bytes: Optional[bytes] = None
) -> bool:
    """Menyematkan ID3 metadata dan cover art ke file MP3."""
    if ID3 is None:
        return False
        
    path = Path(file_path)
    if not path.exists():
        return False

    try:
        try:
            audio = ID3(str(path))
        except ID3NoHeaderError:
            audio = ID3()

        if title:
            audio["TIT2"] = TIT2(encoding=3, text=title)
        if artist:
            audio["TPE1"] = TPE1(encoding=3, text=artist)
        if album:
            audio["TALB"] = TALB(encoding=3, text=album)
        if year:
            audio["TDRC"] = TDRC(encoding=3, text=str(year))
        if track_number is not None:
            audio["TRCK"] = TRCK(encoding=3, text=str(track_number))

        # Download / Embed cover art jika ada
        img_data = cover_bytes
        if not img_data and cover_url:
            try:
                resp = requests.get(cover_url, timeout=10)
                if resp.status_code == 200:
                    img_data = resp.content
            except Exception:
                pass

        if img_data:
            mime = "image/jpeg"
            if img_data.startswith(b"\x89PNG"):
                mime = "image/png"
            elif img_data.startswith(b"RIFF") and img_data[8:12] == b"WEBP":
                mime = "image/webp"

            audio["APIC"] = APIC(
                encoding=3,
                mime=mime,
                type=3,  # Cover (front)
                desc="Cover",
                data=img_data
            )

        audio.save(str(path), v2_version=3)
        return True
    except Exception as e:
        print(f"Warning: Gagal menyematkan ID3 metadata: {e}")
        return False
