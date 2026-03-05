const CACHE_NAME = 'zuri-cache-v1';
const ASSETS = [
    '/',
    '/index.html',
    'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js'
];

// Install event: cache assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(ASSETS);
        })
    );
    self.skipWaiting();
});

// Activate event: clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.map(key => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch event: Network first, fallback to cache
self.addEventListener('fetch', event => {
    // Only cache GET requests (don't cache API POST requests for chat)
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
