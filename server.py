import logging
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
COOKIES_SOURCE = Path(__file__).parent / ".cookies-source.txt"
BGUTIL_SERVER = Path.home() / "bgutil-ytdlp-pot-provider" / "server"
PO_TOKEN_CACHE: dict = {}  # Cache PO tokens to avoid regenerating


def restore_cookies():
    """Restore cookies from protected source before yt-dlp run (yt-dlp overwrites cookies.txt)."""
    if COOKIES_SOURCE.exists():
        import shutil
        shutil.copy(str(COOKIES_SOURCE), str(COOKIES_FILE))
        COOKIES_FILE.chmod(0o644)



def get_cookies_for_url(url: str) -> Path | None:
    """Pick the right cookies file based on URL platform. Instagram uses cobalt (no cookies)."""
    platform, _ = detect_platform(url)
    if platform == "instagram":
        return None  # Instagram handled by cobalt, no cookies needed
    if COOKIES_SOURCE.exists():
        restore_cookies()
        return COOKIES_FILE
    return None


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

def get_ytdlp_base_args() -> list[str]:
    """Get base yt-dlp args: JS runtime + remote components + optional PO token."""
    base = ["--js-runtimes", "node", "--remote-components", "ejs:github"]
    if COOKIES_FILE.exists():
        # Cookies + ejs for signature solving
        return base
    # No cookies — try PO token as fallback
    cached = PO_TOKEN_CACHE.get("po")
    if cached:
        po, vis, ts = cached
        import time
        if time.time() - ts < 300:  # 5 min cache
            return base + [
                "--extractor-args", f"youtube:player-client=web;po_token=web.gvs+{po}",
                "--extractor-args", f"youtube:visitor_data={vis}",
            ]
    token = generate_po_token()
    if token:
        po, vis = token
        import time
        PO_TOKEN_CACHE["po"] = (po, vis, time.time())
        return base + [
            "--extractor-args", f"youtube:player-client=web;po_token=web.gvs+{po}",
            "--extractor-args", f"youtube:visitor_data={vis}",
        ]
    return base


def run_ytdlp(args: list[str], timeout: int = 60) -> str:
    """Run yt-dlp and return stdout."""
    # Extract URL from args to determine cookies
    url = ""
    for a in args:
        if a.startswith("http"):
            url = a
            break
    cookies = get_cookies_for_url(url) if url else None

    cmd = ["yt-dlp", "--no-warnings", "--no-playlist", "--ignore-config"]
    if cookies:
        cmd += ["--cookies", str(cookies)]
    cmd += get_ytdlp_base_args()
    cmd += args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            err_msg = result.stderr.strip() or "yt-dlp failed"
            logging.error(f"yt-dlp failed: cmd={cmd}, stderr={err_msg[:500]}")
            raise RuntimeError(err_msg)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("Request timed out")
    except FileNotFoundError:
        raise RuntimeError("yt-dlp not installed")


COBALT_URL = "http://localhost:9000"


def cobalt_request(url: str) -> dict:
    """Call local cobalt API for IG/TikTok/other supported platforms."""
    import urllib.request
    payload = json.dumps({"url": url}).encode()
    req = urllib.request.Request(
        COBALT_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def get_ig_info(url: str) -> dict:
    """Get Instagram media info via cobalt (no cookies needed)."""
    data = cobalt_request(url)
    status = data.get("status")
    if status == "error":
        code = data.get("error", {}).get("code", "unknown")
        raise RuntimeError(f"Instagram fetch failed: {code}")

    def _ig_format(direct_url: str, label: str = "Video", ext: str = "mp4", thumb: str = "") -> dict:
        """Build IG format entry, fetching file size from CDN."""
        size_str = "Unknown"
        size_bytes = 0
        try:
            import urllib.request as _urlreq
            req = _urlreq.Request(direct_url, method="HEAD", headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.instagram.com/",
            })
            with _urlreq.urlopen(req, timeout=10) as resp:
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

    if status == "redirect":
        return {
            "title": data.get("filename", "Instagram Video"),
            "thumbnail": "",
            "video_formats": [_ig_format(data.get("url", ""))],
            "audio_formats": [],
        }

    if status == "tunnel":
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
        "video_formats": dedup(video_formats)[:6] if video_formats else info.get("video_formats", []),
        "audio_formats": dedup(audio_formats)[:4] if audio_formats else info.get("audio_formats", []),
        # IG/cobalt: include direct URL for download
        "_ig_direct_url": (info.get("video_formats") or [{}])[0].get("_direct_url"),
    }


@app.post("/api/download")
async def api_download(request: Request):
    """Stream download via yt-dlp (YouTube) or cobalt direct URL (Instagram)."""
    body = await request.json()
    url = body.get("url", "").strip()
    format_id = body.get("format_id", "")
    mode = body.get("mode", "video")  # "video" or "audio"
    direct_url = body.get("direct_url")  # cobalt direct URL for IG

    if not url and not direct_url:
        raise HTTPException(400, "url or direct_url required")

    # ── Instagram: always use cobalt (never yt-dlp) ──
    if direct_url or (url and detect_platform(url)[0] == "instagram"):
        import urllib.request as _urlreq
        if not direct_url:
            # Frontend didn't pass direct_url, fetch from cobalt now
            cobalt = cobalt_request(url)
            if cobalt.get("status") == "error":
                err = cobalt.get("error", {}).get("code", "unknown")
                raise HTTPException(422, f"Cobalt error: {err}")
            direct_url = cobalt.get("url")
            if not direct_url:
                raise HTTPException(422, "Cobalt returned no video URL")
        filename = body.get("filename", "instagram_video.mp4")

        def ig_stream():
            req = _urlreq.Request(direct_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.instagram.com/",
            })
            with _urlreq.urlopen(req, timeout=120) as resp:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    yield chunk

        return StreamingResponse(
            ig_stream(),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

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
    text = content.decode("utf-8", errors="ignore")
    if "youtube.com" not in text.lower() and "# Netscape" not in text:
        raise HTTPException(400, "Invalid cookies file. Export from browser in Netscape format.")
    COOKIES_FILE.write_bytes(content)
    # Save as protected source too
    COOKIES_SOURCE.write_bytes(content)
    COOKIES_SOURCE.chmod(0o444)
    return {"status": "ok", "platform": "youtube", "message": "YouTube cookies uploaded"}


@app.get("/api/cookies/status")
async def cookies_status():
    """Check which platform cookies are configured."""
    return {
        "youtube": COOKIES_SOURCE.exists(),
        "instagram": False,  # IG uses cobalt, no cookies needed
    }


@app.delete("/api/cookies")
async def delete_cookies():
    """Remove stored YouTube cookies."""
    for f in [COOKIES_FILE, COOKIES_SOURCE]:
        if f.exists():
            f.unlink()
    return {"status": "ok", "message": "YouTube cookies removed"}
