/* ═══════════════════════════════════════════════════════
   consent.js — Cookie notice (acknowledgement only)
   Plausible is cookie-free; no Accept/Decline needed.
   Include via <script src="/consent.js"></script>
   before </body> on every page.
═══════════════════════════════════════════════════════ */

(function () {
  const KEY = 'ts_consent';

  // Always load Plausible — it's cookie-free, no consent gate needed
  function loadPlausible() {
    if (document.querySelector('script[src*="plausible"]')) return;
    var s = document.createElement('script');
    s.defer = true;
    s.dataset.domain = 'terrasolana.com';
    s.src = 'https://plausible.io/js/script.js';
    document.head.appendChild(s);
  }
  loadPlausible();

  // Only show banner if not yet acknowledged
  if (localStorage.getItem(KEY)) return;

  // ── Build banner ────────────────────────────────────
  var banner = document.createElement('div');
  banner.id = 'cookie-banner';
  banner.setAttribute('role', 'dialog');
  banner.setAttribute('aria-label', 'Privacy notice');
  banner.innerHTML = [
    '<div class="cb-inner">',
    '  <p class="cb-text">We use <strong>no tracking cookies</strong>. ',
    '  <a class="cb-link" href="/privacy.html">Plausible Analytics</a> ',
    '  collects anonymous usage data only. ',
    '  <a class="cb-link" href="/privacy.html">Privacy Policy</a></p>',
    '  <div class="cb-btns">',
    '    <button id="cb-ack" class="cb-btn-accept">Got it</button>',
    '  </div>',
    '</div>',
  ].join('');

  // ── Styles ──────────────────────────────────────────
  var style = document.createElement('style');
  style.textContent = [
    '[data-theme="dark"] #cookie-banner{background:#1C1917;border-top-color:#2C2825;}',
    '#cookie-banner{',
    '  position:fixed;bottom:0;left:0;right:0;z-index:9999;',
    '  background:#fff;border-top:1px solid #E8E2D5;',
    '  box-shadow:0 -4px 24px rgba(0,0,0,0.08);',
    '  padding:14px 24px;',
    '}',
    '.cb-inner{',
    '  max-width:960px;margin:0 auto;',
    '  display:flex;align-items:center;gap:20px;flex-wrap:wrap;',
    '}',
    '.cb-text{',
    '  flex:1;font-size:13px;color:#44403C;line-height:1.5;',
    '  font-family:Inter,system-ui,sans-serif;margin:0;',
    '}',
    '[data-theme="dark"] .cb-text{color:#A8A29E;}',
    '.cb-text strong{color:#1C1917;}',
    '[data-theme="dark"] .cb-text strong{color:#F5F0E8;}',
    '.cb-link{color:#D4622A;text-decoration:underline;}',
    '.cb-btns{display:flex;gap:10px;flex-shrink:0;}',
    '.cb-btn-accept{',
    '  padding:8px 20px;border-radius:6px;font-size:13px;font-weight:600;',
    '  background:#D4622A;border:none;color:#fff;cursor:pointer;',
    '  font-family:Inter,system-ui,sans-serif;white-space:nowrap;',
    '}',
    '.cb-btn-accept:hover{background:#B85220;}',
    '@media(max-width:600px){',
    '  #cookie-banner{padding:12px 16px;}',
    '  .cb-inner{gap:12px;}',
    '  .cb-btns{width:100%;justify-content:flex-end;}',
    '}',
  ].join('');
  document.head.appendChild(style);
  document.body.appendChild(banner);

  // ── Dismiss ─────────────────────────────────────────
  document.getElementById('cb-ack').addEventListener('click', function () {
    localStorage.setItem(KEY, 'acknowledged');
    banner.remove();
  });
})();
