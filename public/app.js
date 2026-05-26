/* ═══════════════════════════════════════════════
   MediaDL — Frontend Logic v2
   ═══════════════════════════════════════════════ */

const API = location.origin;

// ─── Elements ───
const urlInput = document.getElementById('url-input');
const urlForm = document.getElementById('url-form');
const btnFetch = document.getElementById('btn-fetch');
const btnPaste = document.getElementById('btn-paste');
const loadingEl = document.getElementById('loading');
const resultsEl = document.getElementById('results');
const errorEl = document.getElementById('error-msg');
const toastEl = document.getElementById('toast');
const inputShell = document.getElementById('input-shell');
const platformDetect = document.getElementById('platform-detect');

// Info elements
const thumbImg = document.getElementById('thumb-img');
const durationBadge = document.getElementById('duration-badge');
const platformBadge = document.getElementById('platform-badge');
const videoTitle = document.getElementById('video-title');
const videoUploader = document.getElementById('video-uploader');
const videoStats = document.getElementById('video-stats');
const videoFormats = document.getElementById('video-formats');
const audioFormats = document.getElementById('audio-formats');

// ─── State ───
let currentInfo = null;

// ─── Theme ───
function initTheme() {
  const saved = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
}

document.getElementById('theme-toggle').addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
});

initTheme();

// ─── Toast ───
function showToast(msg, type = '') {
  const icons = {
    success: '✓',
    error: '✕',
    '': '•'
  };
  toastEl.innerHTML = `<span class="toast-icon">${icons[type] || '•'}</span>${msg}`;
  toastEl.className = 'toast' + (type ? ' ' + type : '');
  requestAnimationFrame(() => toastEl.classList.add('show'));
  clearTimeout(toastEl._timer);
  toastEl._timer = setTimeout(() => toastEl.classList.remove('show'), 3000);
}

// ─── Platform auto-detect ───
const YT_RE = /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)/;
const IG_RE = /instagram\.com\/(reels?|p|tv)\//;

function detectPlatform(url) {
  if (YT_RE.test(url)) return 'yt';
  if (IG_RE.test(url)) return 'ig';
  return null;
}

function updatePlatformDetect() {
  const url = urlInput.value.trim();
  const platform = detectPlatform(url);

  platformDetect.classList.remove('visible', 'yt', 'ig');
  inputShell.classList.remove('has-platform');

  if (platform) {
    platformDetect.classList.add('visible', platform);
    inputShell.classList.add('has-platform');

    if (platform === 'yt') {
      platformDetect.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>YouTube`;
    } else {
      platformDetect.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/></svg>Instagram`;
    }
  }
}

urlInput.addEventListener('input', updatePlatformDetect);
urlInput.addEventListener('change', updatePlatformDetect);

// ─── Format views ───
function formatViews(n) {
  if (!n) return '';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M views';
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K views';
  return n.toLocaleString() + ' views';
}

// ─── Render formats ───
function renderFormats(formats, container, mode) {
  container.innerHTML = '';

  if (!formats.length) {
    container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-tertiary);font-size:0.8125rem;">No formats available</div>';
    return;
  }

  formats.forEach((f, i) => {
    const item = document.createElement('div');
    item.className = 'format-item';
    item.style.animationDelay = `${i * 0.05}s`;
    item.style.animation = `fadeSlideUp 0.3s ${i * 0.05}s var(--transition-slow) both`;

    const iconClass = mode === 'audio' ? 'audio' : 'video';
    const iconSvg = mode === 'audio'
      ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>'
      : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>';

    item.innerHTML = `
      <div class="format-info">
        <div class="format-icon ${iconClass}">${iconSvg}</div>
        <div>
          <div class="format-label">${f.label}</div>
          <div class="format-detail">${f.ext.toUpperCase()} • ${f.size}</div>
        </div>
      </div>
      <div class="format-actions">
        <span class="format-size">${f.size}</span>
        <button class="btn-download" data-id="${f.id}" data-mode="${mode}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Download
        </button>
      </div>
    `;

    item.querySelector('.btn-download').addEventListener('click', () => {
      handleDownload(f.id, mode);
    });

    container.appendChild(item);
  });
}

