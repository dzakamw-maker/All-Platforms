import os
import shutil
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
COOKIES_DIR = BASE_DIR / "cookies"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Pastikan folder penting selalu ada
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
COOKIES_DIR.mkdir(parents=True, exist_ok=True)

# Default Cookies File
DEFAULT_COOKIES_FILE = COOKIES_DIR / "cookies.txt"

# Server Settings
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# Check for ffmpeg availability
def get_ffmpeg_path() -> str | None:
    # 1. Cek di PATH sistem
    ffmpeg_system = shutil.which("ffmpeg")
    if ffmpeg_system:
        return ffmpeg_system
    # 2. Cek di folder proyek lokal (misal jika user meletakkan ffmpeg.exe di root/bin)
    local_bin = BASE_DIR / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if local_bin.exists():
        return str(local_bin)
    local_root = BASE_DIR / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if local_root.exists():
        return str(local_root)
    return None

def is_ffmpeg_available() -> bool:
    return get_ffmpeg_path() is not None
