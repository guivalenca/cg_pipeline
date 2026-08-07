const PAGES = [
  { path: '/', label: 'Overview' },
  { path: '/structure', label: 'Structure' },
  { path: '/syllabi', label: 'Syllabi' },
  { path: '/sources', label: 'Sources' },
  { path: '/universe', label: 'Universe' },
  { path: '/runs', label: 'Runs' },
];

const mountedShells = new WeakMap();

function normalizePath(pathname) {
  if (pathname.length > 1 && pathname.endsWith('/')) return pathname.slice(0, -1);
  return pathname;
}

function currentPage(path, pathname) {
  return pathname === path ? ' aria-current="page"' : '';
}

function mountAdminShell(host) {
  if (!host) throw new TypeError('AdminShell host is required.');

  const existing = mountedShells.get(host);
  if (existing) return existing;

  const pathname = normalizePath(window.location.pathname);
  host.innerHTML = `
    <header class="admin-shell">
      <div class="admin-shell__identity">
        <a class="admin-shell__brand" href="/" aria-label="concept universe"${currentPage('/', pathname)}>
          <span class="admin-shell__wordmark">
            <span class="admin-shell__concept">concept</span>
            <span class="admin-shell__universe">universe</span>
          </span>
        </a>
        <span class="admin-shell__environment">local</span>
      </div>
      <nav class="admin-shell__primary" aria-label="Primary navigation">
        ${PAGES.map((page) => (
          `<a class="admin-shell__link" href="${page.path}"${currentPage(page.path, pathname)}>${page.label}</a>`
        )).join('')}
      </nav>
      <button class="admin-shell__theme" type="button" data-admin-theme aria-label="Toggle theme" aria-pressed="false">
        <span aria-hidden="true">◐</span>
      </button>
    </header>
  `;

  const themeButton = host.querySelector('[data-admin-theme]');
  const activePrimary = host.querySelector('.admin-shell__primary [aria-current="page"]');
  const documentRef = host.ownerDocument
    || (typeof document !== 'undefined' ? document : null);

  const setTheme = (theme) => {
    const dark = theme === 'dark';
    if (documentRef) {
      if (dark) documentRef.documentElement.dataset.theme = 'dark';
      else delete documentRef.documentElement.dataset.theme;
    }
    themeButton?.setAttribute?.('aria-pressed', String(dark));
  };

  let savedTheme = 'light';
  try {
    savedTheme = window.localStorage?.getItem('universe-theme') === 'dark' ? 'dark' : 'light';
  } catch {
    savedTheme = 'light';
  }
  setTheme(savedTheme);

  const handleTheme = () => {
    const current = documentRef?.documentElement?.dataset?.theme === 'dark';
    const next = current ? 'light' : 'dark';
    setTheme(next);
    try {
      window.localStorage?.setItem('universe-theme', next);
    } catch {
      // Theme storage is optional; the current document remains usable.
    }
    const ThemeEvent = window.CustomEvent || globalThis.CustomEvent;
    if (typeof window.dispatchEvent === 'function' && ThemeEvent) {
      window.dispatchEvent(new ThemeEvent('universe:themechange', {
        detail: { theme: next },
      }));
    }
  };

  const ensureActivePrimaryVisible = () => {
    const mobile = typeof window.matchMedia === 'function'
      && window.matchMedia('(max-width: 780px)').matches;
    if (!mobile) return;
    activePrimary?.scrollIntoView?.({
      block: 'nearest',
      inline: 'center',
    });
  };

  themeButton?.addEventListener('click', handleTheme);
  window.addEventListener?.('resize', ensureActivePrimaryVisible);
  if (typeof window.requestAnimationFrame === 'function') {
    window.requestAnimationFrame(ensureActivePrimaryVisible);
  } else {
    ensureActivePrimaryVisible();
  }

  const controller = Object.freeze({
    dispose() {
      themeButton?.removeEventListener?.('click', handleTheme);
      window.removeEventListener?.('resize', ensureActivePrimaryVisible);
      host.innerHTML = '';
      mountedShells.delete(host);
    },
  });
  mountedShells.set(host, controller);
  return controller;
}

function bootAdminShell() {
  const host = document.querySelector('[data-admin-shell]');
  if (host) mountAdminShell(host);
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootAdminShell, { once: true });
  } else {
    bootAdminShell();
  }
}
