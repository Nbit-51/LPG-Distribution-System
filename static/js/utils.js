/* utils.js — LPG System shared utilities */

/* ── AUTH ── */
function getToken()  { return localStorage.getItem('lpg_token'); }
function getUser()   { try { return JSON.parse(localStorage.getItem('lpg_user') || 'null'); } catch { return null; } }
function setAuth(token, user) { localStorage.setItem('lpg_token', token); localStorage.setItem('lpg_user', JSON.stringify(user)); }
function clearAuth() { localStorage.removeItem('lpg_token'); localStorage.removeItem('lpg_user'); }

function requireAuth() {
  if (!getToken()) { window.location.href = '/'; return false; }
  return true;
}
function requireConsumerAuth() {
  if (!localStorage.getItem('consumer_token')) { window.location.href = '/consumer-portal'; return false; }
  return true;
}

function logout() { clearAuth(); window.location.href = '/'; }

/* ── API HELPER ── */
const api = {
  async request(method, path, body) {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    if (res.status === 401) { clearAuth(); window.location.href = '/'; return; }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.message || `Error ${res.status}`);
    return data;
  },
  get(path)         { return this.request('GET', path); },
  post(path, body)  { return this.request('POST', path, body); },
  put(path, body)   { return this.request('PUT', path, body); },
  delete(path)      { return this.request('DELETE', path); },
  patch(path, body) { return this.request('PATCH', path, body); },
};

/* Consumer API */
const consumerApi = {
  async request(method, path, body) {
    const headers = { 'Content-Type': 'application/json' };
    const token = localStorage.getItem('consumer_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    if (res.status === 401) { localStorage.removeItem('consumer_token'); window.location.href = '/consumer-portal'; return; }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.message || `Error ${res.status}`);
    return data;
  },
  get(path)        { return this.request('GET', path); },
  post(path, body) { return this.request('POST', path, body); },
};

/* ── SIDEBAR ── */
const NAV = [
  { section: 'MAIN' },
  { id:'dashboard',  label:'Dashboard',  icon:'📊', href:'/dashboard' },
  { section: 'MANAGEMENT' },
  { id:'agencies',   label:'Agencies',   icon:'🏢', href:'/agencies-page' },
  { id:'consumer',   label:'Consumers',  icon:'👥', href:'/consumers-page' },
  { id:'bookings',   label:'Bookings',   icon:'📋', href:'/bookings-page' },
  { id:'agents',     label:'Agents',     icon:'🚚', href:'/agents-page' },
  { id:'supply',     label:'Supply',     icon:'🏭', href:'/supply-page' },
  { section: 'OPERATIONS' },
  { id:'allocation', label:'Allocation', icon:'⚡', href:'/allocation-page' },
  { id:'allocation-lab', label:'Allocation Lab', icon:'🧪', href:'/allocation-lab' },
  { id:'qr',         label:'QR Verify',  icon:'📱', href:'/qr-page' },
  { section: 'ADMIN' },
  { id:'reports',    label:'Reports',    icon:'📈', href:'/reports-page' },
  { id:'policies',   label:'Policies',   icon:'📜', href:'/policies-page' },
  { id:'invoices',   label:'Invoices',   icon:'🧾', href:'/invoices-page' },
  { section: 'LAB' },
  { id:'simulator',  label:'Playground', icon:'🔬', href:'/simulator-page' },
];

function renderSidebar(activePage) {
  const user = getUser();
  const el = document.getElementById('sidebar-mount');
  if (!el) return;

  const items = NAV.map(p => {
    if (p.section) return `<div class="nav-section-label">${p.section}</div>`;
    return `<a class="nav-item ${activePage === p.id ? 'active' : ''}" href="${p.href}">
      <span class="nav-icon">${p.icon}</span>
      <span>${p.label}</span>
    </a>`;
  }).join('');

  el.innerHTML = `
    <div class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-title">LPG System</div>
        <div class="brand-sub">Distribution Management</div>
      </div>
      ${items}
      <div class="sidebar-footer">
        <div class="user-name">${user?.username || user?.full_name || 'Admin'}</div>
        <a class="sign-out" onclick="logout()">Sign out</a>
      </div>
    </div>`;
}

/* ── TOAST ── */
function toast(msg, type = 'info') {
  let tc = document.getElementById('toast-container');
  if (!tc) { tc = document.createElement('div'); tc.id = 'toast-container'; document.body.appendChild(tc); }
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.textContent = msg;
  tc.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

/* ── BADGES ── */
function badge(val) {
  if (!val) return '<span class="text-muted">—</span>';
  const v = String(val).toLowerCase();
  const map = {
    pending:'pending', allocated:'allocated', delivered:'delivered', cancelled:'cancelled',
    active:'active', inactive:'inactive',
    domestic:'domestic', commercial:'commercial', essential:'essential',
  };
  const cls = map[v] || 'allocated';
  return `<span class="badge badge-${cls}">${val}</span>`;
}

/* ── DATE FORMAT ── */
function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' });
}
function fmtDateTime(d) {
  if (!d) return '—';
  return new Date(d).toLocaleString('en-IN', { day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit' });
}

/* ── EMPTY ROW ── */
function emptyRow(msg, cols = 7) {
  return `<tr><td colspan="${cols}" class="empty-state" style="padding:30px;text-align:center;color:#94a3b8;">${msg}</td></tr>`;
}

/* ── MODAL HELPERS ── */
function showModal(id) { document.getElementById(id).style.display = 'flex'; }
function hideModal(id) { document.getElementById(id).style.display = 'none'; }
function closeOnOverlay(id) {
  document.getElementById(id).addEventListener('click', e => {
    if (e.target.id === id) hideModal(id);
  });
}
