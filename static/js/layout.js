// layout.js — Premium dark theme sidebar + shared helpers

function renderSidebar(activePage) {
  const user = getUser ? getUser() : null;
  const el = document.getElementById('sidebar-mount');
  if (!el) return;

  const NAV = [
    { section: 'Main' },
    { id: 'dashboard',  label: 'Dashboard',  icon: 'ti-layout-dashboard', href: '/dashboard' },
    { section: 'Management' },
    { id: 'agencies',   label: 'Agencies',   icon: 'ti-building',           href: '/agencies-page' },
    { id: 'consumers',  label: 'Consumers',  icon: 'ti-users',              href: '/?role=consumer' },
    { id: 'bookings',   label: 'Bookings',   icon: 'ti-clipboard-list',     href: '/bookings-page' },
    { id: 'agents',     label: 'Agents',     icon: 'ti-truck',              href: '/agents-page' },
    { id: 'supply',     label: 'Supply',     icon: 'ti-building-factory-2', href: '/supply-page' },
    { section: 'Operations' },
    { id: 'allocation', label: 'Allocation', icon: 'ti-bolt',               href: '/allocation-page' },
    { id: 'qr',         label: 'QR Verify',  icon: 'ti-qrcode',             href: '/qr-page' },
    { section: 'Analytics' },
    { id: 'reports',    label: 'Reports',    icon: 'ti-chart-bar',          href: '/reports-page' },
    { id: 'policies',   label: 'Policies',   icon: 'ti-file-certificate',   href: '/policies-page' },
    { id: 'invoices',   label: 'Invoices',   icon: 'ti-receipt',            href: '/invoices-page' },
    { section: 'Lab' },
    { id: 'simulator',  label: 'Playground', icon: 'ti-flask',              href: '/simulator-page' },
  ];

  const navHtml = NAV.map(n => {
    if (n.section) return `<div class="nav-section">${n.section}</div>`;
    return `
      <a class="nav-item${activePage === n.id ? ' active' : ''}" href="${n.href}">
        <span class="nav-icon"><i class="ti ${n.icon}" aria-hidden="true"></i></span>
        ${n.label}
      </a>`;
  }).join('');

  const name     = user?.full_name || user?.username || 'Admin';
  const role     = user?.role || 'admin';
  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();

  el.innerHTML = `
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-icon">
          <svg width="34" height="34" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <rect width="34" height="34" rx="9" fill="#6366f1"/>
            <rect x="8" y="8" width="8" height="8" rx="2" fill="rgba(255,255,255,0.9)"/>
            <rect x="18" y="8" width="8" height="8" rx="2" fill="rgba(255,255,255,0.5)"/>
            <rect x="8" y="18" width="8" height="8" rx="2" fill="rgba(255,255,255,0.5)"/>
            <rect x="18" y="18" width="8" height="8" rx="2" fill="rgba(255,255,255,0.25)"/>
          </svg>
        </div>
        <div class="brand-text">
          <div class="brand-name">LPG System</div>
          <div class="brand-sub">Distribution Mgmt</div>
        </div>
      </div>

      <nav class="sidebar-nav">${navHtml}</nav>

      <div class="sidebar-user">
        <div class="user-avatar">${initials}</div>
        <div class="user-info">
          <div class="user-name">${name}</div>
          <div class="user-role">${role}</div>
        </div>
        <button class="logout-btn"
          onclick="logout ? logout() : (localStorage.clear(), window.location.href='/')"
          title="Sign out"
          aria-label="Sign out">
          <i class="ti ti-power" aria-hidden="true"></i>
        </button>
      </div>
    </aside>`;
}


// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}

function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
  });
}

function badge(val) {
  const map = {
    domestic:  'badge-domestic',
    essential: 'badge-essential',
    commercial:'badge-commercial',
    pending:   'badge-pending',
    allocated: 'badge-allocated',
    delivered: 'badge-delivered',
    cancelled: 'badge-cancelled',
    active:    'badge-active',
    inactive:  'badge-inactive',
    crisis:    'badge-crisis',
  };
  return `<span class="badge ${map[val] || ''}">${val || '—'}</span>`;
}

/**
 * showToast(msg, type)
 * type: 'success' | 'error' | 'warning' | 'info'
 */
