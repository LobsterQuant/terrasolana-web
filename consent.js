/* ═══════════════════════════════════════════════════════
   consent.js — Cookie consent + Plausible loader
   Include ONCE via <script src="/consent.js"></script>
   before </body> on every page.
═══════════════════════════════════════════════════════ */

(function () {
  const KEY = 'ts_consent';

  // ── Load Plausible (only if consented) ──────────────
  function loadPlausible() {
    if (document.querySelector('script[src*="plausible"]')) return;
    var s = document.createElement('script');
    s.defer = true;
    s.dataset.domain = 'terrasolana.com';
    s.src = 'https://plausible.io/js/script.js';
    document.head.appendChild(s);
  }

  // ── Check stored preference ─────────────────────────
  var stored = localStorage.getItem(KEY);
  if (stored === 'accepted') { loadPlausible(); return; }
  if (stored === 'declined') { return; } // banner already answered

  // ── Build banner ────────────────────────────────────
  var banner = document.createElement('div');
  banner.id = 'cookie-banner';
  banner.setAttribute('role', 'dialog');
  banner.setAttribute('aria-label', 'Cookie consent');
  banner.innerHTML = [
    '<div class="cb-inner">',
    '  <p class="cb-text">We use <strong>Plausible Analytics</strong> (privacy-friendly, no personal data) to understand how visitors use this site. No cookies required for the site to work.</p>',
    '  <div class="cb-btns">',
    '    <button id="cb-decline" class="cb-btn-decline">Decline</button>',
    '    <button id="cb-accept"  class="cb-btn-accept">Accept analytics</button>',
    '  </div>',
    '</div>',
  ].join('');

  // ── Styles (injected — no extra CSS file needed) ────
  var style = document.createElement('style');
  style.textContent = [
    '#cookie-banner{',
    '  position:fixed;bottom:0;left:0;right:0;z-index:9999;',
    '  background:#fff;border-top:1px solid #E8E2D5;',
    '  box-shadow:0 -4px 24px rgba(0,0,0,0.08);',
    '  padding:16px 24px;',
    '}',
    '.cb-inner{',
    '  max-width:960px;margin:0 auto;',
    '  display:flex;align-items:center;gap:24px;flex-wrap:wrap;',
    '}',
    '.cb-text{',
    '  flex:1;font-size:13px;color:#44403C;line-height:1.5;',
    '  font-family:Inter,system-ui,sans-serif;margin:0;',
    '}',
    '.cb-text strong{color:#1C1917;}',
    '.cb-btns{display:flex;gap:10px;flex-shrink:0;}',
    '.cb-btn-decline{',
    '  padding:8px 18px;border-radius:6px;font-size:13px;font-weight:600;',
    '  background:transparent;border:1.5px solid #C8BFA8;color:#78716C;cursor:pointer;',
    '  font-family:Inter,system-ui,sans-serif;',
    '}',
    '.cb-btn-decline:hover{border-color:#78716C;color:#1C1917;}',
    '.cb-btn-accept{',
    '  padding:8px 18px;border-radius:6px;font-size:13px;font-weight:600;',
    '  background:#D4622A;border:none;color:#fff;cursor:pointer;',
    '  font-family:Inter,system-ui,sans-serif;',
    '}',
    '.cb-btn-accept:hover{background:#B85220;}',
    '@media(max-width:600px){',
    '  #cookie-banner{padding:14px 16px;}',
    '  .cb-inner{gap:14px;}',
    '  .cb-btns{width:100%;justify-content:flex-end;}',
    '}',
  ].join('');
  document.head.appendChild(style);
  document.body.appendChild(banner);

  // ── Button handlers ─────────────────────────────────
  document.getElementById('cb-accept').addEventListener('click', function () {
    localStorage.setItem(KEY, 'accepted');
    banner.remove();
    loadPlausible();
  });

  document.getElementById('cb-decline').addEventListener('click', function () {
    localStorage.setItem(KEY, 'declined');
    banner.remove();
  });
})();
