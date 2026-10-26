# All Platforms 🚀

**MASIH DALAM TAHAP PENGEMBANGAN**

Aplikasi web modern berbasis **Python (FastAPI)** untuk mengunduh audio (MP3 hingga 320kbps dengan metadata & album art), video (MP4 hingga 1080p/4K), serta gambar berkualitas asli dari berbagai platform populer: **YouTube, YouTube Music, TikTok, Instagram, Spotify, Twitter/X, SoundCloud, Pinterest, dan 1000+ platform lainnya**.

---

## 🌟 Fitur Utama

- **Multi-Platform Support**:
  - **YouTube & YT Music**: Unduh Video MP4 (1080p/720p/480p) atau Audio MP3 (320k/256k/192k) dengan thumbnail yang otomatis disematkan.
  - **Spotify**: Mengambil info resmi lagu/album/playlist dari Spotify, mencocokkan audio kualitas tinggi dari YouTube Music, serta menyematkan tag ID3 lengkap (Judul, Artis, Album, Tahun, Cover Art).
  - **TikTok**: Unduh video tanpa watermark atau unduh slide foto (carousel gambar beresolusi penuh) + audio latar.
  - **Instagram**: Unduh Reels, video post, foto tunggal, atau seluruh slide **Carousel** (banyak foto/video dalam satu postingan).
  - **Universal**: Twitter/X, SoundCloud, Pinterest, Reddit, Facebook, dan situs lain yang didukung `yt-dlp`.
- **Dukungan Multi-Item & Playlist**:
  - Deteksi otomatis link carousel atau playlist.
  - Tampilan visual daftar item dengan opsi download satu per satu atau unduh semua sekaligus menjadi file terkompresi **`.ZIP`**.
- **Antarmuka Web Modern**:
  - Desain modern bertema gelap (*dark mode*) menggunakan Tailwind CSS & Lucide Icons.
  - *Live progress bar* interaktif dengan indikator persentase, kecepatan unduh, dan status pemrosesan.
  - Opsi simpan langsung ke browser atau akses via folder lokal `downloads/`.
- **Pengaturan Cookies**:
  - Form upload file `cookies.txt` (format Netscape) untuk mengatasi bot-detection YouTube atau mengunduh akun privat Instagram yang Anda ikuti.

---

## 🛠️ Persyaratan Sistem

1. **Python 3.10 atau yang lebih baru**.
2. **FFmpeg** (Sangat disarankan untuk konversi audio ke MP3 320kbps dan penggabungan video berkualitas tinggi).

### Cara Pasang FFmpeg di Windows:
Paling mudah lewat PowerShell / Command Prompt:
```powershell
# Menggunakan Windows Package Manager (Winget):
winget install Gyan.FFmpeg
```
*Atau* unduh build `ffmpeg.exe` dari [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) dan letakkan file `ffmpeg.exe` di dalam folder proyek ini (atau tambahkan ke PATH Windows Anda).

---

## 🚀 Cara Menjalankan

### Cara Cepat (Windows):
Cukup **dobel-klik file `start.bat`**. Skrip ini otomatis mengecek dependensi dan menjalankan server.

### Cara Manual via Terminal:
1. Buka terminal di folder proyek ini:
   ```bash
   cd "d:\Pribadi\Projects\All Platforms"
   ```
2. Pasang pustaka yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```
3. Jalankan aplikasi:
   ```bash
   python run.py
   ```
4. Buka browser pada alamat:
   ```
   http://127.0.0.1:8000
   ```

---

## 📁 Struktur Direktori Proyek

```
All Platforms/
├── app/
│   ├── api/
│   │   └── routes.py            # API routes (/api/inspect, /api/download, /api/progress, dll.)
│   ├── core/
│   │   ├── detector.py          # Pendeteksi platform & URL regex
│   │   ├── engine.py            # Koordinator pemrosesan download
│   │   ├── youtube.py           # Ekstraktor YouTube & YT Music
│   │   ├── spotify.py           # Ekstraktor Spotify Metadata & YT Music Matcher
│   │   ├── tiktok.py            # Ekstraktor TikTok (video tanpa watermark & slide foto)
│   │   ├── instagram.py         # Ekstraktor Instagram (Reels, Post, Carousel)
│   │   ├── generic.py           # Ekstraktor platform universal lainnya
│   │   ├── metadata_tagger.py   # Penyemat tag ID3 dan cover art ke file MP3
│   │   └── zipper.py            # Pengemas file multi-item ke .ZIP
│   ├── utils/
│   │   └── cookies.py           # Pengelola cookies.txt
│   ├── config.py                # Konfigurasi path & deteksi FFmpeg
│   └── main.py                  # Inisialisasi FastAPI & static files
├── static/
│   ├── css/style.css            # Styling kustom
│   └── js/app.js                # Frontend controller & live progress polling
├── templates/
│   └── index.html               # Halaman antarmuka web
├── downloads/                   # Folder hasil unduhan lokal
├── cookies/                     # Folder penyimpanan cookies.txt
├── requirements.txt             # Dependensi Python
├── run.py                       # Skrip utama peluncur aplikasi
├── start.bat                    # Peluncur praktis untuk Windows
└── README.md                    # Dokumentasi ini
```

---

## 🍪 Panduan Ekspor Cookies (Opsional)
Jika Anda ingin mengunduh postingan Instagram dari akun privat yang Anda ikuti, atau jika YouTube memunculkan peringatan bot:
1. Pasang ekstensi browser **"Get cookies.txt LOCALLY"** (tersedia di Chrome Web Store / Firefox Add-ons).
2. Buka situs yang diinginkan (misal Instagram) dan pastikan Anda sudah login.
3. Buka ekstensi dan klik **Export**.
4. Di aplikasi Universal Downloader, klik tombol **"Pengaturan Cookies"** di pojok kanan atas, lalu unggah file `.txt` tersebut atau tempel isinya.
