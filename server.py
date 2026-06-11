import logging
"""
MediaDL — FastAPI backend with Cobalt
YouTube + Instagram media downloader
"""

import asyncio
import json
import re
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="MediaDL")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend
PUBLIC_DIR = Path(__file__).parent / "public"
app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")

COBALT_URL = "http://localhost:9000"

# ─── Cobalt helpers ───


def cobalt_request(payload: dict, timeout: int = 60) -> dict:
    """Call local Cobalt API."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        COBALT_URL,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        try:
            return json.loads(body)
        except Exception:
            raise RuntimeError(f"Cobalt HTTP {e.code}: {body[:200]}")


def cobalt_stream(url: str, timeout: int = 300):
    """Generator: stream bytes from a Cobalt tunnel/redirect URL."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            yield chunk


# ─── Platform detection ───

YOUTUBE_RE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([\w-]+)"
)
INSTAGRAM_RE = re.compile(
    r"instagram\.com/(?:reels?|p|tv)/([\w-]+)"
)


def detect_platform(url: str) -> tuple[str, str]:
    """Return (platform, video_id)."""
    m = YOUTUBE_RE.search(url)
    if m:
        return "youtube", m.group(1)
    m = INSTAGRAM_RE.search(url)
    if m:
        return "instagram", m.group(1)
    return "unknown", ""


# ─── Format helpers ───


def format_size(bytes_val: Optional[int]) -> str:
    if not bytes_val:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"


def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "0:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# YouTube quality presets (cobalt-driven, no dynamic format detection)
YT_VIDEO_PRESETS = [
    {"id": "max",  "type": "video", "label": "Best Available", "quality": 9999, "ext": "mp4", "size": "Unknown", "filesize_bytes": 0},
    {"id": "2160", "type": "video", "label": "2160p (4K)",     "quality": 2160, "ext": "mp4", "size": "Unknown", "filesize_bytes": 0},
    {"id": "1440", "type": "video", "label": "1440p (2K)",     "quality": 1440, "ext": "mp4", "size": "Unknown", "filesize_bytes": 0},
    {"id": "1080", "type": "video", "label": "1080p",          "quality": 1080, "ext": "mp4", "size": "Unknown", "filesize_bytes": 0},
    {"id": "720",  "type": "video", "label": "720p",           "quality": 720,  "ext": "mp4", "size": "Unknown", "filesize_bytes": 0},
    {"id": "480",  "type": "video", "label": "480p",           "quality": 480,  "ext": "mp4", "size": "Unknown", "filesize_bytes": 0},
]

YT_AUDIO_PRESETS = [
    {"id": "320", "type": "audio", "label": "MP3 320kbps", "quality": 320, "ext": "mp3", "size": "Unknown", "filesize_bytes": 0},
    {"id": "256", "type": "audio", "label": "MP3 256kbps", "quality": 256, "ext": "mp3", "size": "Unknown", "filesize_bytes": 0},
    {"id": "128", "type": "audio", "label": "MP3 128kbps", "quality": 128, "ext": "mp3", "size": "Unknown", "filesize_bytes": 0},
]


# ─── Info fetchers ───


