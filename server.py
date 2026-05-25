"""
MediaDL — FastAPI backend with yt-dlp
YouTube + Instagram media downloader
"""

import asyncio
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
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


# ─── yt-dlp helpers ───

COOKIES_FILE = Path(__file__).parent / "cookies.txt"
BGUTIL_SERVER = Path.home() / "bgutil-ytdlp-pot-provider" / "server"
PO_TOKEN_CACHE: dict = {}  # Cache PO tokens to avoid regenerating per request


def generate_po_token() -> tuple[str, str] | None:
    """Generate PO token using bgutil. Returns (po_token, visitor_data) or None."""
    script = BGUTIL_SERVER / "build" / "generate_once.js"
    if not script.exists():
        return None
    try:
        result = subprocess.run(
            ["node", str(script)],
            capture_output=True, text=True, timeout=30,
            cwd=str(BGUTIL_SERVER),
        )
        if result.returncode != 0:
            return None
        # Parse JSON from last line of stdout
        for line in reversed(result.stdout.strip().split("\n")):
            line = line.strip()
            if line.startswith("{"):
                data = json.loads(line)
                po = data.get("poToken", "")
                vis = data.get("contentBinding", "")
                if po and vis:
                    return po, vis
        return None
    except Exception:
        return None


def get_po_args() -> list[str]:
    """Get PO token args, with caching."""
    cached = PO_TOKEN_CACHE.get("po")
    if cached:
        po, vis, ts = cached
        import time
        if time.time() - ts < 300:  # 5 min cache
            return [
                "--js-runtimes", "node",
                "--extractor-args", f"youtube:player-client=web;po_token=web.gvs+{po}",
                "--extractor-args", f"youtube:visitor_data={vis}",
            ]
    token = generate_po_token()
    if token:
        po, vis = token
        import time
        PO_TOKEN_CACHE["po"] = (po, vis, time.time())
        return [
            "--js-runtimes", "node",
            "--extractor-args", f"youtube:player-client=web;po_token=web.gvs+{po}",
            "--extractor-args", f"youtube:visitor_data={vis}",
        ]
    return ["--js-runtimes", "node"]


def run_ytdlp(args: list[str], timeout: int = 60) -> str:
    """Run yt-dlp and return stdout."""
    cmd = ["yt-dlp", "--no-warnings", "--no-playlist"]
    if COOKIES_FILE.exists():
        cmd += ["--cookies", str(COOKIES_FILE)]
    cmd += get_po_args()
    cmd += args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "yt-dlp failed")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("Request timed out")
    except FileNotFoundError:
        raise RuntimeError("yt-dlp not installed")


def get_info(url: str) -> dict:
    """Get video metadata without downloading."""
    raw = run_ytdlp(["--dump-json", "--no-download", url])
    return json.loads(raw)


