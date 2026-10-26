import zipfile
from pathlib import Path
from typing import List, Optional
from app.config import DOWNLOADS_DIR

def create_zip_archive(files: List[str | Path], archive_name: str, folder_in_archive: Optional[str] = None) -> Path:
    """Mengemas daftar file menjadi satu file .ZIP di dalam folder downloads, dengan folder khusus jika ditentukan."""
    # Sanitasi nama file ZIP
    safe_name = "".join(c for c in archive_name if c.isalnum() or c in " ._-").strip()
    if not safe_name.endswith(".zip"):
        safe_name += ".zip"
        
    zip_path = DOWNLOADS_DIR / safe_name
    
    safe_folder = ""
    if folder_in_archive:
        safe_folder = "".join(c for c in folder_in_archive if c.isalnum() or c in " ._-").strip()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            p = Path(file)
            if p.exists() and p.is_file():
                arcname = f"{safe_folder}/{p.name}" if safe_folder else p.name
                zipf.write(p, arcname=arcname)
                
    return zip_path
