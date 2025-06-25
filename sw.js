// =============================================================================
// GST Intelligence Platform - Complete Production Service Worker
// Version: 2.0.0 - Enhanced with loan management and offline functionality
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
    '/health',
    '/loans'
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

// Offline fallback pages
const OFFLINE_FALLBACKS = {
    '/': '/offline.html',
    '/search': '/offline-search.html',
    '/loans': '/offline-loans.html',
    '/history': '/offline-history.html',
    '/analytics': '/offline-analytics.html'
};

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Check if request should be cached
 */
function shouldCache(request) {
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') return false;
    
    // Skip chrome-extension and other special protocols
    if (!url.protocol.startsWith('http')) return false;
    
    // Skip requests with query parameters for sensitive operations
    if (url.pathname.includes('logout') || url.pathname.includes('admin')) return false;
    
    return true;
}

/**
 * Get appropriate cache name for request
 */
function getCacheName(request) {
    const url = new URL(request.url);
    
    // Static assets
    if (CACHE_FIRST_PATTERNS.some(pattern => url.href.includes(pattern))) {
        return STATIC_CACHE;
    }
    
    // API endpoints
    if (API_PATTERNS.some(pattern => url.pathname.startsWith(pattern))) {
        return API_CACHE;
    }
    
    // Images
    if (url.pathname.match(/\.(jpg|jpeg|png|gif|webp|svg|ico)$/i)) {
        return IMAGE_CACHE;
    }
    
    // Everything else
    return DYNAMIC_CACHE;
}

/**
 * Clean up old cache entries
 */
async function cleanupCache(cacheName, maxEntries, maxAge = null) {
    const cache = await caches.open(cacheName);
    const requests = await cache.keys();
    
    // Remove expired entries if maxAge is specified
    if (maxAge) {
        const now = Date.now();
        for (const request of requests) {
            const response = await cache.match(request);
            if (response) {
                const cachedTime = response.headers.get('sw-cached-time');
                if (cachedTime && (now - parseInt(cachedTime)) > maxAge) {
                    await cache.delete(request);
                }
            }
        }
    }
    
    // Remove oldest entries if over limit
    const remainingRequests = await cache.keys();
    if (remainingRequests.length > maxEntries) {
        const sortedRequests = remainingRequests.sort((a, b) => {
            // Sort by last modified or creation time
            return new URL(a.url).searchParams.get('_t') - new URL(b.url).searchParams.get('_t');
        });
        
        const toDelete = sortedRequests.slice(0, remainingRequests.length - maxEntries);
        await Promise.all(toDelete.map(request => cache.delete(request)));
    }
}

/**
 * Add timestamp to cached response
 */
function addCacheTimestamp(response) {
    const headers = new Headers(response.headers);
    headers.set('sw-cached-time', Date.now().toString());
    
    return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: headers
    });
}

/**
 * Create offline fallback response
 */
function createOfflineFallback(pathname) {
    const fallbackPage = OFFLINE_FALLBACKS[pathname] || '/offline.html';
    
    return new Response(`
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - GST Intelligence Platform</title>
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex; align-items: center; justify-content: center;
                    min-height: 100vh; margin: 0; background: #1a1625;
                    color: #e2e8f0; text-align: center; padding: 20px;
                }
                .offline-container {
                    max-width: 400px; padding: 40px; background: #2a2037;
                    border-radius: 20px; box-shadow: 0 20px 50px rgba(0,0,0,0.3);
                }
                .offline-icon { font-size: 4rem; margin-bottom: 20px; color: #7c3aed; }
                h1 { margin: 0 0 10px 0; color: #f8fafc; }
                p { margin: 0 0 20px 0; color: #cbd5e1; line-height: 1.6; }
                .retry-btn {
                    background: linear-gradient(135deg, #7c3aed, #a855f7);
                    color: white; border: none; padding: 12px 24px;
                    border-radius: 12px; cursor: pointer; font-weight: 600;
                    text-decoration: none; display: inline-block;
                    transition: transform 0.2s;
                }
                .retry-btn:hover { transform: translateY(-2px); }
            </style>
        </head>
        <body>
            <div class="offline-container">
                <div class="offline-icon">📡</div>
                <h1>You're Offline</h1>
                <p>Please check your internet connection and try again. Some features may be limited while offline.</p>
                <button class="retry-btn" onclick="window.location.reload()">
                    Try Again
                </button>
            </div>
        </body>
        </html>
    `, {
        status: 200,
        headers: {
            'Content-Type': 'text/html',
            'Cache-Control': 'no-cache'
        }
    });
}

// =============================================================================
// SERVICE WORKER EVENT HANDLERS
// =============================================================================

/**
 * Install event - cache critical resources
 */
