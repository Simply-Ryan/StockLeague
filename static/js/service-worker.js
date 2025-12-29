/**
 * StockLeague Service Worker - Phase 5 Task 5.2.1
 * Enables offline functionality, asset caching, and PWA support
 * 
 * Caching Strategy:
 * - Static assets (CSS, JS, fonts): Cache-first (serve from cache, fall back to network)
 * - API calls: Network-first (try network, fall back to cache)
 * - Images: Stale-while-revalidate (use cache, update in background)
 * - HTML pages: Network-first (always try fresh, use cache if offline)
 */

const CACHE_NAME = 'stockleague-v1';
const OFFLINE_URL = '/offline.html';

/**
 * Assets to cache on install
 * Only critical assets needed for core functionality
 */
const ASSETS_TO_CACHE = [
    '/',
    '/offline.html',
    '/static/css/styles.css',
    '/static/css/touch.css',
    '/static/js/app.js',
    '/static/js/performance.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'
];

/**
 * Install event: Cache critical assets
 * This runs when the service worker is first installed
 */
self.addEventListener('install', event => {
    console.log('[ServiceWorker] Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[ServiceWorker] Caching critical assets');
                return cache.addAll(ASSETS_TO_CACHE)
                    .catch(err => {
                        console.warn('[ServiceWorker] Some assets failed to cache:', err);
                        // Continue even if some assets fail to cache
                        return Promise.resolve();
                    });
            })
            .then(() => {
                console.log('[ServiceWorker] Skipping waiting, activating immediately');
                return self.skipWaiting();
            })
    );
});

/**
 * Activate event: Clean up old caches
 * This runs when the service worker becomes active
 */
self.addEventListener('activate', event => {
    console.log('[ServiceWorker] Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        // Delete old cache versions
                        if (cacheName !== CACHE_NAME) {
                            console.log('[ServiceWorker] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('[ServiceWorker] Claiming clients');
                return self.clients.claim();
            })
    );
});

/**
 * Fetch event: Serve from cache when offline
 * Uses different strategies based on request type
 */
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests (POST, PUT, DELETE, etc.)
    if (request.method !== 'GET') {
        return;
    }

    // Handle API calls (network-first)
    if (url.pathname.startsWith('/api/')) {
        return event.respondWith(
            fetch(request)
                .then(response => {
                    // Cache successful API responses
                    if (response.ok) {
                        const cacheName = `${CACHE_NAME}-api`;
                        const responseToCache = response.clone();
                        caches.open(cacheName)
                            .then(cache => cache.put(request, responseToCache))
                            .catch(err => console.warn('[ServiceWorker] Cache put failed:', err));
                    }
                    return response;
                })
                .catch(error => {
                    console.warn('[ServiceWorker] Network request failed, trying cache:', error);
                    // Fall back to cache
                    return caches.match(request)
                        .then(cachedResponse => {
                            if (cachedResponse) {
                                return cachedResponse;
                            }
                            // Return offline page for failed navigation
                            if (request.destination === 'document') {
                                return caches.match(OFFLINE_URL);
                            }
                            return new Response('Offline - Resource unavailable', {
                                status: 503,
                                statusText: 'Service Unavailable',
                                headers: new Headers({
                                    'Content-Type': 'text/plain'
                                })
                            });
                        });
                })
        );
    }

    // Handle HTML pages (network-first)
    if (request.destination === 'document') {
        return event.respondWith(
            fetch(request)
                .then(response => {
                    // Cache successful page loads
                    if (response.ok) {
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME)
                            .then(cache => cache.put(request, responseToCache))
                            .catch(err => console.warn('[ServiceWorker] Cache put failed:', err));
                    }
                    return response;
                })
                .catch(error => {
                    console.warn('[ServiceWorker] Page request failed, trying cache:', error);
                    // Fall back to cached page or offline page
                    return caches.match(request)
                        .then(cachedResponse => {
                            return cachedResponse || caches.match(OFFLINE_URL);
                        });
                })
        );
    }

    // Handle images (stale-while-revalidate)
    if (request.destination === 'image') {
        return event.respondWith(
            caches.match(request)
                .then(cachedResponse => {
                    // Return cached image immediately
                    const fetchPromise = fetch(request)
                        .then(response => {
                            // Update cache in background
                            if (response.ok) {
                                const responseToCache = response.clone();
                                caches.open(`${CACHE_NAME}-images`)
                                    .then(cache => cache.put(request, responseToCache))
                                    .catch(err => console.warn('[ServiceWorker] Image cache failed:', err));
                            }
                            return response;
                        })
                        .catch(error => {
                            console.warn('[ServiceWorker] Image fetch failed:', error);
                            // Return placeholder if image and cache unavailable
                            return new Response('', { status: 404 });
                        });

                    return cachedResponse || fetchPromise;
                })
        );
    }

    // Handle scripts and stylesheets (cache-first)
    if (request.destination === 'script' || request.destination === 'style') {
        return event.respondWith(
            caches.match(request)
                .then(cachedResponse => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    return fetch(request)
                        .then(response => {
                            // Cache successful responses
                            if (response.ok) {
                                const responseToCache = response.clone();
                                caches.open(CACHE_NAME)
                                    .then(cache => cache.put(request, responseToCache))
                                    .catch(err => console.warn('[ServiceWorker] Cache put failed:', err));
                            }
                            return response;
                        })
                        .catch(error => {
                            console.warn('[ServiceWorker] Script/CSS request failed:', error);
                            return new Response('', { status: 404 });
                        });
                })
        );
    }

    // Default: network-first with cache fallback
    event.respondWith(
        fetch(request)
            .then(response => {
                // Cache successful responses
                if (response.ok) {
                    const responseToCache = response.clone();
                    caches.open(CACHE_NAME)
                        .then(cache => cache.put(request, responseToCache))
                        .catch(err => console.warn('[ServiceWorker] Cache put failed:', err));
                }
                return response;
            })
            .catch(error => {
                console.warn('[ServiceWorker] Request failed:', error);
                return caches.match(request)
                    .then(cachedResponse => cachedResponse || new Response('', { status: 404 }));
            })
    );
});

/**
 * Message event: Handle messages from clients
 * Allows app to communicate with service worker
 */
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        console.log('[ServiceWorker] SKIP_WAITING message received');
        self.skipWaiting();
    }

    if (event.data && event.data.type === 'CLEAR_CACHE') {
        console.log('[ServiceWorker] Clearing cache');
        caches.keys().then(cacheNames => {
            cacheNames.forEach(cacheName => {
                caches.delete(cacheName);
            });
        });
    }

    if (event.data && event.data.type === 'GET_CACHE_SIZE') {
        // Estimate cache size
        caches.keys().then(cacheNames => {
            let totalSize = 0;
            Promise.all(
                cacheNames.map(cacheName =>
                    caches.open(cacheName).then(cache =>
                        cache.keys().then(keys => keys.length)
                    )
                )
            ).then(sizes => {
                totalSize = sizes.reduce((a, b) => a + b, 0);
                event.ports[0].postMessage({ size: totalSize });
            });
        });
    }
});

/**
 * Background sync: Queue trades when offline
 * Syncs when connection is restored
 */
self.addEventListener('sync', event => {
    if (event.tag === 'sync-trades') {
        console.log('[ServiceWorker] Syncing trades');
        event.waitUntil(
            // Implementation will be in offline-manager.js
            Promise.resolve()
        );
    }
});

// Log service worker status
console.log('[ServiceWorker] Loaded and ready');
