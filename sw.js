// /sw.js - Optimized Service Worker
const CACHE_VERSION = 'v2.2.0';
const CACHE_PREFIX = 'gst-intelligence';
const STATIC_CACHE = `${CACHE_PREFIX}-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `${CACHE_PREFIX}-dynamic-${CACHE_VERSION}`;
const API_CACHE = `${CACHE_PREFIX}-api-${CACHE_VERSION}`;

const CACHE_CONFIG = {
    staticTTL: 24 * 60 * 60 * 1000,     // 24 hours
    dynamicTTL: 2 * 60 * 60 * 1000,     // 2 hours  
    apiTTL: 30 * 60 * 1000,             // 30 minutes
    maxEntries: { static: 100, dynamic: 50, api: 30 }
};

const CRITICAL_STATIC_FILES = [
    '/',
    '/static/css/base.css',
    '/static/js/app-core.js',
    '/static/manifest.json'
];

const NETWORK_FIRST_PATTERNS = ['/api/', '/search', '/logout', '/health'];
const CACHE_FIRST_PATTERNS = ['/static/', 'https://cdnjs.cloudflare.com/'];

// Install event - cache critical files
self.addEventListener('install', event => {
    console.log('🔧 Service Worker installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('📦 Caching critical static files');
                return cache.addAll(CRITICAL_STATIC_FILES);
            })
            .then(() => {
                console.log('✅ Service Worker installed successfully');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('❌ Service Worker install failed:', error);
            })
    );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
    console.log('🚀 Service Worker activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                const deletePromises = cacheNames
                    .filter(cacheName => 
                        cacheName.startsWith(CACHE_PREFIX) &&
                        !cacheName.includes(CACHE_VERSION)
                    )
                    .map(cacheName => {
                        console.log('🗑️ Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    });
                
                return Promise.all(deletePromises);
            })
            .then(() => {
                console.log('✅ Service Worker activated successfully');
                return self.clients.claim();
            })
            .catch(error => {
                console.error('❌ Service Worker activation failed:', error);
            })
    );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') return;
    
    // Skip chrome-extension requests
    if (url.protocol === 'chrome-extension:') return;
    
    // Determine caching strategy
    if (shouldUseNetworkFirst(url.pathname)) {
        event.respondWith(networkFirstStrategy(request));
    } else if (shouldUseCacheFirst(url.pathname)) {
        event.respondWith(cacheFirstStrategy(request));
    } else {
        event.respondWith(staleWhileRevalidateStrategy(request));
    }
});

function shouldUseNetworkFirst(pathname) {
    return NETWORK_FIRST_PATTERNS.some(pattern => pathname.startsWith(pattern));
}

function shouldUseCacheFirst(pathname) {
    return CACHE_FIRST_PATTERNS.some(pattern => pathname.startsWith(pattern));
}

async function networkFirstStrategy(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.log('🌐 Network failed, trying cache:', request.url);
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        throw error;
    }
}

async function cacheFirstStrategy(request) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.error('❌ Cache-first strategy failed:', error);
        throw error;
    }
}

async function staleWhileRevalidateStrategy(request) {
    const cachedResponse = await caches.match(request);
    
    const fetchPromise = fetch(request).then(response => {
        if (response.ok) {
            const cache = caches.open(DYNAMIC_CACHE);
            cache.then(c => c.put(request, response.clone()));
        }
        return response;
    });
    
    return cachedResponse || fetchPromise;
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    console.log('🔄 Background sync triggered');
    // Implement offline action sync here
}

// Push notifications
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/badge-72x72.png',
            vibrate: [100, 50, 100],
            data: data.data || {},
            actions: data.actions || []
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});

// Notification click handling
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'open') {
        event.waitUntil(
            clients.openWindow(event.notification.data.url || '/')
        );
    }
});