// ── API base ──────────────────────────────────────────────
const API = 'http://127.0.0.1:8000';

function getToken() { return localStorage.getItem('lpg_token'); }
function getAdmin()  { return JSON.parse(localStorage.getItem('lpg_admin') || 'null'); }

async function apiFetch(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  const token   = getToken();
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(API + path, { ...opts, headers });
  if (res.status === 401) { logout(); return; }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
  return data;
}

async function apiPost(path, body)  { return apiFetch(path, { method:'POST',   body: JSON.stringify(body) }); }
async function apiPatch(path, body) { return apiFetch(path, { method:'PATCH',  body: JSON.stringify(body) }); }
async function apiDelete(path)      { return apiFetch(path, { method:'DELETE' }); }
async function apiGet(path)         { return apiFetch(path, { method:'GET' }); }

// ── Auth ──────────────────────────────────────────────────
function logout() {
  localStorage.removeItem('lpg_token');
  localStorage.removeItem('lpg_admin');
  window.location.href = '/static/login.html';
}

function requireAuth() {
  if (!getToken()) { logout(); return false; }
  const admin = getAdmin();
  if (admin) {
    document.querySelectorAll('.admin-name').forEach(el => el.textContent = admin.full_name);
    document.querySelectorAll('.admin-role').forEach(el => el.textContent = admin.role);
    document.querySelectorAll('.admin-badge').forEach(el => el.textContent = admin.role);
  }
  return true;
}

// ── Toast notifications ───────────────────────────────────
function toast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `alert alert-${type} fade-up`;
  el.style.cssText = 'position:fixed;top:20px;right:20px;z-index:999;min-width:260px;max-width:420px;box-shadow:0 4px 20px rgba(0,0,0,.15)';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Modal helpers ─────────────────────────────────────────
function openModal(id)  { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

// ── Badge helper ──────────────────────────────────────────
function badge(text, cls) {
  return `<span class="badge badge-${cls}">${text}</span>`;
}

function statusBadge(status) {
  const map = { pending:'pending', approved:'approved', allocated:'allocated', cancelled:'cancelled',
                domestic:'domestic', essential:'essential', commercial:'commercial' };
  return badge(status, map[status] || 'pending');
}

// ── Pagination ────────────────────────────────────────────
function renderPagination(containerId, total, page, pageSize, onPage) {
  const el    = document.getElementById(containerId);
  const pages = Math.ceil(total / pageSize);
  if (pages <= 1) { el.innerHTML = ''; return; }
  let html = `<button class="pg-btn" onclick="(${onPage})(${page-1})" ${page===1?'disabled':''}>‹ Prev</button>`;
  for (let i = 1; i <= pages; i++) {
    if (i === 1 || i === pages || Math.abs(i - page) <= 1)
      html += `<button class="pg-btn ${i===page?'active':''}" onclick="(${onPage})(${i})">${i}</button>`;
    else if (Math.abs(i - page) === 2)
      html += `<span style="padding:0 4px;color:var(--ink3)">…</span>`;
  }
  html += `<button class="pg-btn" onclick="(${onPage})(${page+1})" ${page===pages?'disabled':''}>Next ›</button>`;
  el.innerHTML = html;
}

// ── Format helpers ────────────────────────────────────────
function fmtDate(d)  { return d ? new Date(d).toLocaleDateString('en-IN') : '—'; }
function fmtDT(d)    { return d ? new Date(d).toLocaleString('en-IN')     : '—'; }
function fmtNum(n)   { return (n ?? 0).toLocaleString('en-IN'); }

// ── Sidebar active state ──────────────────────────────────
function setActiveNav(page) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
}

// ── Confirm dialog ────────────────────────────────────────
function confirm(msg) { return window.confirm(msg); }