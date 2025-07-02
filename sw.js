// =============================================================================
// GST Intelligence Platform - Production Service Worker
// Version: 2.0.0
// =============================================================================

const CACHE_VERSION = 'v2.0.0';
const CACHE_PREFIX = 'gst-intelligence';
const STATIC_CACHE = `${CACHE_PREFIX}-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `${CACHE_PREFIX}-dynamic-${CACHE_VERSION}`;
const API_CACHE = `${CACHE_PREFIX}-api-${CACHE_VERSION}`;
const IMAGE_CACHE = `${CACHE_PREFIX}-images-${CACHE_VERSION}`;

// Cache configuration
const CACHE_CONFIG = {
    staticTTL: 24 * 60 * 60 * 1000, // 24 hours
    dynamicTTL: 2 * 60 * 60 * 1000,  // 2 hours
    apiTTL: 30 * 60 * 1000,          // 30 minutes
    imageTTL: 7 * 24 * 60 * 60 * 1000, // 7 days
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
    '/api/system/'
];

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Get cache name based on request type
 */
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

/**
 * Check if request should use network first strategy
 */
function isNetworkFirst(request) {
    const url = new URL(request.url);
    return NETWORK_FIRST_PATTERNS.some(pattern => 
        url.pathname.startsWith(pattern)
    );
}

/**
 * Check if request should use cache first strategy
 */
function isCacheFirst(request) {
    const url = new URL(request.url);
    return CACHE_FIRST_PATTERNS.some(pattern => 
        url.href.startsWith(pattern) || url.pathname.startsWith(pattern)
    );
}

/**
 * Create a cache entry with timestamp
 */
function createCacheEntry(response) {
    const entry = {
        response: response.clone(),
        timestamp: Date.now(),
        url: response.url
    };
    return entry;
}

/**
 * Check if cache entry is expired
 */
function isCacheExpired(entry, ttl) {
    return Date.now() - entry.timestamp > ttl;
}

/**
 * Clean up expired cache entries
 */
async function cleanupCache(cacheName, maxEntries, ttl) {
    try {
        const cache = await caches.open(cacheName);
        const keys = await cache.keys();
        
        if (keys.length <= maxEntries) return;
        
        // Remove oldest entries if over limit
        const entriesToDelete = keys.slice(0, keys.length - maxEntries);
        await Promise.all(
            entriesToDelete.map(key => cache.delete(key))
        );
        
        console.log(`🧹 Cleaned up ${entriesToDelete.length} entries from ${cacheName}`);
    } catch (error) {
        console.error(`❌ Error cleaning cache ${cacheName}:`, error);
    }
}

/**
 * Get network timeout based on request type
 */
function getNetworkTimeout(request) {
    const url = new URL(request.url);
    
    if (API_PATTERNS.some(pattern => url.pathname.startsWith(pattern))) {
        return 8000; // 8 seconds for API calls
    }
    
    if (url.pathname.startsWith('/static/')) {
        return 5000; // 5 seconds for static files
    }
    
    return 10000; // 10 seconds for other requests
}

/**
 * Create offline fallback response
 */
function createOfflineResponse(request) {
    const url = new URL(request.url);
    
    // For HTML pages, return offline page
    if (request.headers.get('Accept')?.includes('text/html')) {
        return new Response(`
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Offline - GST Intelligence</title>
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                        color: white;
                        margin: 0;
                        padding: 2rem;
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        text-align: center;
                    }
                    .container {
                        max-width: 400px;
                    }
                    .icon {
                        font-size: 4rem;
                        margin-bottom: 1rem;
                        opacity: 0.7;
                    }
                    h1 {
                        color: #7c3aed;
                        margin-bottom: 1rem;
                    }
                    p {
                        color: #94a3b8;
                        line-height: 1.6;
                        margin-bottom: 2rem;
                    }
                    .btn {
                        background: linear-gradient(135deg, #7c3aed, #a855f7);
                        color: white;
                        border: none;
                        padding: 0.75rem 1.5rem;
                        border-radius: 8px;
                        cursor: pointer;
                        font-weight: 600;
                        transition: transform 0.2s;
                    }
                    .btn:hover {
                        transform: translateY(-2px);
                    }
                    .status {
                        margin-top: 2rem;
                        padding: 1rem;
                        background: rgba(124, 58, 237, 0.1);
                        border-radius: 8px;
                        border: 1px solid rgba(124, 58, 237, 0.3);
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="icon">📱</div>
                    <h1>You're Offline</h1>
                    <p>GST Intelligence Platform is currently unavailable. Please check your internet connection and try again.</p>
                    <button class="btn" onclick="window.location.reload()">Try Again</button>
                    <div class="status">
                        <strong>Offline Mode Active</strong><br>
                        Some features may be limited while offline.
                    </div>
                </div>
                <script>
                    // Auto-retry when online
                    window.addEventListener('online', () => {
                        window.location.reload();
                    });
                </script>
            </body>
            </html>
        `, {
            status: 200,
            statusText: 'OK',
            headers: {
                'Content-Type': 'text/html',
                'Cache-Control': 'no-cache'
            }
        });
    }
    
    // For API calls, return JSON error
    if (url.pathname.startsWith('/api/')) {
        return new Response(JSON.stringify({
            success: false,
            error: 'Network unavailable',
            offline: true,
            message: 'This request requires an internet connection'
        }), {
            status: 503,
            statusText: 'Service Unavailable',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            }
        });
    }
    
    // For other requests, return generic error
    return new Response('Network unavailable', {
        status: 503,
        statusText: 'Service Unavailable',
        headers: {
            'Cache-Control': 'no-cache'
        }
    });
}

// =============================================================================
// CACHING STRATEGIES
// =============================================================================

/**
 * Network first strategy with cache fallback
 */
async function networkFirst(request) {
    const cacheName = getCacheName(request);
    const timeout = getNetworkTimeout(request);
    
    try {
        // Try network with timeout
        const networkPromise = fetch(request.clone());
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Network timeout')), timeout);
        });
        
        const response = await Promise.race([networkPromise, timeoutPromise]);
        
        if (response.ok) {
            // Cache successful response
            const cache = await caches.open(cacheName);
            await cache.put(request.clone(), response.clone());
            
            // Clean up cache if needed
            await cleanupCache(cacheName, CACHE_CONFIG.maxEntries.dynamic, CACHE_CONFIG.dynamicTTL);
            
            return response;
        }
        
        throw new Error(`Network response not ok: ${response.status}`);
        
    } catch (error) {
        console.log(`🌐 Network failed for ${request.url}, trying cache...`);
        
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

/**
 * Cache first strategy with network update
 */

async function cacheFirst(request) {
    const cacheName = getCacheName(request);
    
    try {
        // Try cache first
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            console.log(`⚡ Cache hit: ${request.url}`);
            
            // Update cache in background for next time
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

/**
 * Stale while revalidate strategy
 */
async function staleWhileRevalidate(request) {
    const cacheName = getCacheName(request);
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
    }).catch(error => {
        console.log(`🌐 Network update failed for ${request.url}:`, error);
        return null;
    });
    
    // Return cached version immediately if available
    if (cachedResponse) {
        console.log(`📦 Serving stale: ${request.url}`);
        return cachedResponse;
    }
    
    // Wait for network if no cache
    const networkResponse = await networkPromise;
    return networkResponse || createOfflineResponse(request);
}

// =============================================================================
// SERVICE WORKER EVENT HANDLERS
// =============================================================================

/**
 * Install event - cache critical resources
 */
self.addEventListener('install', event => {
    console.log('🔧 Service Worker installing...');
    
    event.waitUntil(
        (async () => {
            try {
                const cache = await caches.open(STATIC_CACHE);
                
                console.log('📦 Caching critical files...');
                await cache.addAll(CRITICAL_STATIC_FILES.map(url => {
                    return new Request(url, { cache: 'reload' });
                }));
                
                console.log('✅ Service Worker installed successfully');
                
                // Skip waiting to activate immediately
                await self.skipWaiting();
                
            } catch (error) {
                console.error('❌ Service Worker installation failed:', error);
                throw error;
            }
        })()
    );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', event => {
    console.log('🚀 Service Worker activating...');
    
    event.waitUntil(
        (async () => {
            try {
                // Clean up old caches
                const cacheNames = await caches.keys();
                const validCaches = [STATIC_CACHE, DYNAMIC_CACHE, API_CACHE, IMAGE_CACHE];
                
                const deletePromises = cacheNames
                    .filter(cacheName => 
                        cacheName.startsWith(CACHE_PREFIX) && 
                        !validCaches.includes(cacheName)
                    )
                    .map(cacheName => {
                        console.log(`🗑️ Deleting old cache: ${cacheName}`);
                        return caches.delete(cacheName);
                    });
                
                await Promise.all(deletePromises);
                
                // Claim all clients immediately
                await self.clients.claim();
                
                console.log('✅ Service Worker activated successfully');
                
            } catch (error) {
                console.error('❌ Service Worker activation failed:', error);
            }
        })()
    );
});

/**
 * Fetch event - handle all network requests
 */
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip chrome-extension and other non-http protocols
    if (!url.protocol.startsWith('http')) {
        return;
    }
    
    // Skip if request is for the service worker itself
    if (url.pathname.endsWith('/sw.js')) {
        return;
    }
    
    event.respondWith(
        (async () => {
            try {
                // Choose strategy based on request type
                if (isNetworkFirst(request)) {
                    return await networkFirst(request);
                }
                
                if (isCacheFirst(request)) {
                    return await cacheFirst(request);
                }
                
                // Default to stale while revalidate
                return await staleWhileRevalidate(request);
                
            } catch (error) {
                console.error(`❌ Fetch error for ${request.url}:`, error);
                return createOfflineResponse(request);
            }
        })()
    );
});

/**
 * Background sync event
 */
self.addEventListener('sync', event => {
    console.log('🔄 Background sync triggered:', event.tag);
    
    switch (event.tag) {
        case 'background-search':
            event.waitUntil(syncPendingSearches());
            break;
        case 'offline-analytics':
            event.waitUntil(syncOfflineAnalytics());
            break;
        case 'cache-cleanup':
            event.waitUntil(performCacheCleanup());
            break;
        default:
            console.log(`🤷 Unknown sync tag: ${event.tag}`);
    }
});

/**
 * Push notification event
 */
self.addEventListener('push', event => {
    console.log('📲 Push notification received');
    
    const options = {
        body: 'New GST compliance insights available',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        tag: 'gst-update',
        requireInteraction: false,
        actions: [
            {
                action: 'open',
                title: 'View Dashboard',
                icon: '/static/icons/open-24x24.png'
            },
            {
                action: 'dismiss',
                title: 'Dismiss',
                icon: '/static/icons/dismiss-24x24.png'
            }
        ],
        data: {
            url: '/',
            timestamp: Date.now()
        }
    };
    
    if (event.data) {
        try {
            const data = event.data.json();
            Object.assign(options, data);
        } catch (error) {
            console.error('❌ Error parsing push data:', error);
        }
    }
    
    event.waitUntil(
        self.registration.showNotification('GST Intelligence Platform', options)
    );
});

/**
 * Notification click event
 */
self.addEventListener('notificationclick', event => {
    console.log('🔔 Notification clicked:', event.action);
    
    event.notification.close();
    
    if (event.action === 'open' || !event.action) {
        const urlToOpen = event.notification.data?.url || '/';
        
        event.waitUntil(
            clients.matchAll({ type: 'window', includeUncontrolled: true })
                .then(clientList => {
                    // Check if app is already open
                    for (const client of clientList) {
                        if (client.url.includes(self.registration.scope)) {
                            client.navigate(urlToOpen);
                            return client.focus();
                        }
                    }
                    
                    // Open new window
                    return clients.openWindow(urlToOpen);
                })
        );
    }
});

/**
 * Message event - handle communication with main thread
 */
self.addEventListener('message', event => {
    const { type, payload } = event.data || {};
    
    switch (type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;
            
        case 'GET_CACHE_STATUS':
            event.ports[0]?.postMessage({
                type: 'CACHE_STATUS',
                caches: [STATIC_CACHE, DYNAMIC_CACHE, API_CACHE, IMAGE_CACHE],
                version: CACHE_VERSION
            });
            break;
            
        case 'CLEAR_CACHE':
            clearAllCaches().then(success => {
                event.ports[0]?.postMessage({
                    type: 'CACHE_CLEARED',
                    success
                });
            });
            break;
            
        case 'SYNC_DATA':
            self.registration.sync.register('offline-analytics');
            break;
            
        default:
            console.log(`📨 Unknown message type: ${type}`);
    }
});

// =============================================================================
// BACKGROUND SYNC FUNCTIONS
// =============================================================================

/**
 * Sync pending searches when online
 */
async function syncPendingSearches() {
    try {
        const pendingSearches = await getStoredData('pendingSearches') || [];
        
        for (const search of pendingSearches) {
            try {
                const response = await fetch('/api/search/batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(search)
                });
                
                if (response.ok) {
                    await removeStoredData('pendingSearches', search.id);
                    console.log(`✅ Synced search: ${search.id}`);
                }
            } catch (error) {
                console.error(`❌ Failed to sync search ${search.id}:`, error);
            }
        }
    } catch (error) {
        console.error('❌ Background sync failed:', error);
    }
}

/**
 * Sync offline analytics data
 */
async function syncOfflineAnalytics() {
    try {
        const analyticsData = await getStoredData('offlineAnalytics') || [];
        
        if (analyticsData.length > 0) {
            const response = await fetch('/api/analytics/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(analyticsData)
            });
            
            if (response.ok) {
                await clearStoredData('offlineAnalytics');
                console.log(`✅ Synced ${analyticsData.length} analytics events`);
            }
        }
    } catch (error) {
        console.error('❌ Analytics sync failed:', error);
    }
}

/**
 * Perform cache cleanup
 */
async function performCacheCleanup() {
    try {
        await Promise.all([
            cleanupCache(STATIC_CACHE, CACHE_CONFIG.maxEntries.static, CACHE_CONFIG.staticTTL),
            cleanupCache(DYNAMIC_CACHE, CACHE_CONFIG.maxEntries.dynamic, CACHE_CONFIG.dynamicTTL),
            cleanupCache(API_CACHE, CACHE_CONFIG.maxEntries.api, CACHE_CONFIG.apiTTL),
            cleanupCache(IMAGE_CACHE, CACHE_CONFIG.maxEntries.images, CACHE_CONFIG.imageTTL)
        ]);
        
        console.log('✅ Cache cleanup completed');
    } catch (error) {
        console.error('❌ Cache cleanup failed:', error);
    }
}

// =============================================================================
// STORAGE UTILITIES
// =============================================================================

/**
 * Store data in IndexedDB (simplified for service worker)
 */
async function storeData(key, data) {
    try {
        const cache = await caches.open('app-data');
        const response = new Response(JSON.stringify(data));
        await cache.put(key, response);
    } catch (error) {
        console.error(`❌ Failed to store data for ${key}:`, error);
    }
}

/**
 * Get data from IndexedDB
 */
async function getStoredData(key) {
    try {
        const cache = await caches.open('app-data');
        const response = await cache.match(key);
        if (response) {
            return await response.json();
        }
        return null;
    } catch (error) {
        console.error(`❌ Failed to get data for ${key}:`, error);
        return null;
    }
}

/**
 * Remove specific data item
 */
async function removeStoredData(key, itemId) {
    try {
        const data = await getStoredData(key) || [];
        const filtered = data.filter(item => item.id !== itemId);
        await storeData(key, filtered);
    } catch (error) {
        console.error(`❌ Failed to remove data item ${itemId}:`, error);
    }
}

/**
 * Clear all stored data for a key
 */
async function clearStoredData(key) {
    try {
        const cache = await caches.open('app-data');
        await cache.delete(key);
    } catch (error) {
        console.error(`❌ Failed to clear data for ${key}:`, error);
    }
}

/**
 * Clear all caches
 */
async function clearAllCaches() {
    try {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
        console.log('✅ All caches cleared');
        return true;
    } catch (error) {
        console.error('❌ Failed to clear caches:', error);
        return false;
    }
}

// =============================================================================
// PERIODIC MAINTENANCE
// =============================================================================

// Schedule periodic cache cleanup
setInterval(() => {
    self.registration.sync.register('cache-cleanup');
}, 60 * 60 * 1000); // Every hour

console.log('🎉 GST Intelligence Service Worker loaded successfully!');