self.addEventListener('install', event => {
    console.log('[SW] Installing Service Worker v' + CACHE_VERSION);
    
    event.waitUntil(
        (async () => {
            try {
                // Cache critical static files
                const staticCache = await caches.open(STATIC_CACHE);
                
                console.log('[SW] Caching critical static files...');
                await staticCache.addAll(CRITICAL_STATIC_FILES.map(url => {
                    return new Request(url, {
                        cache: 'reload' // Force fresh downloads during install
                    });
                }));
                
                console.log('[SW] Critical files cached successfully');
                
                // Skip waiting to activate immediately
                self.skipWaiting();
                
            } catch (error) {
                console.error('[SW] Failed to cache critical files:', error);
                // Don't fail the installation, just log the error
            }
        })()
    );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', event => {
    console.log('[SW] Activating Service Worker v' + CACHE_VERSION);
    
    event.waitUntil(
        (async () => {
            try {
                // Clean up old caches
                const cacheNames = await caches.keys();
                const oldCaches = cacheNames.filter(name => 
                    name.startsWith(CACHE_PREFIX) && !name.includes(CACHE_VERSION)
                );
                
                if (oldCaches.length > 0) {
                    console.log('[SW] Deleting old caches:', oldCaches);
                    await Promise.all(oldCaches.map(name => caches.delete(name)));
                }
                
                // Clean up existing caches
                await Promise.all([
                    cleanupCache(STATIC_CACHE, CACHE_CONFIG.maxEntries.static, CACHE_CONFIG.staticTTL),
                    cleanupCache(DYNAMIC_CACHE, CACHE_CONFIG.maxEntries.dynamic, CACHE_CONFIG.dynamicTTL),
                    cleanupCache(API_CACHE, CACHE_CONFIG.maxEntries.api, CACHE_CONFIG.apiTTL),
                    cleanupCache(IMAGE_CACHE, CACHE_CONFIG.maxEntries.images, CACHE_CONFIG.imageTTL)
                ]);
                
                // Take control of all clients
                await clients.claim();
                
                console.log('[SW] Service Worker activated successfully');
                
            } catch (error) {
                console.error('[SW] Activation failed:', error);
            }
        })()
    );
});

/**
 * Fetch event - handle all network requests
 */
self.addEventListener('fetch', event => {
    // Skip non-cacheable requests
    if (!shouldCache(event.request)) {
        return;
    }
    
    const url = new URL(event.request.url);
    
    // Handle different request types with appropriate strategies
    if (NETWORK_FIRST_PATTERNS.some(pattern => url.pathname.startsWith(pattern))) {
        // Network first strategy for dynamic content
        event.respondWith(handleNetworkFirst(event.request));
    } else if (CACHE_FIRST_PATTERNS.some(pattern => url.href.includes(pattern))) {
        // Cache first strategy for static assets
        event.respondWith(handleCacheFirst(event.request));
    } else {
        // Stale while revalidate for everything else
        event.respondWith(handleStaleWhileRevalidate(event.request));
    }
});

/**
 * Network first strategy - for dynamic content
 */
async function handleNetworkFirst(request) {
    const cacheName = getCacheName(request);
    
    try {
        // Try network first
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cache successful responses
            const cache = await caches.open(cacheName);
            const responseToCache = addCacheTimestamp(networkResponse.clone());
            cache.put(request, responseToCache);
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('[SW] Network failed, trying cache:', request.url);
        
        // Fall back to cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline fallback for navigation requests
        if (request.mode === 'navigate') {
            return createOfflineFallback(new URL(request.url).pathname);
        }
        
        // For other requests, return a generic offline response
        return new Response('Offline', { 
            status: 503,
            statusText: 'Service Unavailable'
        });
    }
}

/**
 * Cache first strategy - for static assets
 */
async function handleCacheFirst(request) {
    const cacheName = getCacheName(request);
    
    // Try cache first
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        // Fall back to network
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cache for next time
            const cache = await caches.open(cacheName);
            const responseToCache = addCacheTimestamp(networkResponse.clone());
            cache.put(request, responseToCache);
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('[SW] Failed to fetch static asset:', request.url);
        
        // Return a generic fallback for failed static assets
        if (request.url.includes('.css')) {
            return new Response('/* Offline CSS */', {
                headers: { 'Content-Type': 'text/css' }
            });
        }
        
        if (request.url.includes('.js')) {
            return new Response('// Offline JS', {
                headers: { 'Content-Type': 'application/javascript' }
            });
        }
        
        return new Response('Resource unavailable offline', { status: 503 });
    }
}

/**
 * Stale while revalidate strategy - for most content
 */
async function handleStaleWhileRevalidate(request) {
    const cacheName = getCacheName(request);
    const cache = await caches.open(cacheName);
    
    // Get cached response
    const cachedResponse = await cache.match(request);
    
    // Always try to fetch fresh content in background
    const fetchPromise = fetch(request).then(networkResponse => {
        if (networkResponse.ok) {
            const responseToCache = addCacheTimestamp(networkResponse.clone());
            cache.put(request, responseToCache);
        }
        return networkResponse;
    }).catch(error => {
        console.log('[SW] Background fetch failed:', request.url);
        return null;
    });
    
    // Return cached response immediately if available
    if (cachedResponse) {
        return cachedResponse;
    }
    
    // If no cache, wait for network
    try {
        const networkResponse = await fetchPromise;
        if (networkResponse) {
            return networkResponse;
        }
    } catch (error) {
        // Network failed and no cache
    }
    
    // Return offline fallback for navigation requests
    if (request.mode === 'navigate') {
        return createOfflineFallback(new URL(request.url).pathname);
    }
    
    return new Response('Content unavailable', { status: 503 });
}

