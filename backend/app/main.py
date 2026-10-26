"""
QuickDiagnosis - FastAPI Application Main Entrypoint
Integrates symptom screening, lab report management, and external medical sources.
Serves UI templates and static assets for single-page application.
"""

import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.diagnosis import router as diagnosis_router
from backend.app.api.lab_reports import router as lab_reports_router

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"

app = FastAPI(
    title="QuickDiagnosis API",
    description="Gentle, Intelligent & Privacy-First Medical Symptom and Laboratory Assessment",
    version="2.0.0"
)

# Enable CORS for local client and external requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(diagnosis_router)
app.include_router(lab_reports_router)

# Mount Static Files (CSS, JS, icons, manifest, service worker)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse, summary="Serve QuickDiagnosis Web UI")
def serve_index():
    index_file = TEMPLATE_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>QuickDiagnosis - index.html not found</h1>", status_code=404)
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/emergency", response_class=HTMLResponse, summary="Serve Emergency Guidance UI")
def serve_emergency():
    emergency_file = TEMPLATE_DIR / "emergency.html"
    if not emergency_file.exists():
        return HTMLResponse("<h1>QuickDiagnosis - emergency.html not found</h1>", status_code=404)
    with open(emergency_file, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/manifest.json", summary="Serve PWA manifest")
def serve_manifest():
    manifest_path = STATIC_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(str(manifest_path), media_type="application/manifest+json")
    return HTMLResponse("{}", status_code=404)


@app.get("/favicon.ico", summary="Serve favicon icon")
def serve_favicon():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path), media_type="image/x-icon")
    return HTMLResponse("", status_code=404)


@app.get("/sw.js", summary="Serve PWA service worker")
def serve_service_worker():
    sw_path = STATIC_DIR / "sw.js"
    if sw_path.exists():
        return FileResponse(str(sw_path), media_type="application/javascript")
    return HTMLResponse("", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=5000, reload=True)
