// All Platforms Frontend Logic

let currentMediaData = null;
let selectedFormat = "video";
let selectedQuality = "best";
let pollInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  // 1. Inisialisasi ikon Lucide
  lucide.createIcons();

  // 2. Cek status sistem (FFmpeg & Cookies)
  checkSystemStatus();

  // 3. Event listeners input URL & platform detector
  const urlInput = document.getElementById("urlInput");
  const clearBtn = document.getElementById("clearBtn");

  urlInput.addEventListener("input", () => {
    const val = urlInput.value.trim();
    clearBtn.classList.toggle("hidden", val.length === 0);
    updateDetectedPlatformIcon(val);
  });

  clearBtn.addEventListener("click", () => {
    urlInput.value = "";
    clearBtn.classList.add("hidden");
    updateDetectedPlatformIcon("");
    hidePreviewAndProgress();
  });

  // 4. Form submit (Inspect URL)
  document.getElementById("urlForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;
    await inspectUrl(url);
  });

  // 5. Download actions
  document.getElementById("startDownloadBtn").addEventListener("click", () => {
    if (!currentMediaData) return;
    const isMultiOrPlaylist = currentMediaData.is_playlist || (currentMediaData.item_count && currentMediaData.item_count > 1);
    startDownload({
      url: currentMediaData.original_url,
      format_type: selectedFormat,
      quality: selectedQuality,
      download_all_zip: isMultiOrPlaylist
    });
  });

  document.getElementById("downloadAllZipBtn").addEventListener("click", () => {
    if (!currentMediaData) return;
    startDownload({
      url: currentMediaData.original_url,
      format_type: selectedFormat,
      quality: selectedQuality,
      download_all_zip: true
    });
  });

  // 6. Settings Modal handlers
  setupSettingsModal();
});

// Deteksi visual ikon platform saat user mengetik
function updateDetectedPlatformIcon(url) {
  const iconEl = document.getElementById("detectedPlatformIcon");
  let iconName = "link";

  if (url.includes("spotify.com") || url.startsWith("spotify:")) iconName = "music";
  else if (url.includes("youtube.com") || url.includes("youtu.be")) iconName = "youtube";
  else if (url.includes("tiktok.com")) iconName = "video";
  else if (url.includes("instagram.com")) iconName = "instagram";
  else if (url.includes("twitter.com") || url.includes("x.com")) iconName = "twitter";
  else if (url.includes("pinterest.com") || url.includes("pin.it")) iconName = "image";

  iconEl.setAttribute("data-lucide", iconName);
  lucide.createIcons();
}

// Cek status FFmpeg di backend
async function checkSystemStatus() {
  const badge = document.getElementById("ffmpegBadge");
  try {
    const res = await fetch("/api/system/status");
    const data = await res.json();
    if (data.ffmpeg_available) {
      badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400"></span><span class="text-emerald-300 font-medium">FFmpeg: Siap</span>`;
      badge.classList.remove("border-slate-800");
      badge.classList.add("border-emerald-500/30", "bg-emerald-950/30");
    } else {
      badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-400"></span><span class="text-amber-300">FFmpeg: Tidak ditemukan</span>`;
      badge.title = "FFmpeg tidak ditemukan di PATH. Konversi audio MP3 kualitas tinggi memerlukan FFmpeg.";
    }
  } catch (e) {
    badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-slate-500"></span><span>Status Offline</span>`;
  }
}