/**
 * Message event - handle messages from main thread
 */
self.addEventListener('message', event => {
    if (event.data && event.data.type) {
        switch (event.data.type) {
            case 'SKIP_WAITING':
                self.skipWaiting();
                break;
                
            case 'CACHE_URLS':
                if (event.data.urls) {
                    cacheUrls(event.data.urls);
                }
                break;
                
            case 'CLEAR_CACHE':
                clearAllCaches();
                break;
                
            case 'GET_CACHE_SIZE':
                getCacheSize().then(size => {
                    event.ports[0].postMessage({ type: 'CACHE_SIZE', size });
                });
                break;
        }
    }
});

/**
 * Background sync event - handle offline actions
 */
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        event.waitUntil(handleBackgroundSync());
    }
});

/**
 * Push event - handle push notifications
 */
self.addEventListener('push', event => {
    if (event.data) {
        const options = {
            body: event.data.text(),
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/badge-72x72.png',
            vibrate: [200, 100, 200],
            tag: 'gst-notification',
            actions: [
                {
                    action: 'open',
                    title: 'Open App',
                    icon: '/static/icons/open-24x24.png'
                },
                {
                    action: 'close',
                    title: 'Close',
                    icon: '/static/icons/close-24x24.png'
                }
            ]
        };
        
        event.waitUntil(
            self.registration.showNotification('GST Intelligence Platform', options)
        );
    }
});

/**
 * Notification click event
 */
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'open') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Cache specific URLs
 */
async function cacheUrls(urls) {
    const cache = await caches.open(DYNAMIC_CACHE);
    await cache.addAll(urls);
    console.log('[SW] Cached additional URLs:', urls.length);
}

/**
 * Clear all caches
 */
async function clearAllCaches() {
    const cacheNames = await caches.keys();
    await Promise.all(
        cacheNames
            .filter(name => name.startsWith(CACHE_PREFIX))
            .map(name => caches.delete(name))
    );
    console.log('[SW] All caches cleared');
}

/**
 * Get total cache size
 */
async function getCacheSize() {
    const cacheNames = await caches.keys();
    let totalSize = 0;
    
    for (const cacheName of cacheNames) {
        if (cacheName.startsWith(CACHE_PREFIX)) {
            const cache = await caches.open(cacheName);
            const requests = await cache.keys();
            
            for (const request of requests) {
                const response = await cache.match(request);
                if (response && response.body) {
                    // Estimate size (not exact, but good enough)
                    totalSize += new Blob([response.body]).size;
                }
            }
        }
    }
    
    return totalSize;
}

/**
 * Handle background sync
 */
async function handleBackgroundSync() {
    // Handle any offline actions that need to be synced
    console.log('[SW] Background sync triggered');
    
    // Example: sync offline search queries, loan applications, etc.
    // This would integrate with your app's offline queue
}

/**
 * Periodic cache cleanup
 */
setInterval(async () => {
    try {
        await Promise.all([
            cleanupCache(STATIC_CACHE, CACHE_CONFIG.maxEntries.static, CACHE_CONFIG.staticTTL),
            cleanupCache(DYNAMIC_CACHE, CACHE_CONFIG.maxEntries.dynamic, CACHE_CONFIG.dynamicTTL),
            cleanupCache(API_CACHE, CACHE_CONFIG.maxEntries.api, CACHE_CONFIG.apiTTL),
            cleanupCache(IMAGE_CACHE, CACHE_CONFIG.maxEntries.images, CACHE_CONFIG.imageTTL)
        ]);
        console.log('[SW] Periodic cache cleanup completed');
    } catch (error) {
        console.error('[SW] Cache cleanup failed:', error);
    }
}, 60 * 60 * 1000); // Run every hour

console.log('[SW] Service Worker v' + CACHE_VERSION + ' loaded successfully');

// =============================================================================
// PWA INSTALL PROMPT HANDLING
// =============================================================================

/**
 * Handle app install prompt
 */
self.addEventListener('beforeinstallprompt', event => {
    // Prevent the default install prompt
    event.preventDefault();
    
    // Store the event for later use
    self.deferredPrompt = event;
    
    // Notify the main thread that install is available
    self.clients.matchAll().then(clients => {
        clients.forEach(client => {
            client.postMessage({
                type: 'INSTALL_AVAILABLE'
            });
        });
    });
});

/**
 * Handle successful app install
 */
self.addEventListener('appinstalled', event => {
    console.log('[SW] App installed successfully');
    
    // Notify the main thread
    self.clients.matchAll().then(clients => {
        clients.forEach(client => {
            client.postMessage({
                type: 'APP_INSTALLED'
            });
        });
    });
});

// Export for testing (if in test environment)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        CACHE_VERSION,
        shouldCache,
        getCacheName,
        cleanupCache
    };
}