def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "0:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_size(bytes_val: Optional[int]) -> str:
    if not bytes_val:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"


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

    platform, video_id = detect_platform(url)
    if platform == "unknown":
        raise HTTPException(400, "Unsupported URL. Supported: YouTube, Instagram")

    try:
        info = await asyncio.to_thread(get_info, url)
    except RuntimeError as e:
        msg = str(e)
        # Clean up yt-dlp error messages
        if "Sign in to confirm" in msg or "bot" in msg.lower():
            msg = "YouTube requires sign-in for this video. Try another video or use cookies."
        elif "ERROR:" in msg:
            msg = msg.split("ERROR:")[-1].strip()[:200]
        raise HTTPException(422, msg)

    # Build format list
    formats = []
    seen = set()

    for f in info.get("formats", []):
        fid = f.get("format_id", "")
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        ext = f.get("ext", "")
        height = f.get("height")
        width = f.get("width")
        abr = f.get("abr")
        vbr = f.get("vbr")
        filesize = f.get("filesize") or f.get("filesize_approx")
        format_note = f.get("format_note", "")

        # Video+Audio
        if vcodec != "none" and height:
            label = f"{height}p"
            key = f"video-{height}"
            if key not in seen:
                seen.add(key)
                formats.append({
                    "id": fid,
                    "type": "video",
                    "label": label,
                    "quality": height,
                    "ext": ext,
                    "size": format_size(filesize),
                    "filesize_bytes": filesize or 0,
                })

        # Audio only
        elif vcodec == "none" and acodec != "none" and abr:
            label = f"{int(abr)}kbps"
            key = f"audio-{int(abr)}"
            if key not in seen:
                seen.add(key)
                formats.append({
                    "id": fid,
                    "type": "audio",
                    "label": label,
                    "quality": int(abr),
                    "ext": ext if ext in ("mp3", "m4a", "opus", "wav") else "mp3",
                    "size": format_size(filesize),
                    "filesize_bytes": filesize or 0,
                })

    # Sort: video by quality desc, audio by bitrate desc
    video_formats = sorted(
        [f for f in formats if f["type"] == "video"],
        key=lambda x: x["quality"], reverse=True
    )
    audio_formats = sorted(
        [f for f in formats if f["type"] == "audio"],
        key=lambda x: x["quality"], reverse=True
    )

    # Deduplicate by quality label, keep best
    def dedup(fmts):
        best = {}
        for f in fmts:
            key = f["label"]
            if key not in best or f["filesize_bytes"] > best[key]["filesize_bytes"]:
                best[key] = f
        return list(best.values())

    return {
        "platform": platform,
        "title": info.get("title", "Untitled"),
        "thumbnail": info.get("thumbnail", ""),
        "duration": format_duration(info.get("duration")),
        "uploader": info.get("uploader", ""),
        "view_count": info.get("view_count", 0),
        "url": url,
        "video_formats": dedup(video_formats)[:6],
        "audio_formats": dedup(audio_formats)[:4],
    }


@app.post("/api/download")
async def api_download(request: Request):
    """Stream download via yt-dlp."""
    body = await request.json()
    url = body.get("url", "").strip()
    format_id = body.get("format_id", "")
    mode = body.get("mode", "video")  # "video" or "audio"

    if not url or not format_id:
        raise HTTPException(400, "url and format_id required")

    platform, _ = detect_platform(url)
    if platform == "unknown":
        raise HTTPException(400, "Unsupported URL")

    # Create temp file
    tmpdir = tempfile.mkdtemp(prefix="mediadl_")
    output_tpl = os.path.join(tmpdir, "%(title).80s.%(ext)s")

    if mode == "audio":
        args = [
            "-f", format_id,
            "-x", "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", output_tpl,
            url,
        ]
    else:
        args = [
            "-f", f"{format_id}+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", output_tpl,
            url,
        ]

    try:
        await asyncio.to_thread(run_ytdlp, args, timeout=300)
    except RuntimeError as e:
        raise HTTPException(422, str(e))

    # Find downloaded file
    files = list(Path(tmpdir).glob("*"))
    if not files:
        raise HTTPException(422, "Download failed — no output file")

    filepath = files[0]
    filename = filepath.name

    # Stream file
    def cleanup():
        try:
            filepath.unlink()
            Path(tmpdir).rmdir()
        except:
            pass

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/octet-stream",
        background=cleanup,
    )


# ─── Health check ───

@app.get("/api/health")
async def health():
    has_cookies = COOKIES_FILE.exists()
    return {"status": "ok", "service": "mediadl", "has_cookies": has_cookies}


# ─── Cookie management ───

from fastapi import UploadFile, File

@app.post("/api/cookies")
async def upload_cookies(file: UploadFile = File(...)):
    """Upload YouTube cookies.txt (Netscape format)."""
    content = await file.read()
    # Validate basic format
    text = content.decode("utf-8", errors="ignore")
    if "youtube.com" not in text.lower() and "# Netscape" not in text:
        raise HTTPException(400, "Invalid cookies file. Export from browser in Netscape format.")
    COOKIES_FILE.write_bytes(content)
    return {"status": "ok", "message": "Cookies uploaded successfully"}


@app.get("/api/cookies/status")
async def cookies_status():
    """Check if cookies are configured."""
    return {"has_cookies": COOKIES_FILE.exists()}


@app.delete("/api/cookies")
async def delete_cookies():
    """Remove stored cookies."""
    if COOKIES_FILE.exists():
        COOKIES_FILE.unlink()
    return {"status": "ok", "message": "Cookies removed"}
