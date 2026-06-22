import os
import shutil
import sqlite3
from datetime import datetime
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
import database as db
from config import templates

router = APIRouter(prefix="/backup", tags=["backup"])

BACKUP_DIR = "backups"


def _ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


@router.get("")
async def backup_page(request: Request):
    _ensure_backup_dir()
    files = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if f.endswith(".db"):
            path = os.path.join(BACKUP_DIR, f)
            stat = os.stat(path)
            files.append({
                "name": f,
                "size": round(stat.st_size / 1024, 1),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return templates.TemplateResponse("backup.html", {"request": request, "backups": files})


@router.post("/create")
async def create_backup():
    _ensure_backup_dir()
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"gym_backup_{ts}.db")

    # Use SQLite's online backup API for a safe hot copy
    src_conn  = sqlite3.connect(db.DB_PATH)
    dest_conn = sqlite3.connect(dest)
    src_conn.backup(dest_conn)
    dest_conn.close()
    src_conn.close()

    size = round(os.path.getsize(dest) / 1024, 1)
    return JSONResponse({"message": f"Backup created: gym_backup_{ts}.db ({size} KB)", "filename": f"gym_backup_{ts}.db"})


@router.get("/download/{filename}")
async def download_backup(filename: str):
    path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(path, media_type="application/octet-stream",
                        headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.post("/restore")
async def restore_backup(file: UploadFile = File(...)):
    if not file.filename.endswith(".db"):
        return JSONResponse({"error": "Only .db files are supported"}, status_code=400)

    content = await file.read()

    # Validate it's a SQLite file
    if not content.startswith(b"SQLite format 3"):
        return JSONResponse({"error": "Invalid SQLite database file"}, status_code=400)

    # Safety backup of current DB before restore
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    _ensure_backup_dir()
    if os.path.exists(db.DB_PATH):
        shutil.copy2(db.DB_PATH, os.path.join(BACKUP_DIR, f"pre_restore_{ts}.db"))

    with open(db.DB_PATH, "wb") as f:
        f.write(content)

    return JSONResponse({"message": "Database restored successfully. Restart the app if data doesn't refresh."})


@router.post("/delete/{filename}")
async def delete_backup(filename: str):
    path = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    return JSONResponse({"message": f"Deleted {filename}"})
