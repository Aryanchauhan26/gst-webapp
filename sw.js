// =============================================================================
// GST Intelligence Platform - Enhanced Service Worker
// Version: 2.1.0 - Fixed duplicates and improved functionality
// =============================================================================

const CACHE_VERSION = 'v2.1.0';
const CACHE_PREFIX = 'gst-intelligence';
const STATIC_CACHE = `${CACHE_PREFIX}-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `${CACHE_PREFIX}-dynamic-${CACHE_VERSION}`;
const API_CACHE = `${CACHE_PREFIX}-api-${CACHE_VERSION}`;
const IMAGE_CACHE = `${CACHE_PREFIX}-images-${CACHE_VERSION}`;

// Cache configuration
const CACHE_CONFIG = {
    staticTTL: 24 * 60 * 60 * 1000,     // 24 hours
    dynamicTTL: 2 * 60 * 60 * 1000,     // 2 hours
    apiTTL: 30 * 60 * 1000,             // 30 minutes
    imageTTL: 7 * 24 * 60 * 60 * 1000,  // 7 days
    maxEntries: {
        static: 100,
        dynamic: 50,
        api: 30,
        images: 50
    }
};

// Critical files to cache immediately on install
const CRITICAL_STATIC_FILES = [
    '/',
    '/login',
    '/signup',
    '/static/css/base.css',
    '/static/js/app.js',
    '/static/js/missing-implementations.js',
    '/static/js/integration-fixes.js',
    '/static/js/enhanced-error-handling.js',
    '/static/manifest.json',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
];

// Files that should always be fetched from network first
const NETWORK_FIRST_PATTERNS = [
    '/api/',
    '/search',
    '/generate-pdf',
    '/export/',
    '/logout',
    '/health'
];

// Files that can be served from cache first
const CACHE_FIRST_PATTERNS = [
    '/static/',
    'https://cdnjs.cloudflare.com/',
    'https://fonts.googleapis.com/',
    'https://fonts.gstatic.com/'
];

// API endpoints for special handling
const API_PATTERNS = [
    '/api/user/',
    '/api/search/',
    '/api/system/',
    '/api/loans/',
    '/api/admin/'
];

// =============================================================================
// CORE EVENT HANDLERS
// =============================================================================

self.addEventListener('install', event => {
    console.log('🔧 Service Worker installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('📦 Pre-caching critical resources...');
                return cache.addAll(CRITICAL_STATIC_FILES);
            })
            .then(() => {
                console.log('✅ Critical resources cached successfully');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('❌ Error caching critical resources:', error);
                // Don't fail installation if some resources fail to cache
                return self.skipWaiting();
            })
    );
});

self.addEventListener('activate', event => {
    console.log('🚀 Service Worker activating...');
    
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            cleanupOldCaches(),
            // Take control of all open pages
            self.clients.claim()
        ]).then(() => {
            console.log('✅ Service Worker activated successfully');
        })
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(handleFetch(event.request));
});

// Background sync for offline actions
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        event.waitUntil(handleBackgroundSync());
    }
});

// Push notifications
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        event.waitUntil(handlePushNotification(data));
    }
});

// =============================================================================
// FETCH HANDLING STRATEGIES
// =============================================================================

async function handleFetch(request) {
    const url = new URL(request.url);
    
    // Skip non-GET requests for caching
    if (request.method !== 'GET') {
        return fetch(request);
    }
    
    // Skip chrome-extension requests
    if (url.protocol === 'chrome-extension:') {
        return fetch(request);
    }
    
    // Choose strategy based on request type
    if (isNetworkFirst(request)) {
        return networkFirst(request);
    } else if (isCacheFirst(request)) {
        return cacheFirst(request);
    } else {
        return staleWhileRevalidate(request);
    }
}

async function networkFirst(request) {
    const cacheName = getCacheName(request);
    
    try {
        // Try network first
        const response = await fetch(request.clone());
        
        if (response.ok) {
            // Cache successful responses
            try {
                const cache = await caches.open(cacheName);
                await cache.put(request.clone(), response.clone());
                await cleanupCache(cacheName, CACHE_CONFIG.maxEntries.api, CACHE_CONFIG.apiTTL);
            } catch (cacheError) {
                console.warn('Cache storage failed:', cacheError);
            }
        }
        
        return response;
        
    } catch (error) {
        console.warn(`⚠️ Network failed for ${request.url}, trying cache...`);
        
        // Try cache fallback
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            console.log(`💾 Serving from cache: ${request.url}`);
            return cachedResponse;
        }
        
        // Return offline response
        console.log(`📱 Serving offline response for: ${request.url}`);
        return createOfflineResponse(request);
    }
}

async function cacheFirst(request) {
    const cacheName = getCacheName(request);
    
    try {
        // Try cache first
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            console.log(`⚡ Cache hit: ${request.url}`);
            
            // Update cache in background for next time
            updateCacheInBackground(request, cacheName);
            
            return cachedResponse;
        }
        
        // Cache miss, fetch from network
        const response = await fetch(request);
        
        if (response.ok) {
            try {
                const cache = await caches.open(cacheName);
                await cache.put(request.clone(), response.clone());
                await cleanupCache(cacheName, CACHE_CONFIG.maxEntries.static, CACHE_CONFIG.staticTTL);
            } catch (cacheError) {
                console.warn('Cache storage failed:', cacheError);
            }
        }
        
        return response;
        
    } catch (error) {
        console.error(`❌ Failed to fetch ${request.url}:`, error);
        return createOfflineResponse(request);
    }
}

async function staleWhileRevalidate(request) {
    const cacheName = getCacheName(request);
    
    try {
        const cache = await caches.open(cacheName);
        
        // Get cached version
        const cachedResponse = await cache.match(request);
        
        // Start network request
        const networkPromise = fetch(request.clone()).then(async response => {
            if (response.ok) {
                await cache.put(request.clone(), response.clone());
                await cleanupCache(cacheName, CACHE_CONFIG.maxEntries.dynamic, CACHE_CONFIG.dynamicTTL);
            }
            return response;
        });
        
        // Return cached version immediately if available
        if (cachedResponse) {
            console.log(`⚡ Serving stale: ${request.url}`);
            networkPromise.catch(() => {}); // Handle network error silently
            return cachedResponse;
        }
        
        // If no cached version, wait for network
        return await networkPromise;
        
    } catch (error) {
        console.error(`❌ SWR failed for ${request.url}:`, error);
        return createOfflineResponse(request);
    }
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

function getCacheName(request) {
    const url = new URL(request.url);
    
    if (API_PATTERNS.some(pattern => url.pathname.startsWith(pattern))) {
        return API_CACHE;
    }
    
    if (url.pathname.startsWith('/static/') || url.hostname !== location.hostname) {
        if (request.destination === 'image') {
            return IMAGE_CACHE;
        }
        return STATIC_CACHE;
    }
    
    return DYNAMIC_CACHE;
}

function isNetworkFirst(request) {
    const url = new URL(request.url);
    return NETWORK_FIRST_PATTERNS.some(pattern => 
        url.pathname.startsWith(pattern)
    );
}

function isCacheFirst(request) {
    const url = new URL(request.url);
    return CACHE_FIRST_PATTERNS.some(pattern => 
        url.href.startsWith(pattern) || url.pathname.startsWith(pattern)
    );
}

function updateCacheInBackground(request, cacheName) {
    // Update cache in background without blocking response
    fetch(request.clone()).then(async response => {
        if (response.ok) {
            try {
                const cache = await caches.open(cacheName);
                await cache.put(request.clone(), response.clone());
            } catch (cacheError) {
                console.warn('Background cache update failed:', cacheError);
            }
        }
    }).catch(() => {
        // Ignore background update errors
    });
}

async function cleanupCache(cacheName, maxEntries, ttl) {
    try {
        const cache = await caches.open(cacheName);
        const keys = await cache.keys();
        
        if (keys.length <= maxEntries) return;
        
        // Remove oldest entries
        const keysToDelete = keys.slice(0, keys.length - maxEntries);
        await Promise.all(keysToDelete.map(key => cache.delete(key)));
        
        console.log(`🧹 Cleaned up ${keysToDelete.length} cache entries from ${cacheName}`);
        
    } catch (error) {
        console.warn('Cache cleanup failed:', error);
    }
}

async function cleanupOldCaches() {
    try {
        const cacheNames = await caches.keys();
        const oldCaches = cacheNames.filter(name => 
            name.startsWith(CACHE_PREFIX) && !name.includes(CACHE_VERSION)
        );
        
        await Promise.all(oldCaches.map(name => caches.delete(name)));
        
        if (oldCaches.length > 0) {
            console.log(`🧹 Deleted ${oldCaches.length} old cache versions`);
        }
        
    } catch (error) {
        console.warn('Old cache cleanup failed:', error);
    }
}

function createOfflineResponse(request) {
    const url = new URL(request.url);
    
    // For HTML pages, return offline page
    if (request.headers.get('accept').includes('text/html')) {
        return new Response(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Offline - GST Intelligence</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        text-align: center; 
                        padding: 50px; 
                        background: #1a1a1a; 
                        color: #fff;
                    }
                    .offline-icon { font-size: 64px; margin-bottom: 20px; }
                    .offline-message { font-size: 18px; margin-bottom: 30px; }
                    .retry-btn { 
                        background: #007bff; 
                        color: white; 
                        border: none; 
                        padding: 12px 24px; 
                        border-radius: 4px; 
                        cursor: pointer; 
                        font-size: 16px;
                    }
                </style>
            </head>
            <body>
                <div class="offline-icon">📱</div>
                <h1>You're Offline</h1>
                <p class="offline-message">
                    Please check your internet connection and try again.
                </p>
                <button class="retry-btn" onclick="window.location.reload()">
                    Retry
                </button>
            </body>
            </html>
        `, {
            status: 200,
            headers: { 'Content-Type': 'text/html' }
        });
    }
    
    // For API requests, return JSON error
    if (url.pathname.startsWith('/api/')) {
        return new Response(JSON.stringify({
            success: false,
            error: 'You are offline. Please check your internet connection.'
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
    // For other requests, return generic error
    return new Response('Offline', { status: 503 });
}

// =============================================================================
// BACKGROUND SYNC AND NOTIFICATIONS
// =============================================================================

async function handleBackgroundSync() {
    try {
        console.log('🔄 Handling background sync...');
        
        // Handle offline actions stored in IndexedDB
        const offlineActions = await getOfflineActions();
        
        for (const action of offlineActions) {
            try {
                await fetch(action.url, {
                    method: action.method,
                    headers: action.headers,
                    body: action.body
                });
                
                // Remove successfully synced action
                await removeOfflineAction(action.id);
                
            } catch (error) {
                console.warn('Failed to sync action:', error);
            }
        }
        
    } catch (error) {
        console.error('Background sync failed:', error);
    }
}

async function handlePushNotification(data) {
    const options = {
        body: data.body,
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: data.data || {},
        actions: [
            {
                action: 'view',
                title: 'View',
                icon: '/static/icons/view.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss',
                icon: '/static/icons/dismiss.png'
            }
        ]
    };
    
    return self.registration.showNotification(data.title, options);
}

// Placeholder functions for IndexedDB operations
async function getOfflineActions() {
    // Implement IndexedDB read for offline actions
    return [];
}

async function removeOfflineAction(id) {
    // Implement IndexedDB delete for offline action
    return true;
}

// =============================================================================
// MESSAGE HANDLING
// =============================================================================

self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('🚀 Service Worker loaded successfully');