function showToast(msg, type = 'success') {
  const icons = { success: 'ti-check', error: 'ti-x', warning: 'ti-alert-triangle', info: 'ti-info-circle' };
  const icon  = icons[type] || 'ti-circle';

  let wrap = document.getElementById('toast-container');
  if (!wrap) {
    wrap = document.createElement('div');
    wrap.id = 'toast-container';
    document.body.appendChild(wrap);
  }

  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `
    <span class="toast-icon"><i class="ti ${icon}" aria-hidden="true"></i></span>
    <span>${msg}</span>`;
  wrap.appendChild(el);

  el.getBoundingClientRect(); // force reflow for animation
  el.classList.add('toast-visible');

  setTimeout(() => {
    el.classList.remove('toast-visible');
    el.addEventListener('transitionend', () => el.remove(), { once: true });
  }, 3500);
}

function openModal(id) {
  const m = document.getElementById(id);
  if (m) {
    m.classList.add('open');
    m.setAttribute('aria-hidden', 'false');
  }
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) {
    m.classList.remove('open');
    m.setAttribute('aria-hidden', 'true');
  }
}

// Close modals on backdrop click
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
    e.target.setAttribute('aria-hidden', 'true');
  }
});

// Close modals on Escape key
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => {
      m.classList.remove('open');
      m.setAttribute('aria-hidden', 'true');
    });
  }
});

function emptyRow(msg, cols = 8) {
  return `<tr>
    <td colspan="${cols}" class="table-empty">
      <span class="empty-icon"><i class="ti ti-inbox" aria-hidden="true"></i></span>
      <span>${msg}</span>
    </td>
  </tr>`;
}

// ── Interactive Cursor Glow & Spotlight Effects ───────────────────────────────────────────────────
(function initUIEnhancements() {
  if (typeof window === 'undefined' || !document) return;

  // 1. Create Ambient Background Glow Blobs
  const ambientContainer = document.createElement('div');
  ambientContainer.className = 'ambient-glow-container';
  ambientContainer.innerHTML = `
    <div class="ambient-blob blob-indigo"></div>
    <div class="ambient-blob blob-teal"></div>
    <div class="ambient-blob blob-purple"></div>
  `;
  document.body.prepend(ambientContainer);

  // 2. Cursor Trail & Click Sparks
  const colors = [
    'rgba(99, 102, 241, 0.8)', // indigo
    'rgba(20, 184, 166, 0.8)', // teal
    'rgba(245, 158, 11, 0.8)', // amber
    'rgba(239, 68, 68, 0.8)',  // red
    'rgba(16, 185, 129, 0.8)', // green
    'rgba(168, 85, 247, 0.8)'  // purple
  ];
  
  let lastSpawn = 0;
  
  function createGlow(x, y, isClick = false) {
    const el = document.createElement('div');
    el.className = 'cursor-glow';
    el.style.left = x + 'px';
    el.style.top = y + 'px';
    
    const color = colors[Math.floor(Math.random() * colors.length)];
    el.style.background = `radial-gradient(circle, ${color} 0%, transparent 70%)`;
    
    if (isClick) {
      el.style.width = '45px';
      el.style.height = '45px';
      el.style.animationDuration = '0.6s';
      el.style.boxShadow = `0 0 25px ${color}`;
    } else {
      el.style.boxShadow = `0 0 8px ${color}`;
    }
    
    document.body.appendChild(el);
    el.addEventListener('animationend', () => el.remove());
  }

  // 3. Card Spotlight Hover Effect (delegated to be super efficient)
  document.addEventListener('mousemove', (e) => {
    const now = performance.now();
    // Cursor trail spawn rate check
    if (now - lastSpawn > 55) {
      createGlow(e.pageX, e.pageY);
      lastSpawn = now;
    }

    // Find if we are hovering over a card/interactive container
    const card = e.target.closest('.card, .stat-card, .consumer-card, .modal-content, .sidebar, .btn');
    if (card) {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty('--mx', `${x}px`);
      card.style.setProperty('--my', `${y}px`);
    }
  });

  document.addEventListener('click', (e) => {
    createGlow(e.pageX, e.pageY, true);
    for (let i = 1; i <= 4; i++) {
       setTimeout(() => {
         createGlow(
           e.pageX + (Math.random() - 0.5) * 40, 
           e.pageY + (Math.random() - 0.5) * 40, 
           true
         );
       }, i * 35);
    }
  });
})();

