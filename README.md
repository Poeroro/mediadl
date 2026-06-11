# MediaDL

YouTube & Instagram media downloader — free, fast, no tracking.

**Live:** [dl.tempmeil.xyz](https://dl.tempmeil.xyz)

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)
![Cobalt](https://img.shields.io/badge/Cobalt-11.x-FF6B35?logo=cobalt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **YouTube** — download video (up to 4K) or audio-only via [Cobalt](https://github.com/imputnet/cobalt)
- **Instagram** — download Reels, Posts, and TV via Cobalt
- **Bot detection bypass** — Cobalt self-hosted with auto PO token (yt-session-generator)
- **No signup** — paste URL, pick format, download
- **Dark/Light theme** — toggle with one click
- **Mobile-first** — responsive UI, works on any device
- **No data stored** — zero logging, zero tracking

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI + uvicorn |
| Download engine | [Cobalt](https://github.com/imputnet/cobalt) self-hosted (YouTube + Instagram) |
| PO token | yt-session-generator (auto, no manual cookies) |
| Frontend | Vanilla HTML/CSS/JS |
| Reverse proxy | nginx |
| Deployment | systemd + Docker Compose |

## API

```
POST /api/info          — get video metadata + available formats
POST /api/download      — stream download (video or audio)
GET  /api/health        — health check (includes cobalt status)
POST /api/cookies       — upload cookies.txt (optional, multipart form)
GET  /api/cookies/status — check cookie status
DELETE /api/cookies     — remove uploaded cookies
```

### Example

```bash
# Fetch video info
curl -X POST https://Yourdomain.com/api/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Download video (720p)
curl -X POST https://Yourdomain.com/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "mode": "video", "format_id": "720"}' \
  -o video.mp4

# Download audio (MP3 320kbps)
curl -X POST https://Yourdomain.com/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "mode": "audio", "format_id": "320"}' \
  -o audio.mp3
```

## Setup

### Requirements

- Python 3.12+
- Docker + Docker Compose (for Cobalt)
- ffmpeg (for audio extraction)

### 1. Start Cobalt

```bash
cd cobalt/
docker compose up -d
```

This starts:
- `cobalt` — API server on `127.0.0.1:9000`
- `yt-session-generator` — auto PO token for YouTube
- `cobalt-watchtower` — auto-update Cobalt images

### 2. Start MediaDL

```bash
cd mediadl/
pip install fastapi uvicorn

python -m uvicorn server:app --host 0.0.0.0 --port 8181
```

### 3. Systemd (production)

```bash
sudo cp mediadl.service /etc/systemd/system/
sudo systemctl enable --now mediadl
```

### 4. Nginx

```nginx
server {
    server_name Yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8181;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
}
```

## Project Structure

```
mediadl/
├── server.py           # FastAPI backend (Cobalt-powered)
├── start.sh            # Launcher script
├── launch.py           # Process launcher
├── DESIGN.md           # UI design tokens & spec
├── public/
│   ├── index.html      # Frontend
│   ├── style.css       # Styles (dark/light theme)
│   └── app.js          # Client-side logic
└── README.md

cobalt/
└── docker-compose.yml  # Cobalt + yt-session-generator + Watchtower
```

## Cobalt Quality Presets

**Video:** Best Available, 2160p (4K), 1440p (2K), 1080p, 720p, 480p

**Audio:** MP3 320kbps, MP3 256kbps, MP3 128kbps

Codec: h264 (best compatibility) + Better Audio enabled.

## License

MIT
