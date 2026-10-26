from pathlib import Path
from app.config import DEFAULT_COOKIES_FILE, COOKIES_DIR

def get_cookies_path() -> str | None:
    """Mengembalikan path file cookies jika ada dan tidak kosong."""
    if DEFAULT_COOKIES_FILE.exists() and DEFAULT_COOKIES_FILE.stat().st_size > 0:
        return str(DEFAULT_COOKIES_FILE)
    return None

def save_cookies_content(content: str) -> bool:
    """Menyimpan konten cookies format Netscape."""
    COOKIES_DIR.mkdir(parents=True, exist_ok=True)
    with open(DEFAULT_COOKIES_FILE, "w", encoding="utf-8") as f:
        f.write(content.strip())
    return True

def delete_cookies() -> bool:
    """Menghapus file cookies."""
    if DEFAULT_COOKIES_FILE.exists():
        DEFAULT_COOKIES_FILE.unlink()
        return True
    return False

def has_cookies() -> bool:
    return get_cookies_path() is not None
