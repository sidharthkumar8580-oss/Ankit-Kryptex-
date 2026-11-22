import os
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Ankit Kryptex AI Studio", version="1.0.0")
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "")
AGNES_BASE_URL = os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com").rstrip("/")

class ImageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    ratio: str = Field(default="1:1")
    resolution: str = Field(default="1K")
    reference_image: str | None = None

class VideoRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    ratio: str = Field(default="9:16")
    duration: int = Field(default=5, ge=4, le=12)
    resolution: str = Field(default="720P")
    mode: str = Field(default="single")
    reference_image: str | None = None

def agnes_headers():
    if not AGNES_API_KEY:
        raise HTTPException(status_code=503, detail="Agnes API key abhi Render ke AGNES_API_KEY environment variable mein add nahi hui hai.")
    return {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}

def ratio_size(ratio: str, resolution: str):
    tier = resolution if resolution in {"1K", "2K", "3K", "4K"} else "1K"
    return tier

def validate_ratio(ratio: str):
    allowed = {"1:1", "16:9", "9:16", "4:3", "3:4", "21:9"}
    if ratio not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported aspect ratio.")
    return ratio

@app.get("/health")
def health():
    return {"ok": True, "service": "Ankit Kryptex AI Studio", "agnes_configured": bool(AGNES_API_KEY)}

@app.post("/api/media/image")
async def generate_image(body: ImageRequest):
    validate_ratio(body.ratio)
    if body.resolution not in {"1K", "2K", "3K", "4K"}:
        raise HTTPException(status_code=400, detail="Choose a supported image resolution.")
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": body.prompt,
        "size": body.resolution,
        "n": 1,
        "extra_body": {"ratio": body.ratio, "response_format": "url"}
    }
    if body.reference_image:
        payload["extra_body"]["image"] = [body.reference_image]
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(f"{AGNES_BASE_URL}/v1/images/generations", headers=agnes_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        except HTTPException:
            raise
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:1200]
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agnes image error: {detail}")
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=f"Agnes image service error: {exc}")
    item = (data.get("data") or [{}])[0]
    result_url = item.get("url")
    if not result_url and item.get("b64_json"):
        result_url = "data:image/png;base64," + item["b64_json"]
    if not result_url:
        raise HTTPException(status_code=502, detail="Agnes response mein image URL nahi mila.")
    return {"type": "image", "url": result_url, "model": "agnes-image-2.1-flash"}

@app.post("/api/media/video")
async def generate_video(body: VideoRequest):
    validate_ratio(body.ratio)
    model = "agnes-video-2.5" if body.resolution in {"1080P", "1K", "2K"} else "agnes-video-2.5-flash"
    resolution = body.resolution if model == "agnes-video-2.5" else "720P"
    prompt = body.prompt
    if body.mode == "multi":
        prompt = ("Create a coherent multi-shot story with 2 to 5 visually distinct cinematic shots, "
                  "clear shot transitions, consistent subjects and a beginning, middle and ending. " + prompt)
    payload = {
        "model": model,
        "prompt": prompt,
        "mode": "img2video" if body.reference_image else "text",
        "seconds": str(body.duration),
        "size": resolution,
        "aspect_ratio": body.ratio
    }
    if body.reference_image:
        payload["first_frame"] = body.reference_image
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(f"{AGNES_BASE_URL}/v1/videos", headers=agnes_headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        except HTTPException:
            raise
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:1200]
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agnes video error: {detail}")
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=f"Agnes video service error: {exc}")
    video_id = data.get("video_id") or data.get("id") or data.get("task_id")
    if not video_id:
        raise HTTPException(status_code=502, detail=f"Agnes response mein video task ID nahi mila: {data}")
    return {"type": "video", "video_id": video_id, "model": model, "status": data.get("status", "processing"), "raw": data}

@app.get("/api/media/video/{video_id}")
async def poll_video(video_id: str, model_name: str = Query(default="agnes-video-2.5-flash")):
    if not video_id or len(video_id) > 300:
        raise HTTPException(status_code=400, detail="Invalid video ID.")
    if model_name not in {"agnes-video-2.5", "agnes-video-2.5-flash"}:
        raise HTTPException(status_code=400, detail="Unsupported video model.")
    async with httpx.AsyncClient(timeout=45) as client:
        try:
            response = await client.get(
                f"{AGNES_BASE_URL}/agnesapi",
                headers={"Authorization": f"Bearer {AGNES_API_KEY}"} if AGNES_API_KEY else {},
                params={"video_id": video_id, "model_name": model_name}
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agnes status error: {exc.response.text[:1000]}")
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=f"Agnes status service error: {exc}")
    return data

@app.get("/api/media/download")
async def download_media(url: str = Query(min_length=8, max_length=4000)):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Only secure HTTPS media URLs are supported.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if any(ipaddress.ip_address(item[4][0]).is_private or ipaddress.ip_address(item[4][0]).is_loopback or ipaddress.ip_address(item[4][0]).is_link_local for item in addresses):
            raise HTTPException(status_code=400, detail="Invalid media host.")
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Could not resolve media host.")
    async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Media download failed: {exc}")
    content_type = response.headers.get("content-type", "application/octet-stream").split(";")[0]
    filename = "ankit-kryptex-media" + (".mp4" if "video" in content_type else ".png" if "image" in content_type else ".bin")
    return StreamingResponse(iter([response.content]), media_type=content_type,
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")
