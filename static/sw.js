// TradeRadar — Service Worker
// Strategie :
//   - shell statique (HTML/CSS/JS/manifest/icon) : cache-first, mise a jour en arriere-plan
//   - requetes /api/* : network-first, fallback cache si offline
//   - reste : network-first
//
// Pour forcer un refresh complet apres deploiement : bump CACHE_VERSION.

const CACHE_VERSION = 'tr-v5';
const STATIC_CACHE  = `${CACHE_VERSION}-static`;
const API_CACHE     = `${CACHE_VERSION}-api`;

const PRECACHE_URLS = [
  '/',
  '/static/style.css',
  '/static/app.js',
  '/static/icon.svg',
  '/manifest.webmanifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS).catch(() => null))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => !k.startsWith(CACHE_VERSION))
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

function isStaticAsset(url) {
  return (
    url.pathname === '/' ||
    url.pathname === '/manifest.webmanifest' ||
    url.pathname.startsWith('/static/')
  );
}

function isApiRequest(url) {
  return url.pathname.startsWith('/api/');
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const fresh = await fetch(request);
    if (fresh && fresh.ok) cache.put(request, fresh.clone());
    return fresh;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw err;
  }
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    // revalidation en arriere-plan
    fetch(request).then((fresh) => {
      if (fresh && fresh.ok) cache.put(request, fresh.clone());
    }).catch(() => null);
    return cached;
  }
  const fresh = await fetch(request);
  if (fresh && fresh.ok) cache.put(request, fresh.clone());
  return fresh;
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // ignore CDN, Yahoo, etc.

  if (isApiRequest(url)) {
    event.respondWith(networkFirst(req, API_CACHE));
    return;
  }

  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(req, STATIC_CACHE));
    return;
  }

  event.respondWith(networkFirst(req, STATIC_CACHE));
});
