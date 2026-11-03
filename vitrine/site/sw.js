// Gerado por vitrine/build.py: não edite à mão.
// Precache de todas as páginas e assets desta versão: navegação instantânea
// e funcionamento offline. Cada build muda VERSION, e o cache antigo é apagado.
const VERSION = 'couture-ed8fbb73f0fe';
const PRECACHE = ["./", "index.html", "como-funciona/index.html", "privacidade/index.html", "pecas/vestido-varanda/index.html", "pecas/camisa-janela/index.html", "pecas/saia-mapa/index.html", "pecas/lenco-traco/index.html", "designers/helena-vasques/index.html", "designers/theo-amaral/index.html", "assets/encomenda.js?v=1bf2929cf1", "assets/site.js?v=e25ef7671b", "assets/vitrine.css?v=de14912dd0"];
const FONTS = 'couture-fonts';

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== VERSION && k !== FONTS).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  // Google Fonts: serve from cache, refresh in the background.
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    event.respondWith(caches.open(FONTS).then(async (cache) => {
      const cached = await cache.match(request);
      const network = fetch(request).then((response) => {
        if (response.ok) cache.put(request, response.clone());
        return response;
      }).catch(() => cached);
      return cached || network;
    }));
    return;
  }
  if (url.origin !== self.location.origin) return;

  // Pages and assets of this version: cache first, network as fallback.
  event.respondWith(caches.match(request, { cacheName: VERSION }).then((cached) => cached || fetch(request).then((response) => {
    if (response.ok && url.pathname.startsWith(new URL(self.registration.scope).pathname)) {
      const copy = response.clone();
      caches.open(VERSION).then((cache) => cache.put(request, copy));
    }
    return response;
  }).catch(() => caches.match(new URL('index.html', self.registration.scope).href))));
});
