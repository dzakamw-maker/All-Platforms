import sys
from pathlib import Path

# Tambahkan direktori root ke sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def test_imports():
    print("[TEST 1] Menguji import modul...")
    import app.config as config
    import app.core.detector as detector
    import app.core.metadata_tagger as tagger
    import app.core.zipper as zipper
    import app.core.youtube as yt
    import app.core.spotify as sp
    import app.core.tiktok as tt
    import app.core.instagram as ig
    import app.core.threads as th
    import app.core.twitter as tw
    import app.core.pinterest as pt
    import app.core.generic as gen
    import app.utils.errors as errors
    import app.core.engine as engine
    import app.api.routes as routes
    import app.main as main
    print("  -> Semua modul berhasil di-import tanpa error!")

def test_detector():
    print("\n[TEST 2] Menguji logika pendeteksi platform...")
    from app.core.detector import detect_platform, Platform, MediaType

    test_cases = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", Platform.YOUTUBE, MediaType.VIDEO),
        ("https://youtu.be/dQw4w9WgXcQ", Platform.YOUTUBE, MediaType.VIDEO),
        ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", Platform.YT_MUSIC, MediaType.AUDIO),
        ("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT", Platform.SPOTIFY, MediaType.AUDIO),
        ("https://open.spotify.com/album/4m2880jivSbbyEGAKfITCa", Platform.SPOTIFY, MediaType.PLAYLIST),
        ("https://www.tiktok.com/@user/video/7234567890123456789", Platform.TIKTOK, MediaType.VIDEO),
        ("https://www.tiktok.com/@user/photo/7234567890123456789", Platform.TIKTOK, MediaType.CAROUSEL),
        ("https://www.instagram.com/p/C123456789/", Platform.INSTAGRAM, MediaType.CAROUSEL),
        ("https://www.instagram.com/reel/C123456789/", Platform.INSTAGRAM, MediaType.VIDEO),
        ("https://x.com/user/status/123456789", Platform.TWITTER, MediaType.VIDEO),
        ("https://www.threads.com/share/EBR7c2sRK/", Platform.THREADS, MediaType.CAROUSEL),
        ("https://www.threads.net/@user/post/123456789", Platform.THREADS, MediaType.CAROUSEL),
        ("https://www.facebook.com/watch/?v=123456", Platform.FACEBOOK, MediaType.VIDEO),
        ("https://soundcloud.com/artist/track", Platform.SOUNDCLOUD, MediaType.AUDIO),
        ("https://id.pinterest.com/pin/123456789/", Platform.PINTEREST, MediaType.IMAGE),
    ]

    for url, expected_plat, expected_media in test_cases:
        res = detect_platform(url)
        assert res["platform"] == expected_plat, f"Failed platform for {url}: got {res['platform']}, expected {expected_plat}"
        assert res["media_type"] == expected_media, f"Failed media_type for {url}: got {res['media_type']}, expected {expected_media}"
        print(f"  [OK] {res['name']} ({res['media_type'].value}) -> {url[:45]}...")

    print("  -> Seluruh 12 pola URL berhasil dideteksi dengan akurat!")

def test_fastapi_routes():
    print("\n[TEST 3] Menguji rute FastAPI...")
    from app.main import app
    route_paths = [route.path for route in app.routes]
    expected_endpoints = ["/", "/api/system/status", "/api/inspect", "/api/download", "/api/progress/{task_id}", "/api/files/{filename}", "/api/settings/cookies"]
    
    for ep in expected_endpoints:
        assert ep in route_paths, f"Missing endpoint: {ep}"
        print(f"  [OK] Endpoint terdaftar: {ep}")
    print("  -> Seluruh endpoint API terdaftar dengan benar!")

if __name__ == "__main__":
    print("=" * 60)
    print("      VERIFIKASI INTEGRITAS APLIKASI UNIVERSAL DOWNLOADER")
    print("=" * 60)
    test_imports()
    test_detector()
    test_fastapi_routes()
    print("\n" + "=" * 60)
    print("      SEMUA PENGUJIAN OTOMATIS BERHASIL (100% PASS)")
    print("=" * 60)
