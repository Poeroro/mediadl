/* ═══════════════════════════════════════════════
   MediaDL — Frontend Logic
   ═══════════════════════════════════════════════ */

const API = location.origin;

// ─── Elements ───
const urlInput = document.getElementById('url-input');
const urlForm = document.getElementById('url-form');
const btnFetch = document.getElementById('btn-fetch');
const loadingEl = document.getElementById('loading');
const resultsEl = document.getElementById('results');
const errorEl = document.getElementById('error-msg');
const toastEl = document.getElementById('toast');

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
  toastEl.textContent = msg;
  toastEl.className = 'toast' + (type ? ' ' + type : '');
  requestAnimationFrame(() => toastEl.classList.add('show'));
  setTimeout(() => toastEl.classList.remove('show'), 3000);
}

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
    container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-tertiary);font-size:0.875rem;">No formats available</div>';
    return;
  }

  formats.forEach(f => {
    const item = document.createElement('div');
    item.className = 'format-item';

    const iconClass = mode === 'audio' ? 'audio' : 'video';
    const iconSvg = mode === 'audio'
      ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>'
      : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>';

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
        <button class="btn btn-download btn-small" data-id="${f.id}" data-mode="${mode}">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Download
        </button>
      </div>
    `;

    item.querySelector('.btn-download').addEventListener('click', (e) => {
      handleDownload(f.id, mode);
    });

    container.appendChild(item);
  });
}

// ─── Handle download ───
async function handleDownload(formatId, mode) {
  if (!currentInfo) return;

  showToast('Starting download...', 'success');

  try {
    const resp = await fetch(`${API}/api/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: currentInfo.url,
        format_id: formatId,
        mode: mode,
      }),
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
    thumbImg.src = info.thumbnail || '';
    thumbImg.alt = info.title;
    durationBadge.textContent = info.duration;
    videoTitle.textContent = info.title;
    videoUploader.textContent = info.uploader || '';

    const stats = [formatViews(info.view_count), info.duration].filter(Boolean).join(' • ');
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

// ─── Paste from clipboard ───
urlInput.addEventListener('focus', async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text && (text.includes('youtube.com') || text.includes('youtu.be') || text.includes('instagram.com'))) {
      urlInput.value = text;
      showToast('URL pasted from clipboard');
    }
  } catch {}
});

// ─── Cookie management ───
const cookieFile = document.getElementById('cookie-file');
const cookieMsg = document.getElementById('cookie-msg');
const cookieStatus = document.getElementById('cookie-status');
const btnCookieDelete = document.getElementById('btn-cookie-delete');

// Check cookie status on load
async function checkCookieStatus() {
  try {
    const resp = await fetch(`${API}/api/cookies/status`);
    const data = await resp.json();
    if (data.has_cookies) {
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

// Upload cookies
cookieFile.addEventListener('change', async () => {
  const file = cookieFile.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const resp = await fetch(`${API}/api/cookies`, { method: 'POST', body: formData });
    const data = await resp.json();
    if (resp.ok) {
      showCookieMsg('Cookies uploaded! YouTube downloads should work now.', 'success');
      checkCookieStatus();
    } else {
      showCookieMsg(data.detail || 'Upload failed', 'error');
    }
  } catch (e) {
    showCookieMsg('Upload failed: ' + e.message, 'error');
  }
  cookieFile.value = '';
});

// Delete cookies
btnCookieDelete.addEventListener('click', async () => {
  try {
    await fetch(`${API}/api/cookies`, { method: 'DELETE' });
    showCookieMsg('Cookies removed', 'success');
    checkCookieStatus();
  } catch (e) {
    showCookieMsg('Failed: ' + e.message, 'error');
  }
});

function showCookieMsg(text, type) {
  cookieMsg.textContent = text;
  cookieMsg.className = `cookie-msg ${type}`;
  cookieMsg.classList.remove('hidden');
  setTimeout(() => cookieMsg.classList.add('hidden'), 5000);
}