// ─── Handle download ───
async function handleDownload(formatId, mode) {
  if (!currentInfo) return;

  showToast('Starting download...', 'success');

  const payload = {
    url: currentInfo.url,
    format_id: formatId,
    mode: mode,
  };

  // IG: use cobalt direct URL, skip yt-dlp format selection
  if (currentInfo._ig_direct_url) {
    payload.direct_url = currentInfo._ig_direct_url;
    payload.filename = (currentInfo.title || 'instagram_video').replace(/[^a-zA-Z0-9._-]/g, '_') + '.mp4';
  }

  try {
    const resp = await fetch(`${API}/api/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Download failed' }));
      throw new Error(err.detail || 'Download failed');
    }

    const blob = await resp.blob();
    const disposition = resp.headers.get('content-disposition') || '';
    const match = disposition.match(/filename="?([^";\n]+)"?/);
    const filename = match ? match[1] : `download.${mode === 'audio' ? 'mp3' : 'mp4'}`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    showToast('Download complete!', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ─── Fetch info ───
async function fetchInfo(url) {
  errorEl.classList.add('hidden');
  resultsEl.classList.add('hidden');
  loadingEl.classList.remove('hidden');
  btnFetch.disabled = true;
  btnFetch.classList.add('loading');

  try {
    const resp = await fetch(`${API}/api/info`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: 'Failed to fetch info' }));
      throw new Error(err.detail || 'Failed to fetch info');
    }

    const info = await resp.json();
    currentInfo = info;

    // Fill info card
    const thumbContainer = thumbImg.parentElement;
    const existingVideo = thumbContainer.querySelector('video');
    if (existingVideo) existingVideo.remove();

    if (info.platform === 'instagram' && info._ig_direct_url) {
      thumbImg.style.display = 'none';
      const vid = document.createElement('video');
      vid.src = info._ig_direct_url;
      vid.controls = true;
      vid.muted = true;
      vid.playsInline = true;
      vid.preload = 'metadata';
      vid.style.cssText = 'width:100%;height:100%;object-fit:contain;background:#000';
      thumbContainer.appendChild(vid);
      vid.addEventListener('loadedmetadata', () => {
        const mins = Math.floor(vid.duration / 60);
        const secs = Math.floor(vid.duration % 60);
        const dStr = `${mins}:${secs.toString().padStart(2, '0')}`;
        durationBadge.textContent = dStr;
        videoStats.textContent = dStr;
      });
    } else {
      thumbImg.style.display = '';
      thumbImg.src = info.thumbnail || '';
    }
    thumbImg.alt = info.title;
    durationBadge.textContent = info.duration;
    videoTitle.textContent = info.title;
    videoUploader.textContent = info.uploader || '';

    const stats = [formatViews(info.view_count), info.duration].filter(Boolean).join(' · ');
    videoStats.textContent = stats;

    // Platform badge
    platformBadge.className = 'platform-badge ' + info.platform;
    platformBadge.textContent = info.platform === 'youtube' ? '▶ YouTube' : '📸 Instagram';

    // Render formats
    renderFormats(info.video_formats, videoFormats, 'video');
    renderFormats(info.audio_formats, audioFormats, 'audio');

    // Show results
    loadingEl.classList.add('hidden');
    resultsEl.classList.remove('hidden');

    // Reset tabs
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector('.tab[data-tab="video"]').classList.add('active');
    videoFormats.classList.remove('hidden');
    audioFormats.classList.add('hidden');

  } catch (err) {
    loadingEl.classList.add('hidden');
    errorEl.textContent = err.message;
    errorEl.classList.remove('hidden');
  } finally {
    btnFetch.disabled = false;
    btnFetch.classList.remove('loading');
  }
}

// ─── Form submit ───
urlForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;
  fetchInfo(url);
});

// ─── Tab switching ───
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    const target = tab.dataset.tab;
    videoFormats.classList.toggle('hidden', target !== 'video');
    audioFormats.classList.toggle('hidden', target !== 'audio');
  });
});

// ─── Paste button ───
btnPaste.addEventListener('click', async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      urlInput.value = text;
      urlInput.focus();
      updatePlatformDetect();
      showToast('Pasted from clipboard');
    }
  } catch {
    showToast('Clipboard access denied', 'error');
  }
});

// ─── Auto-paste on focus (only if input empty) ───
urlInput.addEventListener('focus', async () => {
  if (urlInput.value.trim()) return;
  try {
    const text = await navigator.clipboard.readText();
    if (text && (text.includes('youtube.com') || text.includes('youtu.be') || text.includes('instagram.com'))) {
      urlInput.value = text;
      updatePlatformDetect();
      showToast('URL pasted from clipboard');
    }
  } catch {}
});

// ─── Cookie management ───
const cookieFile = document.getElementById('cookie-file');
const cookieMsg = document.getElementById('cookie-msg');
const cookieStatus = document.getElementById('cookie-status');
const btnCookieDelete = document.getElementById('btn-cookie-delete');

async function checkCookieStatus() {
  try {
    const resp = await fetch(`${API}/api/cookies/status`);
    const data = await resp.json();
    if (data.youtube) {
      cookieStatus.textContent = 'Active';
      cookieStatus.className = 'cookie-status active';
      btnCookieDelete.classList.remove('hidden');
    } else {
      cookieStatus.textContent = 'Not set';
      cookieStatus.className = 'cookie-status inactive';
      btnCookieDelete.classList.add('hidden');
    }
  } catch {}
}
checkCookieStatus();

cookieFile.addEventListener('change', async () => {
  const file = cookieFile.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const resp = await fetch(`${API}/api/cookies`, { method: 'POST', body: formData });
    const data = await resp.json();
    if (resp.ok) {
      showCookieMsg('YouTube cookies uploaded!', 'success');
      checkCookieStatus();
    } else {
      showCookieMsg(data.detail || 'Upload failed', 'error');
    }
  } catch (e) {
    showCookieMsg('Upload failed: ' + e.message, 'error');
  }
  cookieFile.value = '';
});

btnCookieDelete.addEventListener('click', async () => {
  try {
    await fetch(`${API}/api/cookies`, { method: 'DELETE' });
    showCookieMsg('YouTube cookies removed', 'success');
    checkCookieStatus();
  } catch (e) {
    showCookieMsg('Failed: ' + e.message, 'error');
  }
});

function showCookieMsg(text, type) {
  cookieMsg.textContent = text;
  cookieMsg.className = `cookie-msg ${type}`;
  cookieMsg.classList.remove('hidden');
  clearTimeout(cookieMsg._timer);
  cookieMsg._timer = setTimeout(() => cookieMsg.classList.add('hidden'), 5000);
}
