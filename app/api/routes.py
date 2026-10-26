import os
import uuid
import threading
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.config import DOWNLOADS_DIR, is_ffmpeg_available, get_ffmpeg_path
from app.core.engine import inspect_url, process_download
from app.utils.cookies import has_cookies, save_cookies_content, delete_cookies, get_cookies_path

router = APIRouter(prefix="/api")

# In-memory task tracker untuk live progress
tasks: Dict[str, Dict[str, Any]] = {}

class InspectRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format_type: str = "video"       # "video", "audio", "image"
    quality: str = "best"           # "1080", "720", "480", "320", "256", "192", "best"
    selected_item: Optional[Dict[str, Any]] = None
    download_all_zip: bool = False

@router.get("/system/status")
def get_system_status():
    """Mengecek status ketersediaan FFmpeg dan konfigurasi sistem."""
    return {
        "ffmpeg_available": is_ffmpeg_available(),
        "ffmpeg_path": get_ffmpeg_path(),
        "has_cookies": has_cookies(),
        "downloads_dir": str(DOWNLOADS_DIR)
    }

@router.post("/inspect")
def inspect_media_endpoint(req: InspectRequest):
    """Menganalisis URL dan mengembalikan preview metadata."""
    if not req.url or not req.url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL tidak valid. Masukkan URL lengkap (misal: https://...)")
    try:
        data = inspect_url(req.url)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_download_task(task_id: str, req: DownloadRequest):
    def progress_cb(update: Dict[str, Any]):
        if task_id in tasks:
            tasks[task_id].update(update)

    try:
        tasks[task_id]["status"] = "downloading"
        res = process_download(
            url=req.url,
            format_type=req.format_type,
            quality=req.quality,
            selected_item=req.selected_item,
            download_all_zip=req.download_all_zip,
            progress_callback=progress_cb
        )
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["percent"] = 100
        tasks[task_id]["result"] = {
            "title": res.get("title"),
            "filename": res.get("filename"),
            "file_url": f"/api/files/{res.get('filename')}",
            "file_path": res.get("file_path"),
            "folder_name": res.get("folder_name"),
            "folder_path": res.get("folder_path"),
            "is_zip": res.get("is_zip", False)
        }
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)

@router.post("/download")
def download_media_endpoint(req: DownloadRequest, background_tasks: BackgroundTasks):
    """Memulai unduhan di background task dan mengembalikan task_id."""
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "percent": 0,
        "speed": None,
        "eta": None,
        "result": None,
        "error": None
    }
    # Jalankan background thread
    t = threading.Thread(target=run_download_task, args=(task_id, req), daemon=True)
    t.start()
    return {"task_id": task_id}

@router.get("/progress/{task_id}")
def get_task_progress(task_id: str):
    """Mengambil status dan persentase unduhan berdasarkan task_id."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task tidak ditemukan.")
    return tasks[task_id]

@router.get("/files/{filename}")
def serve_downloaded_file(filename: str):
    """Mengunduh file langsung ke browser."""
    # Keamanan path traversal
    safe_filename = os.path.basename(filename)
    file_path = DOWNLOADS_DIR / safe_filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File tidak ditemukan di server.")

    return FileResponse(
        path=str(file_path),
        filename=safe_filename,
        media_type="application/octet-stream"
    )

@router.get("/settings/cookies")
def get_cookies_status():
    """Cek apakah cookies.txt sudah diupload/disimpan."""
    return {"has_cookies": has_cookies(), "path": get_cookies_path()}

@router.post("/settings/cookies")
async def upload_or_save_cookies(
    file: Optional[UploadFile] = File(None),
    content: Optional[str] = Form(None)
):
    """Menyimpan file cookies.txt baik via upload file atau paste teks."""
    try:
        text_data = ""
        if file:
            content_bytes = await file.read()
            text_data = content_bytes.decode("utf-8", errors="ignore")
        elif content:
            text_data = content
        else:
            raise HTTPException(status_code=400, detail="Tidak ada data cookies yang dikirim.")

        save_cookies_content(text_data)
        return {"success": True, "message": "Cookies berhasil disimpan."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan cookies: {str(e)}")

@router.delete("/settings/cookies")
def remove_cookies():
    """Menghapus cookies.txt."""
    deleted = delete_cookies()
    return {"success": deleted, "message": "Cookies berhasil dihapus."}
