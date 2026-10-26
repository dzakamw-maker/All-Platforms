import sys
import os
import webbrowser
import threading
import time

def check_dependencies():
    missing = []
    errors = {}
    for pkg in ["fastapi", "uvicorn", "yt_dlp", "mutagen", "requests", "bs4"]:
        try:
            __import__(pkg)
        except ImportError as e:
            missing.append(pkg)
            errors[pkg] = str(e)
            
    if missing:
        print("=" * 60)
        print("Pemberitahuan: Ada dependensi yang belum terinstal!")
        print(f"Python interpreter: {sys.executable}")
        print(f"Paket bermasalah  : {', '.join(missing)}")
        for p in missing:
            print(f"  - {p}: {errors[p]}")
        print("\nJalankan perintah berikut di terminal terlebih dahulu:")
        print("    python -m pip install -r requirements.txt")
        print("=" * 60)
        sys.exit(1)

def open_browser(url: str):
    time.sleep(1.2)
    print(f"\n[INFO] Membuka browser: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    check_dependencies()
    
    import uvicorn
    from app.config import HOST, PORT, is_ffmpeg_available

    print("=" * 60)
    print("              ALL PLATFORMS (FASTAPI WEB APP)")
    print("=" * 60)
    print(f"[*] Server Address : http://{HOST}:{PORT}")
    print(f"[*] FFmpeg Status  : {'[TERSEDIA]' if is_ffmpeg_available() else '[BELUM DITEMUKAN - Konversi MP3/muxing terbatas]'}")
    print(f"[*] Folder Simpan  : {os.path.abspath('downloads')}")
    print("=" * 60)
    print("Tekan Ctrl + C di terminal untuk menghentikan server.\n")

    # Buka browser otomatis
    threading.Thread(target=open_browser, args=(f"http://{HOST}:{PORT}",), daemon=True).start()

    # Jalankan server
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