// Inspect URL
async function inspectUrl(url) {
  const inspectBtn = document.getElementById("inspectBtn");
  const errorAlert = document.getElementById("errorAlert");
  const errorMessage = document.getElementById("errorMessage");

  errorAlert.classList.add("hidden");
  hidePreviewAndProgress();

  inspectBtn.disabled = true;
  inspectBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Menganalisis...</span>`;
  lucide.createIcons();

  try {
    const res = await fetch("/api/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Gagal mengambil data dari URL.");
    }

    currentMediaData = data;
    renderMediaPreview(data);
  } catch (err) {
    errorMessage.textContent = err.message || "Terjadi kesalahan saat memeriksa URL.";
    errorAlert.classList.remove("hidden");
  } finally {
    inspectBtn.disabled = false;
    inspectBtn.innerHTML = `<i data-lucide="search" class="w-4 h-4"></i><span>Analisis Link</span>`;
    lucide.createIcons();
  }
}

// Render Preview Card
function renderMediaPreview(data) {
  const previewSection = document.getElementById("previewSection");
  const mediaThumbnail = document.getElementById("mediaThumbnail");
  const mediaTitle = document.getElementById("mediaTitle");
  const mediaUploader = document.getElementById("mediaUploader").querySelector("span");
  const mediaPlatformBadge = document.getElementById("mediaPlatformBadge");
  const mediaDurationBadge = document.getElementById("mediaDurationBadge");

  // Thumbnail & text
  mediaThumbnail.src = data.thumbnail || "/static/img/placeholder.png";
  mediaTitle.textContent = data.title || "Media File";
  mediaUploader.textContent = data.uploader || "Unknown Author";
  mediaPlatformBadge.textContent = data.platform_name || data.platform;

  if (data.duration) {
    const mins = Math.floor(data.duration / 60);
    const secs = Math.floor(data.duration % 60);
    mediaDurationBadge.textContent = `${mins}:${secs.toString().padStart(2, "0")}`;
    mediaDurationBadge.classList.remove("hidden");
  } else {
    mediaDurationBadge.classList.add("hidden");
  }

  // Setup Format Tabs
  setupFormatTabs(data.supported_formats || ["video", "audio"]);

  // Sesuaikan tombol download utama untuk playlist vs single
  const startBtn = document.getElementById("startDownloadBtn");
  if (data.is_playlist) {
    startBtn.innerHTML = `<i data-lucide="folder-down" class="w-5 h-5"></i><span>Unduh Playlist ke Folder (.ZIP)</span>`;
  } else {
    startBtn.innerHTML = `<i data-lucide="download" class="w-5 h-5"></i><span>Unduh Sekarang</span>`;
  }

  // Multi-item / Carousel / Playlist view
  const multiSection = document.getElementById("multiItemSection");
  const multiGrid = document.getElementById("multiItemGrid");
  const multiTitle = document.getElementById("multiItemTitle");

  if (data.item_count > 1 || data.is_playlist) {
    multiSection.classList.remove("hidden");
    multiTitle.textContent = `${data.item_count} Item Ditemukan (${data.is_playlist ? "Playlist/Album" : "Carousel/Slides"})`;
    multiGrid.innerHTML = "";

    data.items.forEach((item, idx) => {
      const card = document.createElement("div");
      card.className = "media-item-card bg-slate-950 border border-slate-800 rounded-xl p-3 flex flex-col justify-between";
      card.innerHTML = `
        <div>
          <div class="aspect-square bg-slate-900 rounded-lg overflow-hidden mb-2 relative">
            <img src="${item.thumbnail || data.thumbnail || ''}" onerror="this.onerror=null; this.src='${data.thumbnail || ''}'" class="w-full h-full object-cover">
            <span class="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-black/70 text-[10px] font-mono text-white">#${idx + 1}</span>
          </div>
          <h5 class="text-xs font-semibold text-white truncate" title="${item.title}">${item.title}</h5>
          ${item.artist ? `<p class="text-[11px] text-slate-400 truncate">${item.artist}</p>` : ''}
        </div>
        <button class="item-download-btn mt-3 w-full py-1.5 bg-slate-900 hover:bg-indigo-600 border border-slate-700 hover:border-transparent text-slate-300 hover:text-white rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1.5" data-index="${idx}">
          <i data-lucide="download" class="w-3.5 h-3.5"></i> Unduh
        </button>
      `;
      multiGrid.appendChild(card);
    });

    // Event listener untuk tombol unduh individual
    multiGrid.querySelectorAll(".item-download-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const itemIdx = parseInt(btn.getAttribute("data-index"));
        const item = data.items[itemIdx];
        startDownload({
          url: data.original_url,
          format_type: selectedFormat,
          quality: selectedQuality,
          selected_item: item,
          download_all_zip: false
        });
      });
    });
  } else {
    multiSection.classList.add("hidden");
  }

  previewSection.classList.remove("hidden");
  lucide.createIcons();
}

// Konfigurasi tab format (Video / Audio / Gambar)
function setupFormatTabs(supportedFormats) {
  const tabs = document.querySelectorAll(".format-btn");
  let defaultSet = false;

  tabs.forEach((tab) => {
    const fmt = tab.getAttribute("data-format");
    if (supportedFormats.includes(fmt) || (fmt === "video" && supportedFormats.includes("mp4")) || (fmt === "audio" && supportedFormats.includes("mp3"))) {
      tab.classList.remove("hidden");
      if (!defaultSet) {
        setActiveFormat(fmt);
        defaultSet = true;
      }
    } else {
      tab.classList.add("hidden");
    }

    tab.onclick = () => {
      setActiveFormat(fmt);
    };
  });
}

function setActiveFormat(format) {
  selectedFormat = format;
  document.querySelectorAll(".format-btn").forEach((tab) => {
    tab.classList.toggle("active", tab.getAttribute("data-format") === format);
  });
  updateQualityOptions();
}

// Update opsi kualitas berdasarkan format yang aktif
function updateQualityOptions() {
  const select = document.getElementById("qualitySelect");
  const hint = document.getElementById("qualityHint");
  const container = document.getElementById("qualityContainer");

  select.innerHTML = "";

  if (selectedFormat === "audio") {
    container.classList.remove("hidden");
    select.innerHTML = `
      <option value="320" selected>320 kbps (High Quality MP3)</option>
      <option value="256">256 kbps (Medium-High MP3)</option>
      <option value="192">192 kbps (Standard MP3)</option>
    `;
    hint.textContent = "Metadata ID3 (Artis, Judul, Album Art) otomatis disematkan ke file MP3.";
    selectedQuality = "320";
  } else if (selectedFormat === "video") {
    container.classList.remove("hidden");
    select.innerHTML = `
      <option value="best" selected>Resolusi Tertinggi (Auto Best)</option>
      <option value="1080">1080p Full HD</option>
      <option value="720">720p HD</option>
      <option value="480">480p SD</option>
    `;
    hint.textContent = "Video diunduh dalam format MP4 yang kompatibel dengan semua perangkat.";
    selectedQuality = "best";
  } else {
    // Image
    container.classList.add("hidden");
    selectedQuality = "best";
  }

  select.onchange = () => {
    selectedQuality = select.value;
  };
}

// Mulai proses download
async function startDownload(payload) {
  const progressSection = document.getElementById("progressSection");
  const completedSection = document.getElementById("completedSection");
  const errorAlert = document.getElementById("errorAlert");
  const progressBar = document.getElementById("progressBar");
  const progressPercentText = document.getElementById("progressPercentText");
  const progressStatusText = document.getElementById("progressStatusText");
  const progressSubtext = document.getElementById("progressSubtext");

  errorAlert.classList.add("hidden");
  completedSection.classList.add("hidden");
  progressSection.classList.remove("hidden");

  // Reset bar
  progressBar.style.width = "0%";
  progressPercentText.textContent = "0%";
  progressStatusText.textContent = "Memulai Unduhan...";
  progressSubtext.textContent = "Mengirim permintaan ke server...";

  // Scroll ke progress
  progressSection.scrollIntoView({ behavior: "smooth", block: "nearest" });

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Gagal memulai unduhan.");
    }

    const taskId = data.task_id;
    pollDownloadProgress(taskId);
  } catch (err) {
    progressSection.classList.add("hidden");
    document.getElementById("errorMessage").textContent = err.message;
    errorAlert.classList.remove("hidden");
  }
}

// Polling status download dari server
function pollDownloadProgress(taskId) {
  if (pollInterval) clearInterval(pollInterval);

  const progressBar = document.getElementById("progressBar");
  const progressPercentText = document.getElementById("progressPercentText");
  const progressStatusText = document.getElementById("progressStatusText");
  const progressSubtext = document.getElementById("progressSubtext");
  const progressSection = document.getElementById("progressSection");
  const completedSection = document.getElementById("completedSection");

  pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/progress/${taskId}`);
      if (!res.ok) return;

      const data = await res.json();

      if (data.status === "downloading" || data.status === "processing") {
        const pct = data.percent || 0;
        progressBar.style.width = `${pct}%`;
        progressPercentText.textContent = `${pct}%`;

        if (data.item_total) {
          progressStatusText.textContent = `Mengunduh (${data.item_current}/${data.item_total}): ${data.current_title || ''}`;
        } else if (data.status === "processing") {
          progressStatusText.textContent = "Memproses & Menyelaraskan Format...";
          progressSubtext.textContent = "Konversi audio / muxing video...";
        } else {
          progressStatusText.textContent = "Mengunduh file...";
          progressSubtext.textContent = data.speed ? `Kecepatan: ${(data.speed / 1024 / 1024).toFixed(2)} MB/s` : 'Sedang mentransfer data...';
        }
      } else if (data.status === "completed") {
        clearInterval(pollInterval);
        progressBar.style.width = "100%";
        progressPercentText.textContent = "100%";

        setTimeout(() => {
          progressSection.classList.add("hidden");
          completedSection.classList.remove("hidden");

          const result = data.result || {};
          document.getElementById("completedFilename").textContent = result.filename || "File siap diunduh";
          const folderInfo = document.getElementById("completedFolderInfo");
          if (folderInfo) {
            if (result.is_zip && result.folder_name) {
              folderInfo.innerHTML = `Tersimpan di folder <code class="text-indigo-300 font-mono">downloads/${result.folder_name}/</code> & arsip <code class="text-indigo-300 font-mono">downloads/${result.filename}</code>`;
            } else {
              folderInfo.innerHTML = `Tersimpan di folder <code class="text-indigo-300 font-mono">downloads/</code>`;
            }
          }
          const browserBtn = document.getElementById("browserDownloadBtn");
          browserBtn.href = result.file_url;
          browserBtn.download = result.filename;
          
          lucide.createIcons();
          completedSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }, 600);
      } else if (data.status === "error") {
        clearInterval(pollInterval);
        progressSection.classList.add("hidden");
        document.getElementById("errorMessage").textContent = data.error || "Gagal mengunduh media.";
        document.getElementById("errorAlert").classList.remove("hidden");
      }
    } catch (e) {
      console.error("Polling error:", e);
    }
  }, 600);
}

