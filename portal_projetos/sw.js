/* ============================================================
   ProfHistória Portal — Service Worker
   Permite instalar o portal como PWA (prompt de instalação) e
   oferece um fallback offline básico para os assets essenciais.

   Estratégia:
   - Navegação (HTML, inclusive a raiz "/"): network-first — nunca
     serve HTML velho quando há rede; só usa o cache se offline.
   - Ícones estáticos (png/ico): cache-first (nunca mudam).
   - Nada de respostas de erro é gravado no cache.
   ============================================================ */

const CACHE = "profhistoria-v1";

const SHELL = [
  "./index.html",
  "./manifest.json",
  "./favicon.ico",
  "./favicon.png",
  "./apple-touch-icon.png",
  "./icon-192.png",
  "./icon-512.png",
  "./icon-maskable-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Só intercepta requisições do próprio portal (mesmo origin).
  if (url.origin !== self.location.origin) return;

  // Ícones estáticos (png/ico): cache-first.
  // NOTA: JSON fica de fora de propósito — dados podem mudar (quizzes, i18n).
  if (/\.(png|ico)$/.test(url.pathname)) {
    event.respondWith(
      caches.match(event.request).then((hit) => hit || fetch(event.request))
    );
    return;
  }

  // Navegação (HTML, incluindo a raiz "/"): network-first.
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then((resp) => {
          // Só grava no cache se for resposta válida (evita 404/500 offline).
          if (resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE).then((cache) => cache.put(event.request, clone)).catch(() => {});
          }
          return resp;
        })
        .catch(() =>
          caches.match(event.request).then(
            (hit) => hit || caches.match("./index.html")
          )
        )
    );
  }
});
