const CACHE_NAME = 'uhoues-v1';
const urlsToCache = [
  '/',
  'https://uhoues.streamlit.app/',
  'https://img.icons8.com/color/192/000000/home--v1.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
