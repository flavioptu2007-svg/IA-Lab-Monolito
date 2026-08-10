/* =============================================================================
   ia_api.js — Integração do portal com a API de IA (Render / Cloud)
   =============================================================================
   Usa a API pública: https://ia-lab-api.onrender.com
     - POST /api/chat        →  { response, provider, task_type, latency_ms }
     - POST /api/audio/tts   →  { audio_base64 (WAV), ... }

   Exposição global:
     window.IAApi = {
       BASE,             // URL base da API (detecta override window.IA_API_BASE)
       ping(),           // -> Promise<boolean>  (API no ar?)
       chat(prompt, o),  // -> Promise<{response, provider, latency_ms}>
       tts(text, o),     // -> Promise<Blob> (áudio WAV)
       speak(text, o),   // -> Promise<void> (sintetiza + toca)
       stopSpeak(),      // para a fala atual
       injectWidget(o),  // widget flutuante "Assistente IA" (Shadow DOM)
     }

   Uso rápido num jogo (antes de </body>):
     <script src="ia_api.js"></script>
     <script>IAApi.injectWidget({ title:'Assistente de História', hint:'Pergunte sobre o jogo…' });</script>
   ============================================================================= */
(function () {
  'use strict';

  /* ---------- Config ---------- */
  // Detecção automática de LAN: se o portal foi aberto via IP 192.168.x.x
  // (ex.: http://192.168.15.17:8765 — servidor local da escola), o widget usa
  // a API local da MESMA máquina (porta 8099) em vez da nuvem.
  // No Firebase (jogos-5f131.web.app) ou localhost continua usando a nuvem.
  if (!window.IA_API_BASE && /^https?:\/\/192\.168\./i.test(location.origin)) {
    window.IA_API_BASE = location.origin.replace(/:\d+$/, ':8099');
  }
  var BASE = (window.IA_API_BASE || 'https://ia-lab-api.onrender.com').replace(/\/+$/, '');
  var TIMEOUT = 60000; // chat pode demorar quando o Render "acorda"

  /* ---------- Util ---------- */
  function fetchJSON(path, opts) {
    var controller = ('AbortController' in window) ? new AbortController() : null;
    var timer = setTimeout(function () { if (controller) controller.abort(); }, TIMEOUT);
    return fetch(BASE + path, {
      method: opts && opts.method ? opts.method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: opts && opts.body ? JSON.stringify(opts.body) : undefined,
      signal: controller ? controller.signal : undefined,
    })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (!r.ok) {
            var det = (data && (data.detail || data.message)) || ('HTTP ' + r.status);
            throw new Error(det);
          }
          return data;
        });
      })
      .finally(function () { clearTimeout(timer); });
  }

  function base64ToBlob(b64, mime) {
    var bin = atob(b64);
    var len = bin.length;
    var bytes = new Uint8Array(len);
    for (var i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
    return new Blob([bytes], { type: mime || 'audio/wav' });
  }

  /* ---------- API pública ---------- */
  var IAApi = {
    BASE: BASE,
    _online: null,

    ping: function () {
      return fetch(BASE + '/api/health', { method: 'GET' })
        .then(function (r) { return r.ok; })
        .then(function (ok) { IAApi._online = ok; return ok; })
        .catch(function () { IAApi._online = false; return false; });
    },

    chat: function (prompt, opts) {
      opts = opts || {};
      var body = { prompt: prompt };
      if (opts.provider) body.provider = opts.provider;
      if (opts.task_type) body.task_type = opts.task_type;
      if (opts.agent) body.agent = opts.agent;
      if (typeof opts.use_rag === 'boolean') body.use_rag = opts.use_rag;
      return fetchJSON('/api/chat', { body: body }).then(function (d) {
        if (!d.response) throw new Error('A API retornou uma resposta vazia.');
        return {
          response: d.response || '',
          provider: d.provider || '?',
          task_type: d.task_type || '?',
          latency_ms: d.latency_ms || 0,
        };
      });
    },

    tts: function (text, opts) {
      opts = opts || {};
      var body = { text: String(text) };
      if (opts.voice) body.voice = opts.voice;
      if (opts.engine) body.engine = opts.engine;
      if (opts.rate) body.rate = opts.rate;
      body.save_format = opts.save_format || 'wav';
      return fetchJSON('/api/audio/tts', { body: body }).then(function (d) {
        if (!d.audio_base64) throw new Error('Áudio vazio na resposta do TTS');
        return { blob: base64ToBlob(d.audio_base64, 'audio/wav'), meta: d };
      });
    },

    _audio: null,
    speak: function (text, opts) {
      IAApi.stopSpeak();
      return IAApi.tts(text, opts).then(function (res) {
        var url = URL.createObjectURL(res.blob);
        var a = new Audio(url);
        IAApi._audio = { el: a, url: url };
        return new Promise(function (resolve, reject) {
          a.onended = function () { URL.revokeObjectURL(url); IAApi._audio = null; resolve(); };
          a.onerror = function () { URL.revokeObjectURL(url); IAApi._audio = null; reject(new Error('Falha ao reproduzir o áudio')); };
          a.play().catch(function (e) { URL.revokeObjectURL(url); IAApi._audio = null; reject(e); });
        });
      });
    },

    stopSpeak: function () {
      if (IAApi._audio) {
        try { IAApi._audio.el.pause(); } catch (e) {}
        URL.revokeObjectURL(IAApi._audio.url);
        IAApi._audio = null;
      }
    },

    /* ---------- Widget flutuante ---------- */
    injectWidget: function (o) {
      o = o || {};
      var title = o.title || 'Assistente IA';
      var hint = o.hint || 'Pergunte sobre o jogo ou o conteúdo da aula.';
      var accent = o.accent || '#4f46e5';
      var placeholder = o.placeholder || 'Digite sua pergunta…';

      // Se já existe, não duplica
      if (document.querySelector('ia-lab-widget')) return;

      var host = document.createElement('ia-lab-widget');
      host.setAttribute('style', 'all:initial');
      document.body.appendChild(host);

      var shadow = host.attachShadow({ mode: 'open' });

      var css = (
        ':host{--accent:' + accent + ';position:fixed;bottom:18px;right:18px;z-index:2147483000;' +
        'font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}' +
        '*{box-sizing:border-box;margin:0;padding:0}' +
        '.fab{width:56px;height:56px;border-radius:50%;border:none;cursor:pointer;' +
        'background:linear-gradient(135deg,var(--accent),#7c3aed);color:#fff;font-size:24px;' +
        'box-shadow:0 6px 20px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;' +
        'transition:transform .2s ease,box-shadow .2s ease}' +
        '.fab:hover{transform:scale(1.08);box-shadow:0 8px 26px rgba(0,0,0,.4)}' +
        '.fab:active{transform:scale(.95)}' +
        '.panel{position:fixed;bottom:84px;right:18px;width:min(380px,calc(100vw - 36px));' +
        'max-height:min(560px,calc(100vh - 120px));display:flex;flex-direction:column;' +
        'background:#fff;border-radius:18px;box-shadow:0 20px 60px rgba(0,0,0,.35);' +
        'overflow:hidden;transform-origin:bottom right;' +
        'animation:iaPop .22s cubic-bezier(.4,0,.2,1)}' +
        '.panel.closed{display:none}' +
        '@keyframes iaPop{from{opacity:0;transform:translateY(14px) scale(.94)}to{opacity:1;transform:none}}' +
        '.head{display:flex;align-items:center;gap:10px;padding:12px 14px;color:#fff;' +
        'background:linear-gradient(135deg,var(--accent),#7c3aed)}' +
        '.head .ico{font-size:20px}' +
        '.head .tt{flex:1;font-weight:800;font-size:14px}' +
        '.head .st{font-size:10px;opacity:.85;display:block;font-weight:500;margin-top:1px}' +
        '.head button{border:none;background:rgba(255,255,255,.18);color:#fff;width:28px;height:28px;' +
        'border-radius:8px;cursor:pointer;font-size:14px;transition:background .15s}' +
        '.head button:hover{background:rgba(255,255,255,.32)}' +
        '.msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;' +
        'background:#f6f7fb;scroll-behavior:smooth}' +
        '.m{max-width:88%;padding:9px 13px;border-radius:14px;font-size:13.5px;line-height:1.5;' +
        'white-space:pre-wrap;word-wrap:break-word;position:relative;animation:iaMsg .18s ease}' +
        '@keyframes iaMsg{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}' +
        '.m.user{align-self:flex-end;background:var(--accent);color:#fff;border-bottom-right-radius:4px}' +
        '.m.bot{align-self:flex-start;background:#fff;border:1px solid #e5e7f0;' +
        'border-bottom-left-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,.05)}' +
        '.m .meta{display:block;font-size:10px;opacity:.6;margin-top:5px}' +
        '.m .speak{position:absolute;top:6px;right:6px;border:none;background:transparent;' +
        'cursor:pointer;font-size:13px;opacity:.55;padding:2px;border-radius:6px;transition:all .15s}' +
        '.m.bot .speak{display:inline-block}' +
        '.m.bot .speak:hover{opacity:1;background:#f0f1f8}' +
        '.m.bot.speaking{outline:2px solid var(--accent);outline-offset:2px}' +
        '.sys{align-self:center;font-size:11px;color:#8a90a8;background:#eef0f7;padding:4px 12px;' +
        'border-radius:999px;text-align:center;max-width:95%}' +
        '.typing{display:inline-flex;gap:4px;padding:12px 16px}' +
        '.typing i{width:7px;height:7px;border-radius:50%;background:var(--accent);' +
        'animation:iaBlink 1s infinite}' +
        '.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}' +
        '@keyframes iaBlink{0%,80%,100%{opacity:.25;transform:scale(.8)}40%{opacity:1;transform:scale(1)}}' +
        '.input{display:flex;gap:8px;padding:10px 12px;background:#fff;border-top:1px solid #eef0f6}' +
        '.input textarea{flex:1;resize:none;border:1px solid #e2e5f1;border-radius:12px;' +
        'padding:9px 12px;font-size:13.5px;font-family:inherit;outline:none;max-height:100px;' +
        'min-height:42px;line-height:1.4}' +
        '.input textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(79,70,229,.12)}' +
        '.input button{border:none;border-radius:12px;padding:0 16px;font-weight:800;font-size:13px;' +
        'background:var(--accent);color:#fff;cursor:pointer;transition:all .15s;min-width:64px}' +
        '.input button:hover{background:#4338ca;transform:translateY(-1px)}' +
        '.input button:disabled{opacity:.5;cursor:not-allowed;transform:none}' +
        '.off{display:flex;align-items:center;gap:8px;padding:8px 12px;font-size:12px;' +
        'background:#fef3c7;color:#92400e;border-top:1px solid #fde68a}'
      );

      var sheet = document.createElement('style');
      sheet.textContent = css;
      shadow.appendChild(sheet);

      /* ---- DOM do widget ---- */
      var fab = document.createElement('button');
      fab.className = 'fab';
      fab.setAttribute('aria-label', title);
      fab.innerHTML = '🤖';

      var panel = document.createElement('div');
      panel.className = 'panel closed';

      panel.innerHTML =
        '<div class="head">' +
        '<span class="ico">🤖</span>' +
        '<div class="tt">' + escHTML(title) + '<span class="st" id="ia-st">conectando…</span></div>' +
        '<button id="ia-clear" title="Nova conversa">↺</button>' +
        '<button id="ia-close" title="Fechar">✕</button>' +
        '</div>' +
        '<div class="msgs" id="ia-msgs">' +
        '<div class="sys">' + escHTML(hint) + '</div>' +
        '</div>' +
        '<div class="input">' +
        '<textarea id="ia-in" rows="1" placeholder="' + escAttr(placeholder) + '"></textarea>' +
        '<button id="ia-send">➤</button>' +
        '</div>' +
        '<div class="off" id="ia-off" style="display:none">⚠️ API indisponível no momento — tente novamente em instantes.</div>';

      shadow.appendChild(fab);
      shadow.appendChild(panel);

      var $msgs = panel.querySelector('#ia-msgs');
      var $in = panel.querySelector('#ia-in');
      var $send = panel.querySelector('#ia-send');
      var $off = panel.querySelector('#ia-off');
      var $st = panel.querySelector('#ia-st');

      /* ---- histórico persistente por sessão (localStorage) ---- */
      // Chave por página → cada jogo tem sua própria conversa.
      // encodeURIComponent evita colisões (ex: /jogo-x.html vs /jogo_x.html).
      var HISTORY_KEY = 'ia-lab-hist:' + encodeURIComponent(location.pathname || '/');
      var MAX_HISTORY = 60; // últimas 60 mensagens (30 perguntas/respostas)
      var HISTORY_TTL = 7 * 24 * 3600 * 1000; // expira após 7 dias

      function loadHistory() {
        try {
          var raw = localStorage.getItem(HISTORY_KEY);
          if (!raw) return [];
          var obj = JSON.parse(raw);
          if (obj && Array.isArray(obj.msgs) && obj.updatedAt) {
            if (Date.now() - obj.updatedAt > HISTORY_TTL) {
              localStorage.removeItem(HISTORY_KEY); // limpa entrada vencida
              return [];
            }
            return obj.msgs.slice(-MAX_HISTORY);
          }
          return [];
        } catch (e) { return []; }
      }

      function saveHistory() {
        try {
          localStorage.setItem(HISTORY_KEY, JSON.stringify({
            updatedAt: Date.now(),
            msgs: history.slice(-MAX_HISTORY),
          }));
        } catch (e) { /* quota/privacidade: ignora */ }
      }

      var history = loadHistory();
      var busy = false;

      /* ---- helpers de mensagem ---- */
      function escHTML(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
          return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
      }
      function escAttr(s) { return escHTML(s).replace(/`/g, '&#96;'); }

      function addMsg(role, text, meta) {
        var d = document.createElement('div');
        d.className = 'm ' + role;
        d.textContent = text;
        if (meta) {
          var m = document.createElement('span');
          m.className = 'meta';
          m.textContent = meta;
          d.appendChild(m);
        }
        if (role === 'bot') {
          var sp = document.createElement('button');
          sp.className = 'speak';
          sp.title = 'Ouvir resposta';
          sp.textContent = '🔊';
          sp.addEventListener('click', function () {
            if (IAApi._audio) IAApi.stopSpeak();
            d.classList.add('speaking');
            IAApi.speak(text).catch(function () {}).finally(function () {
              d.classList.remove('speaking');
            });
          });
          d.appendChild(sp);
        }
        $msgs.appendChild(d);
        $msgs.scrollTop = $msgs.scrollHeight;
        return d;
      }

      function addTyping() {
        var d = document.createElement('div');
        d.className = 'm bot';
        d.innerHTML = '<div class="typing"><i></i><i></i><i></i></div>';
        $msgs.appendChild(d);
        $msgs.scrollTop = $msgs.scrollHeight;
        return d;
      }

      /* ---- restaura a conversa salva desta sessão ---- */
      history.forEach(function (m) {
        // history grava 'assistant'; o DOM/CSS usa 'bot'
        addMsg(m.role === 'assistant' ? 'bot' : 'user', m.content, m.meta);
      });
      if (history.length) {
        var note = document.createElement('div');
        note.className = 'sys';
        note.textContent = '💬 Conversa retomada — ' + Math.ceil(history.length / 2) + ' pergunta' + (Math.ceil(history.length / 2) > 1 ? 's' : '') + ' desta sessão.';
        $msgs.appendChild(note);
        $msgs.scrollTop = $msgs.scrollHeight;
      }

      /* ---- envio ---- */
      function buildPrompt(text) {
        // O backend /api/chat aceita só `prompt` — embute o contexto do jogo
        // e as últimas trocas no próprio prompt para manter o diálogo.
        var ctx = o.context ? 'Contexto da atividade: ' + o.context + '\n\n' : '';
        var tail = history.slice(-6).map(function (m) {
          return (m.role === 'user' ? 'Aluno: ' : 'Assistente: ') + m.content;
        }).join('\n');
        return ctx + (tail ? tail + '\n\n' : '') + 'Aluno: ' + text + '\nAssistente:';
      }

      function send() {
        if (busy) return;
        var text = $in.value.trim();
        if (!text) return;
        $in.value = '';
        $in.style.height = 'auto';
        history.push({ role: 'user', content: text });
        saveHistory();
        addMsg('user', text);
        busy = true;
        $send.disabled = true;
        var t = addTyping();

        IAApi.chat(buildPrompt(text), { use_rag: false })
          .then(function (res) {
            var meta = '⚡ ' + res.latency_ms + ' ms · ' + res.provider;
            history.push({ role: 'assistant', content: res.response, meta: meta });
            saveHistory();
            t.remove();
            addMsg('bot', res.response, meta);
            $off.style.display = 'none';
          })
          .catch(function (err) {
            t.remove();
            var msg = (err && err.name === 'AbortError')
              ? 'A API demorou para responder — tente novamente.'
              : (err && err.message ? err.message : '');
            var errText = '😕 Não consegui responder agora. ' + msg;
            addMsg('bot', errText);
            // persiste também a resposta de erro para não restaurar pergunta órfã
            history.push({ role: 'assistant', content: errText, meta: '' });
            saveHistory();
            $off.style.display = 'flex';
            $st.textContent = 'offline';
          })
          .finally(function () {
            busy = false;
            $send.disabled = false;
            $in.focus();
          });
      }

      $send.addEventListener('click', send);
      $in.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
      });
      $in.addEventListener('input', function () {
        $in.style.height = 'auto';
        $in.style.height = Math.min($in.scrollHeight, 100) + 'px';
      });

      function resetClear() {
        if (clearTimer) { clearTimeout(clearTimer); clearTimer = null; }
        clearArmed = false;
        $clear.textContent = '↺';
        $clear.style.background = '';
      }

      fab.addEventListener('click', function () {
        var closed = panel.classList.toggle('closed');
        fab.innerHTML = closed ? '🤖' : '✕';
        if (closed) {
          resetClear();
        } else {
          $in.focus();
          // com histórico restaurado, mostra a conversa mais recente
          $msgs.scrollTop = $msgs.scrollHeight;
          IAApi.ping().then(function (ok) {
            $st.textContent = ok ? 'online' : 'offline';
            $off.style.display = ok ? 'none' : 'flex';
          });
        }
      });
      panel.querySelector('#ia-close').addEventListener('click', function () {
        panel.classList.add('closed');
        fab.innerHTML = '🤖';
        resetClear();
      });

      /* ---- nova conversa (limpa a sessão) — 2 cliques para confirmar ---- */
      var $clear = panel.querySelector('#ia-clear');
      var clearArmed = false, clearTimer = null;
      $clear.addEventListener('click', function () {
        if (!clearArmed) {
          clearArmed = true;
          $clear.textContent = 'Limpar?';
          $clear.style.background = 'rgba(220,38,38,.85)';
          clearTimer = setTimeout(function () {
            resetClear();
          }, 3000);
          return;
        }
        resetClear();
        history = [];
        saveHistory();
        while ($msgs.firstChild) $msgs.removeChild($msgs.firstChild);
        var hintEl = document.createElement('div');
        hintEl.className = 'sys';
        hintEl.textContent = hint;
        $msgs.appendChild(hintEl);
        addMsg('bot', '🧹 Conversa nova! Pergunte o que quiser sobre este jogo.');
        $in.focus();
      });

      // Verifica status ao carregar (silencioso)
      IAApi.ping().then(function (ok) { $st.textContent = ok ? 'online' : 'offline'; });

      return IAApi;
    },
  };

  window.IAApi = IAApi;
})();
