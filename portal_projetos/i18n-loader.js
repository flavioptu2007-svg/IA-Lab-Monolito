/* ============================================================
   i18n Loader — Include this ONE script tag in any HTML game
   <script src="i18n-loader.js"></script>
   Then add data-i18n="games.memory.title" to your elements
   ============================================================ */

(function() {
  // Load order: engine → locales
  const scripts = [
    'i18n.js',
    'i18n/pt-BR.js',
    'i18n/en-US.js',
  ];

  let loaded = 0;
  const base = document.currentScript ? document.currentScript.src.replace(/\/[^/]+$/, '') : '.';

  function loadNext() {
    if (loaded >= scripts.length) {
      // All loaded — init and update DOM
      I18N.init('pt-BR');
      I18N.injectCSS();
      I18N.updateDOM();

      // Re-run on locale change
      document.addEventListener('i18n-changed', () => {
        I18N.updateDOM();
      });

      document.dispatchEvent(new CustomEvent('i18n-loaded'));
      return;
    }

    const script = document.createElement('script');
    script.src = `${base}/${scripts[loaded]}`;
    script.onload = () => { loaded++; loadNext(); };
    script.onerror = () => {
      console.error(`[i18n] Failed to load ${scripts[loaded]}`);
      loaded++; loadNext(); // continue anyway
    };
    document.head.appendChild(script);
  }

  loadNext();
})();