def get_yt_info(url: str) -> dict:
    """Get YouTube metadata via oEmbed; formats are static presets."""
    m = YOUTUBE_RE.search(url)
    if not m:
        raise RuntimeError("Invalid YouTube URL")
    vid = m.group(1)

    oembed_url = (
        f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
    )
    try:
        req = urllib.request.Request(oembed_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            meta = json.loads(resp.read())
    except Exception:
        meta = {"title": "YouTube Video", "author_name": ""}

    return {
        "title": meta.get("title", "YouTube Video"),
        "thumbnail": f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg",
        "uploader": meta.get("author_name", ""),
        "duration": "",
        "video_formats": YT_VIDEO_PRESETS,
        "audio_formats": YT_AUDIO_PRESETS,
    }


def get_ig_info(url: str) -> dict:
    """Get Instagram media info via Cobalt."""
    data = cobalt_request({"url": url})
    status = data.get("status")
    if status == "error":
        code = data.get("error", {}).get("code", "unknown")
        raise RuntimeError(f"Instagram fetch failed: {code}")

    def _ig_format(direct_url: str, label: str = "Video", ext: str = "mp4", thumb: str = "") -> dict:
        size_str = "Unknown"
        size_bytes = 0
        try:
            head_req = urllib.request.Request(direct_url, method="HEAD", headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.instagram.com/",
            })
            with urllib.request.urlopen(head_req, timeout=10) as resp:
                cl = resp.headers.get("Content-Length")
                if cl:
                    size_bytes = int(cl)
                    size_str = format_size(size_bytes)
        except Exception:
            pass
        return {
            "id": "best",
            "type": "video" if ext == "mp4" else "photo",
            "label": label,
            "quality": 0,
            "ext": ext,
            "size": size_str,
            "filesize_bytes": size_bytes,
            "_direct_url": direct_url,
        }

    if status == "picker":
        items = data.get("picker", [])
        for item in items:
            if item.get("type") == "video":
                return {
                    "title": "Instagram Video",
                    "thumbnail": item.get("thumb", ""),
                    "video_formats": [_ig_format(item.get("url", ""), thumb=item.get("thumb", ""))],
                    "audio_formats": [],
                }
        first = items[0] if items else {}
        return {
            "title": "Instagram Photo",
            "thumbnail": first.get("thumb", ""),
            "video_formats": [_ig_format(first.get("url", ""), label="Photo", ext="jpg", thumb=first.get("thumb", ""))],
            "audio_formats": [],
        }

    if status in ("redirect", "tunnel"):
        return {
            "title": data.get("filename", "Instagram Media"),
            "thumbnail": "",
            "video_formats": [_ig_format(data.get("url", ""))],
            "audio_formats": [],
        }

    raise RuntimeError("Unknown cobalt response")


def get_info(url: str) -> dict:
    """Get video metadata without downloading."""
    platform, _ = detect_platform(url)
    if platform == "instagram":
        return get_ig_info(url)
    return get_yt_info(url)


# ─── Cobalt error mapping ───

COBALT_ERRORS = {
    "error.fetch.fail": "Could not fetch the video. It may be private or region-locked.",
    "error.fetch.empty": "No downloadable media found.",
    "error.content.video.unavailable": "Video is unavailable.",
    "error.content.video.region": "Video is region-locked.",
    "error.content.video.private": "Video is private.",
    "error.rate": "Rate limited. Try again in a few seconds.",
    "error.link.unsupported": "This URL is not supported.",
}


# ─── API Routes ───


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(PUBLIC_DIR / "index.html"))


@app.post("/api/info")
async def api_info(request: Request):
    """Get video metadata and available formats."""
    body = await request.json()
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(400, "URL required")

    platform, _ = detect_platform(url)
    if platform == "unknown":
        raise HTTPException(400, "Unsupported URL. Supported: YouTube, Instagram")

    try:
        info = await asyncio.to_thread(get_info, url)
    except RuntimeError as e:
        raise HTTPException(422, str(e))

    return {
        "platform": platform,
        "title": info.get("title", "Untitled"),
        "thumbnail": info.get("thumbnail", ""),
        "duration": info.get("duration", ""),
        "uploader": info.get("uploader", ""),
        "view_count": info.get("view_count", 0),
        "url": url,
        "video_formats": info.get("video_formats", []),
        "audio_formats": info.get("audio_formats", []),
        "_ig_direct_url": (info.get("video_formats") or [{}])[0].get("_direct_url"),
    }


