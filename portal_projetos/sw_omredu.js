/* ============================================================
   OMREdu — Service Worker
   Suporte offline para o Corretor Híbrido de Gabaritos
   ============================================================ */

const CACHE_NAME = 'omredu-v1';
const ASSETS_TO_CACHE = [
  '/omredu_corretor_hibrido.html',
  '/sw_omredu.js',
];

// Recursos CDN que serão cacheados sob demanda
const CDN_CACHE = 'omredu-cdn-v1';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key !== CDN_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Cache-first para o app
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match('/omredu_corretor_hibrido.html')
      )
    );
    return;
  }

  // Cache CDN assets (OpenCV.js, Google Fonts) sob demanda
  if (
    url.hostname.includes('opencv') ||
    url.hostname.includes('googleapis') ||
    url.hostname.includes('gstatic') ||
    url.hostname.includes('anthropic') // API calls não devem ser cacheadas
  ) {
    event.respondWith(
      caches.open(CDN_CACHE).then((cache) => {
        return cache.match(event.request).then((cached) => {
          const fetchPromise = fetch(event.request).then((response) => {
            // Cache apenas recursos estáticos CDN, não API calls
            if (!url.pathname.includes('messages')) {
              cache.put(event.request, response.clone());
            }
            return response;
          }).catch(() => cached);
          return cached || fetchPromise;
        });
      })
    );
    return;
  }

  // Network-first para todo o resto (com fallback para cache)
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache recursos estáticos
        if (response.status === 200 && url.protocol === 'https:') {
          const contentType = response.headers.get('Content-Type') || '';
          if (
            contentType.includes('javascript') ||
            contentType.includes('css') ||
            contentType.includes('font') ||
            contentType.includes('image')
          ) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

/* ============================================================
   Background Sync — fila de correções pendentes
   ============================================================ */

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-grades') {
    event.waitUntil(syncPendingGrades());
  }
});

async function syncPendingGrades() {
  const cache = await caches.open('pending-grades');
  const keys = await cache.keys();
  for (const request of keys) {
    try {
      const cached = await cache.match(request);
      if (cached) {
        const data = await cached.json();
        // Tenta enviar para API quando online
        await fetch('/api/v1/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        await cache.delete(request);
      }
    } catch (e) {
      console.warn('[SW] Sync pending grade failed:', e);
    }
  }
}
