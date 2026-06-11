# MediaDL

YouTube & Instagram media downloader — free, fast, no tracking.

**Live:** [dl.tempmeil.xyz](https://dl.tempmeil.xyz)

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- **YouTube** — download video (up to 4K) or audio-only, format picker with file size preview
- **Instagram** — download Reels, Posts, and TV via cobalt backend
- **No signup** — paste URL, pick format, download
- **Cookie upload** — bypass YouTube bot detection with your browser cookies
- **Auto PO token** — bgutil integration for YouTube PO token generation
- **Dark/Light theme** — toggle with one click
- **Mobile-first** — responsive UI, works on any device
- **No data stored** — zero logging, zero tracking

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI + uvicorn |
| Download engine | yt-dlp (YouTube), cobalt (Instagram) |
| Frontend | Vanilla HTML/CSS/JS |
| Reverse proxy | nginx |
| Deployment | systemd service |

## API

```
POST /api/info          — get video metadata + available formats
POST /api/download      — stream download (video or audio)
GET  /api/health        — health check
POST /api/cookies       — upload cookies.txt (multipart form)
GET  /api/cookies/status — check if cookies are active
DELETE /api/cookies     — remove uploaded cookies
```

### Example

```bash
# Fetch video info
curl -X POST https://dl.tempmeil.xyz/api/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Download (streams the file)
curl -X POST https://dl.tempmeil.xyz/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format_id": "best"}' \
  -o video.mp4
```

## Setup

### Requirements

- Python 3.12+
- yt-dlp
- ffmpeg (for audio extraction)
- Node.js (for PO token via bgutil)

### Install

```bash
git clone git@github.com:Poeroro/mediadl.git
cd mediadl

pip install fastapi uvicorn

# Run
python -m uvicorn server:app --host 0.0.0.0 --port 8181
```

### Systemd (production)

```bash
sudo cp mediadl.service /etc/systemd/system/
sudo systemctl enable --now mediadl
```

### Nginx

```nginx
server {
    server_name dl.tempmeil.xyz;

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
├── server.py           # FastAPI backend
├── launch.py           # Launcher script
├── cookies.txt         # YouTube cookies (gitignored)
├── .cookies-source.txt # Cookie source metadata
├── DESIGN.md           # UI design tokens & spec
├── public/
│   ├── index.html      # Frontend
│   ├── style.css       # Styles (dark/light theme)
│   └── app.js          # Client-side logic
└── README.md
```

## YouTube Cookie Setup

YouTube blocks server-side downloads. To bypass:

1. Install [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) extension
2. Go to [youtube.com](https://youtube.com), make sure you're logged in
3. Click extension icon → Export → saves `cookies.txt`
4. Upload via the UI (click "YouTube Cookies" section) or replace `cookies.txt` in project root

## Design

Dark-first UI. Pure black (#050708) background with subtle green radial glow. See [DESIGN.md](DESIGN.md) for full spec.

## License

MIT