@app.post("/api/download")
async def api_download(request: Request):
    """Stream download via Cobalt."""
    body = await request.json()
    url = body.get("url", "").strip()
    format_id = body.get("format_id", "max")
    mode = body.get("mode", "video")  # "video" or "audio"
    direct_url = body.get("direct_url")  # cobalt direct URL for IG

    if not url and not direct_url:
        raise HTTPException(400, "url or direct_url required")

    # ── Instagram: use cobalt direct URL ──
    if direct_url or (url and detect_platform(url)[0] == "instagram"):
        if not direct_url:
            cobalt = cobalt_request({"url": url})
            if cobalt.get("status") == "error":
                err = cobalt.get("error", {}).get("code", "unknown")
                raise HTTPException(422, COBALT_ERRORS.get(err, f"Cobalt error: {err}"))
            direct_url = cobalt.get("url")
            if not direct_url:
                raise HTTPException(422, "Cobalt returned no video URL")
        filename = body.get("filename", "instagram_video.mp4")
        return StreamingResponse(
            cobalt_stream(direct_url),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    platform, _ = detect_platform(url)
    if platform == "unknown":
        raise HTTPException(400, "Unsupported URL")

    # ── YouTube: cobalt download ──
    payload: dict = {"url": url}
    if mode == "audio":
        payload["downloadMode"] = "audio"
        payload["audioFormat"] = "mp3"
        payload["audioBitrate"] = format_id if format_id in ("320", "256", "128") else "320"
    else:
        payload["downloadMode"] = "auto"
        payload["videoQuality"] = format_id if format_id in ("max", "2160", "1440", "1080", "720", "480") else "max"
        payload["youtubeVideoCodec"] = "h264"
        payload["youtubeBetterAudio"] = True

    try:
        cobalt = await asyncio.to_thread(cobalt_request, payload, 120)
    except Exception as e:
        raise HTTPException(422, f"Cobalt request failed: {e}")

    status = cobalt.get("status")

    if status == "error":
        code = cobalt.get("error", {}).get("code", "unknown")
        raise HTTPException(422, COBALT_ERRORS.get(code, f"Download failed: {code}"))

    if status in ("tunnel", "redirect"):
        tunnel_url = cobalt.get("url")
        filename = cobalt.get("filename", "download.mp4")
        return StreamingResponse(
            cobalt_stream(tunnel_url),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if status == "picker":
        items = cobalt.get("picker", [])
        for item in items:
            if item.get("type") == "video":
                return StreamingResponse(
                    cobalt_stream(item["url"]),
                    media_type="application/octet-stream",
                    headers={"Content-Disposition": 'attachment; filename="video.mp4"'},
                )
        if items:
            return StreamingResponse(
                cobalt_stream(items[0]["url"]),
                media_type="application/octet-stream",
                headers={"Content-Disposition": 'attachment; filename="media.mp4"'},
            )
        raise HTTPException(422, "No downloadable items found")

    raise HTTPException(422, f"Unexpected cobalt response: {status}")


# ─── Health check ───


@app.get("/api/health")
async def health():
    cobalt_ok = False
    cobalt_version = ""
    try:
        req = urllib.request.Request(f"{COBALT_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            cobalt_ok = "cobalt" in data
            cobalt_version = data.get("cobalt", {}).get("version", "")
    except Exception:
        pass
    return {"status": "ok", "service": "mediadl", "cobalt": cobalt_ok, "cobalt_version": cobalt_version}


# ─── Cookie management (legacy, no longer used by cobalt) ───

COOKIES_FILE = Path(__file__).parent / "cookies.txt"
COOKIES_SOURCE = Path(__file__).parent / ".cookies-source.txt"


@app.post("/api/cookies")
async def upload_cookies(file: UploadFile = File(...)):
    """Upload cookies.txt (Netscape format). Kept for future use."""
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    if "# Netscape" not in text:
        raise HTTPException(400, "Invalid cookies file. Export from browser in Netscape format.")
    COOKIES_FILE.write_bytes(content)
    COOKIES_SOURCE.write_bytes(content)
    COOKIES_SOURCE.chmod(0o444)
    return {"status": "ok", "message": "Cookies uploaded (not required with Cobalt)"}


@app.get("/api/cookies/status")
async def cookies_status():
    return {
        "youtube": COOKIES_SOURCE.exists(),
        "instagram": False,
        "note": "Cobalt handles all downloads — cookies optional",
    }


@app.delete("/api/cookies")
async def delete_cookies():
    for f in [COOKIES_FILE, COOKIES_SOURCE]:
        if f.exists():
            f.unlink()
    return {"status": "ok", "message": "Cookies removed"}
