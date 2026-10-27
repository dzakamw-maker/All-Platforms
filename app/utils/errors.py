import re
from urllib.parse import urlparse

def clean_error_message(msg: str) -> str:
    """Membersihkan ANSI escape codes dan mengubah pesan error teknis menjadi pesan yang user-friendly."""
    if not msg:
        return "Terjadi kesalahan yang tidak diketahui."

    # 1. Bersihkan kode warna ANSI terminal (misal: [0;31mERROR:[0m)
    cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(msg))
    cleaned = re.sub(r'\[[0-9;]+m', '', cleaned)

    # 2. Hapus prefix log teknis
    cleaned = re.sub(r'^(ERROR|WARNING|CRITICAL):\s*', '', cleaned.strip(), flags=re.IGNORECASE)
    cleaned = cleaned.strip()

    # 3. Terjemahkan error umum yt-dlp / jaringan menjadi pesan ramah pengguna
    if "Unsupported URL" in cleaned:
        m = re.search(r'https?://[^\s]+', cleaned)
        domain = ""
        if m:
            try:
                domain = urlparse(m.group(0)).netloc
            except Exception:
                domain = ""
        if domain:
            return f"Tautan dari {domain} tidak didukung atau formatnya belum dikenali oleh sistem."
        return "Tautan ini tidak didukung atau formatnya belum dikenali oleh sistem."

    if any(k in cleaned.lower() for k in ["private video", "sign in to confirm", "login required", "restricted", "requires authentication"]):
        return "Konten ini bersifat privat atau dibatasi login. Silakan pasang cookies akun Anda di menu 'Pengaturan Cookies'."

    if any(k in cleaned.lower() for k in ["video unavailable", "media not found", "404 not found", "does not exist"]):
        return "Media tidak ditemukan atau konten telah dihapus oleh pemiliknya."

    if any(k in cleaned.lower() for k in ["too many requests", "rate limit", "429"]):
        return "Terlalu banyak permintaan ke platform tersebut (Rate Limited). Silakan tunggu beberapa saat lagi."

    if "No video could be found in this tweet" in cleaned:
        return "Tidak ada media foto atau video yang dapat ditemukan pada tweet tersebut. Pastikan postingan memuat media dan bersifat publik."

    if "Unable to extract" in cleaned:
        return "Gagal mengekstrak data dari tautan tersebut. Pastikan konten bersifat publik."

    return cleaned