function hidePreviewAndProgress() {
  document.getElementById("previewSection").classList.add("hidden");
  document.getElementById("progressSection").classList.add("hidden");
  document.getElementById("completedSection").classList.add("hidden");
  if (pollInterval) clearInterval(pollInterval);
}

// Modal Pengaturan Cookies
function setupSettingsModal() {
  const modal = document.getElementById("settingsModal");
  const openBtn = document.getElementById("openSettingsBtn");
  const closeBtn = document.getElementById("closeSettingsBtn");
  const saveBtn = document.getElementById("saveCookiesBtn");
  const deleteBtn = document.getElementById("deleteCookiesBtn");
  const fileInput = document.getElementById("cookiesFileInput");
  const textInput = document.getElementById("cookiesTextInput");
  const statusIndicator = document.getElementById("cookiesStatusIndicator");

  const updateModalCookiesStatus = async () => {
    try {
      const res = await fetch("/api/settings/cookies");
      const d = await res.json();
      if (d.has_cookies) {
        statusIndicator.textContent = "Aktif (cookies.txt tersimpan)";
        statusIndicator.className = "font-semibold text-emerald-400";
      } else {
        statusIndicator.textContent = "Belum disetel";
        statusIndicator.className = "font-semibold text-amber-400";
      }
    } catch (e) {}
  };

  openBtn.onclick = () => {
    modal.classList.remove("hidden");
    updateModalCookiesStatus();
    lucide.createIcons();
  };

  closeBtn.onclick = () => {
    modal.classList.add("hidden");
  };

  modal.onclick = (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  };

  saveBtn.onclick = async () => {
    const file = fileInput.files[0];
    const text = textInput.value.trim();

    if (!file && !text) {
      alert("Pilih file cookies.txt atau tempel teks cookies terlebih dahulu.");
      return;
    }

    const formData = new FormData();
    if (file) {
      formData.append("file", file);
    } else {
      formData.append("content", text);
    }

    try {
      const res = await fetch("/api/settings/cookies", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        alert("Cookies berhasil disimpan!");
        fileInput.value = "";
        textInput.value = "";
        updateModalCookiesStatus();
      } else {
        alert(data.detail || "Gagal menyimpan cookies.");
      }
    } catch (err) {
      alert("Error: " + err.message);
    }
  };

  deleteBtn.onclick = async () => {
    if (!confirm("Hapus cookies yang tersimpan?")) return;
    try {
      await fetch("/api/settings/cookies", { method: "DELETE" });
      alert("Cookies berhasil dihapus.");
      updateModalCookiesStatus();
    } catch (e) {
      alert("Gagal menghapus cookies.");
    }
  };
}
