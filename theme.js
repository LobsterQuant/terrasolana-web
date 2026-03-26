/* theme.js — dark/light mode toggle
   Include before </body> on every page (after consent.js) */
(function () {
  const KEY = 'ts_theme';

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const btn = document.getElementById('themeToggle');
    if (btn) btn.textContent = theme === 'dark' ? '🌙' : '☀️';
  }

  // On load: apply stored pref or system default
  const stored = localStorage.getItem(KEY);
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const initial = stored || (prefersDark ? 'dark' : 'light');
  apply(initial);

  // Wire up button (runs after DOM ready)
  function wireButton() {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;
    // Set correct icon after DOM exists
    apply(document.documentElement.getAttribute('data-theme') || initial);
    btn.addEventListener('click', function () {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      localStorage.setItem(KEY, next);
      apply(next);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireButton);
  } else {
    wireButton();
  }
})();
