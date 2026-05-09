const CACHE = 'osmosis-v1';
const STATIC_RE = /\/static\/dist\/.+\.(?:js|mjs|css|png|jpg|jpeg|svg|webp|woff2?|ttf|eot|ico)$/;
const APP_SHELL = ['/', '/static/dist/logo.png', '/manifest.json'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(APP_SHELL)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Never intercept the API — it must always be live
  if (url.pathname.startsWith('/api/')) return;

  // Cache-first for fingerprinted build assets
  if (STATIC_RE.test(url.pathname)) {
    event.respondWith(
      caches.open(CACHE).then((cache) =>
        cache.match(req).then((cached) =>
          cached ||
          fetch(req).then((resp) => {
            if (resp.ok) cache.put(req, resp.clone());
            return resp;
          })
        )
      )
    );
    return;
  }

  // Network-first for everything else (HTML, manifest, etc.)
  const wantsHTML = req.headers.get('accept')?.includes('text/html');
  event.respondWith(
    fetch(req)
      .then((resp) => {
        if (resp.ok && wantsHTML) {
          const clone = resp.clone();
          caches.open(CACHE).then((cache) => cache.put(req, clone));
        }
        return resp;
      })
      .catch(() => caches.match(req).then((r) => r || caches.match('/')))
  );
});
