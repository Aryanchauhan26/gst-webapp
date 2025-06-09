// Service Worker for GST Intelligence Platform PWA
const CACHE_NAME = 'gst-intelligence-v1.0.0';
const STATIC_CACHE_NAME = 'gst-static-v1.0.0';
const DYNAMIC_CACHE_NAME = 'gst-dynamic-v1.0.0';

// Files to cache immediately
const STATIC_FILES = [
    '/',
    '/login',
    '/signup',
    '/static/style.css',
    '/static/common-styles.css',
    '/static/common-scripts.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
    // Add your critical assets here
];

// Files that should always be fetched from network
const NETWORK_FIRST = [
    '/search',
    '/api/',
    '/generate-pdf',
    '/export/'
];

// Install event - cache static files
self.addEventListener('install', event => {
    console.log('🔧 Service Worker installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then(cache => {
                console.log('📦 Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .then(() => {
                console.log('✅ Service Worker installed');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('❌ Cache installation failed:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('🚀 Service Worker activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(cacheName => {
                            // Delete old caches
                            return cacheName !== STATIC_CACHE_NAME && 
                                   cacheName !== DYNAMIC_CACHE_NAME;
                        })
                        .map(cacheName => {
                            console.log('🗑️ Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            })
            .then(() => {
                console.log('✅ Service Worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - handle network requests
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip chrome-extension and other protocols
    if (!url.protocol.startsWith('http')) {
        return;
    }
    
    event.respondWith(
        handleFetch(request)
    );
});

async function handleFetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;
    
    try {
        // Network first for dynamic content
        if (NETWORK_FIRST.some(pattern => path.startsWith(pattern))) {
            return await networkFirst(request);
        }
        
        // Cache first for static content
        if (isStaticAsset(path)) {
            return await cacheFirst(request);
        }
        
        // Stale while revalidate for pages
        return await staleWhileRevalidate(request);
        
    } catch (error) {
        console.error('Fetch failed:', error);
        return await getFallbackResponse(request);
    }
}

// Network first strategy
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        throw error;
    }
}

// Cache first strategy
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
        const cache = await caches.open(STATIC_CACHE_NAME);
        cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
}

// Stale while revalidate strategy
async function staleWhileRevalidate(request) {
    const cache = await caches.open(DYNAMIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    const fetchPromise = fetch(request).then(networkResponse => {
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    });
    
    return cachedResponse || fetchPromise;
}

// Check if request is for static asset
function isStaticAsset(path) {
    return /\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/i.test(path);
}

// Fallback response for offline scenarios
async function getFallbackResponse(request) {
    const url = new URL(request.url);
    
    // For HTML pages, return offline page
    if (request.headers.get('Accept').includes('text/html')) {
        const offlineResponse = await caches.match('/offline.html');
        if (offlineResponse) {
            return offlineResponse;
        }
        
        // Create a simple offline response
        return new Response(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Offline - GST Intelligence</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        text-align: center; 
                        padding: 50px;
                        background: #0a0a0a;
                        color: white;
                    }
                    .offline-icon { font-size: 64px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="offline-icon">📱</div>
                <h1>You're Offline</h1>
                <p>Please check your internet connection and try again.</p>
                <button onclick="window.location.reload()">Retry</button>
            </body>
            </html>
        `, {
            status: 200,
            headers: { 'Content-Type': 'text/html' }
        });
    }
    
    // For other requests, throw error
    throw new Error('Network unavailable');
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('🔄 Background sync:', event.tag);
    
    if (event.tag === 'background-search') {
        event.waitUntil(syncPendingSearches());
    }
});

async function syncPendingSearches() {
    // Implement background sync for searches made while offline
    const pendingSearches = await getStoredSearches();
    
    for (const search of pendingSearches) {
        try {
            await performSearch(search);
            await removePendingSearch(search.id);
        } catch (error) {
            console.error('Background sync failed for search:', error);
        }
    }
}

// Push notifications
self.addEventListener('push', event => {
    console.log('📲 Push notification received');
    
    if (!event.data) {
        return;
    }
    
    const data = event.data.json();
    const options = {
        body: data.body || 'New update available',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        tag: data.tag || 'general',
        requireInteraction: data.requireInteraction || false,
        actions: data.actions || [
            {
                action: 'open',
                title: 'Open App',
                icon: '/static/icons/open-24x24.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss',
                icon: '/static/icons/dismiss-24x24.png'
            }
        ],
        data: data.data || {}
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title || 'GST Intelligence', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    console.log('🔔 Notification clicked:', event.action);
    
    event.notification.close();
    
    const action = event.action;
    const data = event.notification.data;
    
    if (action === 'open' || !action) {
        event.waitUntil(
            clients.openWindow(data.url || '/')
        );
    }
    // 'dismiss' action just closes the notification
});

// Message handling for communication with main thread
self.addEventListener('message', event => {
    console.log('📨 Message received:', event.data);
    
    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data.type === 'GET_CACHE_STATUS') {
        event.ports[0].postMessage({
            type: 'CACHE_STATUS',
            cached: STATIC_FILES.length
        });
    }
});

// Utility functions for IndexedDB storage (for background sync)
async function getStoredSearches() {
    // Implement IndexedDB operations for offline search storage
    return [];
}

async function removePendingSearch(id) {
    // Remove completed search from storage
}

async function performSearch(search) {
    // Perform the actual search request
    const response = await fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(search)
    });
    
    return response.json();
}