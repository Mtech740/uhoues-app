// Uhoues Service Worker
const CACHE_NAME = 'uhoues-v1.0';
const urlsToCache = [
  '/',
  'https://uhoues.streamlit.app/',
  'https://img.icons8.com/color/192/000000/home--v1.png',
  'https://img.icons8.com/color/512/000000/home--v1.png'
];

self.addEventListener('install', event => {
  console.log('Uhoues Service Worker installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Uhoues cache opened');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          console.log('Uhoues serving from cache:', event.request.url);
          return response;
        }
        console.log('Uhoues fetching from network:', event.request.url);
        return fetch(event.request);
      })
  );
});

self.addEventListener('activate', event => {
  console.log('Uhoues Service Worker activated');
});
