# API-сервис: ingestion постов и витрина решений (Facade внутри)
import os
import uuid
import io
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse

from common.bus import make_bus
from common.storage import make_storage
from services.api.facade import ModeratorFacade

app = FastAPI(title="Forum Image Moderator API", version="1.0")
facade = ModeratorFacade(make_bus(), make_storage())

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_SIZE = 15 * 1024 * 1024

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/v1/posts")
def submit_post(image: UploadFile, text: str = Form(""), user_id: str = Form("anon")):
    name = (image.filename or "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "unsupported file type: %s" % ext)
    data = image.file.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "file too large (max 15 MB)")
    if len(data) == 0:
        raise HTTPException(400, "empty file")
    post_id = str(uuid.uuid4())
    key = facade.store_image(post_id, "upload" + ext, data)
    event = facade.submit_post(post_id, user_id, key, text)
    return JSONResponse({"post_id": post_id, "media_key": key, "status": "accepted"}, status_code=202)

@app.get("/api/v1/posts/{post_id}")
def get_verdict(post_id: str):
    row = facade.get_verdict(post_id)
    if not row:
        raise HTTPException(404, "verdict not ready or post not found")
    return row

@app.get("/api/v1/stats")
def stats():
    return facade.stats()

@app.get("/api/v1/search")
def search(q: str):
    return facade.search(q)
