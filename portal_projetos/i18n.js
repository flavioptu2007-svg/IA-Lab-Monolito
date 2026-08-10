/* ============================================================
   i18n — Sistema de Internacionalização para Jogos Educativos
   Self-contained, zero dependências, funciona offline
   ============================================================ */

const I18N = (() => {
  'use strict';

  // ── LOCALES ────────────────────────────────────────────────
  const LOCALES = {};

  // ── CURRENT LOCALE ─────────────────────────────────────────
  let _current = 'pt-BR';
  let _fallback = 'pt-BR';
  let _onChange = null;
  let _initialized = false;

  // ── DETECT BROWSER LANGUAGE ────────────────────────────────
  function detectLocale() {
    const supported = Object.keys(LOCALES);
    if (supported.length === 0) return 'pt-BR';

    // Check localStorage first
    try {
      const stored = localStorage.getItem('i18n_locale');
      if (stored && supported.includes(stored)) return stored;
    } catch (_) {}

    // Check browser language
    const lang = (navigator.language || navigator.userLanguage || '').slice(0, 5);
    if (supported.includes(lang)) return lang;

    // Check base language (e.g., 'en' matches 'en-US')
    const base = lang.slice(0, 2);
    const match = supported.find(s => s.slice(0, 2) === base);
    if (match) return match;

    return _fallback;
  }

  // ── REGISTER A LOCALE ──────────────────────────────────────
  function register(locale, messages) {
    LOCALES[locale] = messages;
    return I18N_EXPORTS;
  }

  // ── REGISTER MULTIPLE LOCALES ──────────────────────────────
  function registerAll(locales) {
    Object.entries(locales).forEach(([key, msgs]) => register(key, msgs));
    return I18N_EXPORTS;
  }

  // ── SET LOCALE ─────────────────────────────────────────────
  function setLocale(locale) {
    if (!LOCALES[locale]) {
      console.warn(`[i18n] Locale '${locale}' not registered. Keeping '${_current}'.`);
      return false;
    }
    _current = locale;
    try { localStorage.setItem('i18n_locale', locale); } catch (_) {}
    if (_onChange) _onChange(locale);
    return true;
  }

  // ── GET CURRENT LOCALE ─────────────────────────────────────
  function getLocale() { return _current; }

  // ── GET AVAILABLE LOCALES ──────────────────────────────────
  function getLocales() { return Object.keys(LOCALES); }

  // ── GET LOCALE LABEL ───────────────────────────────────────
  function getLocaleLabel(locale) {
    const labels = { 'pt-BR': 'Português (BR)', 'en-US': 'English (US)' };
    return labels[locale] || locale;
  }

  // ── TRANSLATE ──────────────────────────────────────────────
  function t(key, params) {
    const keys = key.split('.');
    let msg = LOCALES[_current];

    // Navigate the nested object
    for (const k of keys) {
      if (msg && typeof msg === 'object' && k in msg) {
        msg = msg[k];
      } else {
        // Fallback to fallback locale
        msg = LOCALES[_fallback];
        for (const fk of keys) {
          if (msg && typeof msg === 'object' && fk in msg) {
            msg = msg[fk];
          } else {
            return key; // Key not found
          }
        }
        break;
      }
    }

    if (typeof msg !== 'string') return key;

    // Interpolation: {{param}}
    if (params) {
      return msg.replace(/\{\{(\w+)\}\}/g, (_, p) => params[p] !== undefined ? params[p] : `{{${p}}}`);
    }

    return msg;
  }

  // ── ON CHANGE CALLBACK ─────────────────────────────────────
  function onChange(callback) {
    _onChange = callback;
    return I18N_EXPORTS;
  }

  // ── UPDATE SWITCHER UI ──────────────────────────────────────
  function updateSwitcher() {
    const label = document.querySelector('.i18n-label');
    if (label) label.textContent = getLocaleLabel(_current);
    document.querySelectorAll('.i18n-option').forEach(el => {
      el.classList.toggle('i18n-active', el.textContent.includes(getLocaleLabel(_current)));
    });
  }

  // ── INIT ───────────────────────────────────────────────────
  function init(fallback) {
    if (fallback) _fallback = fallback;
    if (!_initialized) {
      _current = detectLocale();
      _initialized = true;
    }
    // Dispatch event for auto-updating
    document.dispatchEvent(new CustomEvent('i18n-ready', { detail: { locale: _current } }));
    return I18N_EXPORTS;
  }

  // ── UPDATE ALL ELEMENTS WITH data-i18n ─────────────────────
  function updateDOM() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      let params;
      try {
        const p = el.getAttribute('data-i18n-params');
        if (p) params = JSON.parse(p);
      } catch (_) {}
      const text = t(key, params);
      if (text !== key) {
        el.innerHTML = text;
      }
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      const text = t(key);
      if (text !== key) el.placeholder = text;
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      const text = t(key);
      if (text !== key) el.title = text;
    });
    document.querySelectorAll('[data-i18n-alt]').forEach(el => {
      const key = el.getAttribute('data-i18n-alt');
      const text = t(key);
      if (text !== key) el.alt = text;
    });
    document.querySelectorAll('[data-i18n-value]').forEach(el => {
      const key = el.getAttribute('data-i18n-value');
      const text = t(key);
      if (text !== key) el.value = text;
    });
  }

  // ── LANGUAGE SWITCHER HTML ─────────────────────────────────
  function renderSwitcher() {
    const current = _current;
    const locales = getLocales();
    return `
      <div class="i18n-switcher">
        <button class="i18n-current" onclick="this.nextElementSibling.classList.toggle('i18n-open')" title="${t('common.switchLanguage')}">
          <span class="i18n-globe">🌐</span>
          <span class="i18n-label">${getLocaleLabel(current)}</span>
          <span class="i18n-arrow">▾</span>
        </button>
        <div class="i18n-dropdown">
          ${locales.map(loc => `
            <button class="i18n-option ${loc === current ? 'i18n-active' : ''}"
                    onclick="I18N.setLocale('${loc}');I18N.updateDOM();this.closest('.i18n-dropdown').classList.remove('i18n-open')">
              <span class="i18n-flag">${loc === 'pt-BR' ? '🇧🇷' : loc === 'en-US' ? '🇺🇸' : '🌐'}</span>
              ${getLocaleLabel(loc)}
            </button>
          `).join('')}
        </div>
      </div>`;
  }

  // ── CSS (injetado automaticamente) ─────────────────────────
  function injectCSS() {
    const id = 'i18n-styles';
    if (document.getElementById(id)) return;
    const style = document.createElement('style');
    style.id = id;
    style.textContent = `
      .i18n-switcher { position: relative; display: inline-block; font-family: system-ui, sans-serif; }
      .i18n-current {
        display: flex; align-items: center; gap: 6px;
        padding: 6px 12px; background: transparent; border: 1px solid rgba(255,255,255,0.15);
        border-radius: 8px; color: inherit; cursor: pointer; font-size: 0.8rem;
        transition: all 0.2s;
      }
      .i18n-current:hover { border-color: rgba(255,255,255,0.3); background: rgba(255,255,255,0.05); }
      .i18n-globe { font-size: 1rem; }
      .i18n-label { font-weight: 500; }
      .i18n-arrow { font-size: 0.7rem; opacity: 0.6; transition: transform 0.2s; }
      .i18n-open .i18n-arrow { transform: rotate(180deg); }
      .i18n-dropdown {
        display: none; position: absolute; top: 100%; right: 0; margin-top: 4px;
        background: #1a1d27; border: 1px solid rgba(255,255,255,0.12);
        border-radius: 10px; padding: 4px; min-width: 180px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.5); z-index: 1000;
      }
      .i18n-dropdown.i18n-open { display: block; }
      .i18n-option {
        display: flex; align-items: center; gap: 8px; width: 100%;
        padding: 8px 12px; background: none; border: none; border-radius: 6px;
        color: #c4c9d4; cursor: pointer; font-size: 0.8rem;
        transition: all 0.15s; text-align: left;
      }
      .i18n-option:hover { background: rgba(255,255,255,0.06); color: #fff; }
      .i18n-option.i18n-active { background: rgba(74,222,128,0.1); color: #4ade80; }
      .i18n-flag { font-size: 1.1rem; }
    `;
    document.head.appendChild(style);
  }

  // ── PUBLIC API ─────────────────────────────────────────────
  const I18N_EXPORTS = {
    register,
    registerAll,
    setLocale,
    getLocale,
    getLocales,
    getLocaleLabel,
    t,
    init,
    updateDOM,
    renderSwitcher,
    injectCSS,
    onChange,
    _locales: LOCALES,
  };

  // ── RE-RENDER ALL ON LOCALE CHANGE ─────────────────────────
  // (registrado APOS a definicao de I18N_EXPORTS para evitar TDZ)
  onChange((locale) => {
    updateSwitcher();
    document.dispatchEvent(new CustomEvent('i18n-changed', { detail: { locale } }));
    updateDOM();
  });

  return I18N_EXPORTS;
})();
