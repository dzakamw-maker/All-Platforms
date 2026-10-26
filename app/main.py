import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import STATIC_DIR, TEMPLATES_DIR, DOWNLOADS_DIR
from app.api.routes import router as api_router

app = FastAPI(
    title="All Platforms",
    description="Unduh MP3, MP4, dan Gambar dari YouTube, TikTok, Instagram, Spotify, dan berbagai platform lainnya.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include API Router
app.include_router(api_router)

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>All Platforms is running!</h1>")
