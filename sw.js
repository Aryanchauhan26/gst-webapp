// /sw.js - Optimized Service Worker
const CACHE_VERSION = "v2.2.0";
const CACHE_PREFIX = "gst-intelligence";
const STATIC_CACHE = `${CACHE_PREFIX}-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `${CACHE_PREFIX}-dynamic-${CACHE_VERSION}`;
const API_CACHE = `${CACHE_PREFIX}-api-${CACHE_VERSION}`;

const CACHE_CONFIG = {
    staticTTL: 24 * 60 * 60 * 1000, // 24 hours
    dynamicTTL: 2 * 60 * 60 * 1000, // 2 hours
    apiTTL: 30 * 60 * 1000, // 30 minutes
    maxEntries: { static: 100, dynamic: 50, api: 30 },
};

const CRITICAL_STATIC_FILES = [
    "/",
    "/static/css/base.css",
    "/static/js/missing-globals.js",
    "/static/js/app-core.js",
    "/static/manifest.json",
];

const NETWORK_FIRST_PATTERNS = ["/api/", "/search", "/logout", "/health"];
const CACHE_FIRST_PATTERNS = ["/static/", "https://cdnjs.cloudflare.com/"];

// Install event - cache critical files
self.addEventListener("install", (event) => {
    console.log("🔧 Service Worker installing...");

    event.waitUntil(
        caches
            .open(STATIC_CACHE)
            .then((cache) => {
                console.log("📦 Caching critical static files");
                return cache.addAll(CRITICAL_STATIC_FILES);
            })
            .then(() => {
                console.log("✅ Service Worker installed successfully");
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error("❌ Service Worker install failed:", error);
            }),
    );
});

// Activate event - clean old caches
self.addEventListener("activate", (event) => {
    console.log("🚀 Service Worker activating...");

    event.waitUntil(
        caches
            .keys()
            .then((cacheNames) => {
                const deletePromises = cacheNames
                    .filter(
                        (cacheName) =>
                            cacheName.startsWith(CACHE_PREFIX) &&
                            !cacheName.includes(CACHE_VERSION),
                    )
                    .map((cacheName) => {
                        console.log("🗑️ Deleting old cache:", cacheName);
                        return caches.delete(cacheName);
                    });

                return Promise.all(deletePromises);
            })
            .then(() => {
                console.log("✅ Service Worker activated successfully");
                return self.clients.claim();
            })
            .catch((error) => {
                console.error("❌ Service Worker activation failed:", error);
            }),
    );
});

// Fetch event - handle all requests
self.addEventListener("fetch", (event) => {
    const { request } = event;
    const { url, method } = request;

    // Only handle GET requests
    if (method !== "GET") {
        return;
    }

    // Skip chrome-extension and other non-http(s) requests
    if (!url.startsWith("http")) {
        return;
    }

    event.respondWith(handleRequest(request));
});

// Main request handler
async function handleRequest(request) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    try {
        // Network first for API calls and dynamic content
        if (shouldUseNetworkFirst(pathname)) {
            return await networkFirst(request);
        }

        // Cache first for static assets
        if (shouldUseCacheFirst(pathname)) {
            return await cacheFirst(request);
        }

        // Stale while revalidate for HTML pages
        return await staleWhileRevalidate(request);
    } catch (error) {
        console.error("Request handling failed:", error);
        return await handleOffline(request);
    }
}

// Network first strategy
async function networkFirst(request) {
    try {
        const response = await fetch(request);

        // Cache successful API responses
        if (response.ok && isApiRequest(request.url)) {
            const cache = await caches.open(API_CACHE);
            cache.put(request, response.clone());

            // Clean up old API cache entries
            await cleanupCache(API_CACHE, CACHE_CONFIG.maxEntries.api);
        }

        return response;
    } catch (error) {
        // Try cache if network fails
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            console.log("📱 Serving from cache (offline):", request.url);
            return cachedResponse;
        }

        throw error;
    }
}

// Cache first strategy
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
        // Check if cache is still fresh
        const cacheTime = getCacheTime(cachedResponse);
        const now = Date.now();

        if (cacheTime && now - cacheTime < CACHE_CONFIG.staticTTL) {
            return cachedResponse;
        }
    }

    try {
        const response = await fetch(request);

        if (response.ok) {
            const cache = await caches.open(STATIC_CACHE);
            const responseToCache = response.clone();

            // Add timestamp header
            const headers = new Headers(responseToCache.headers);
            headers.set("sw-cache-time", Date.now().toString());

            const modifiedResponse = new Response(responseToCache.body, {
                status: responseToCache.status,
                statusText: responseToCache.statusText,
                headers: headers,
            });

            cache.put(request, modifiedResponse);

            // Clean up old static cache entries
            await cleanupCache(STATIC_CACHE, CACHE_CONFIG.maxEntries.static);
        }

        return response;
    } catch (error) {
        // Return cached version if available
        if (cachedResponse) {
            return cachedResponse;
        }

        throw error;
    }
}

// Stale while revalidate strategy
async function staleWhileRevalidate(request) {
    const cache = await caches.open(DYNAMIC_CACHE);
    const cachedResponse = await cache.match(request);

    // Always try to fetch from network
    const networkPromise = fetch(request)
        .then((response) => {
            if (response.ok) {
                // Update cache in background
                cache.put(request, response.clone());

                // Clean up old dynamic cache entries
                cleanupCache(DYNAMIC_CACHE, CACHE_CONFIG.maxEntries.dynamic);
            }
            return response;
        })
        .catch(() => null);

    // Return cached version immediately if available
    if (cachedResponse) {
        networkPromise; // Update cache in background
        return cachedResponse;
    }

    // Otherwise wait for network
    const networkResponse = await networkPromise;
    if (networkResponse) {
        return networkResponse;
    }

    // Final fallback
    throw new Error("No cached response and network failed");
}

// Handle offline scenarios
async function handleOffline(request) {
    const url = new URL(request.url);

    // Try to find a cached version
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }

    // For HTML pages, return offline page
    if (request.headers.get("accept")?.includes("text/html")) {
        const offlineResponse = await caches.match("/");
        if (offlineResponse) {
            return offlineResponse;
        }
    }

    // For images, return placeholder
    if (request.headers.get("accept")?.includes("image/")) {
        return new Response(
            '<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#f3f4f6"/><text x="50%" y="50%" text-anchor="middle" fill="#6b7280">Image unavailable offline</text></svg>',
            { headers: { "Content-Type": "image/svg+xml" } },
        );
    }

    // Default offline response
    return new Response("Offline - content not available", {
        status: 503,
        statusText: "Service Unavailable",
    });
}

// Helper functions
function shouldUseNetworkFirst(pathname) {
    return NETWORK_FIRST_PATTERNS.some((pattern) => pathname.includes(pattern));
}

function shouldUseCacheFirst(pathname) {
    return CACHE_FIRST_PATTERNS.some((pattern) => pathname.includes(pattern));
}

function isApiRequest(url) {
    return url.includes("/api/");
}

function getCacheTime(response) {
    const cacheTime = response.headers.get("sw-cache-time");
    return cacheTime ? parseInt(cacheTime) : null;
}

// Clean up old cache entries
async function cleanupCache(cacheName, maxEntries) {
    try {
        const cache = await caches.open(cacheName);
        const keys = await cache.keys();

        if (keys.length > maxEntries) {
            const entriesToDelete = keys.slice(0, keys.length - maxEntries);
            await Promise.all(entriesToDelete.map((key) => cache.delete(key)));
            console.log(
                `🧹 Cleaned up ${entriesToDelete.length} entries from ${cacheName}`,
            );
        }
    } catch (error) {
        console.error("Cache cleanup failed:", error);
    }
}

// Background sync for offline actions
self.addEventListener("sync", (event) => {
    console.log("🔄 Background sync:", event.tag);

    if (event.tag === "background-sync") {
        event.waitUntil(handleBackgroundSync());
    }
});

async function handleBackgroundSync() {
    try {
        // Handle any pending offline actions
        console.log("📡 Handling background sync");

        // Example: Sync offline search queries
        const offlineActions = await getOfflineActions();
        for (const action of offlineActions) {
            try {
                await syncAction(action);
                await removeOfflineAction(action.id);
            } catch (error) {
                console.error("Failed to sync action:", error);
            }
        }
    } catch (error) {
        console.error("Background sync failed:", error);
    }
}

// Offline action management
async function getOfflineActions() {
    // Implementation would depend on your offline storage strategy
    return [];
}

async function syncAction(action) {
    // Implementation for syncing specific actions
    console.log("Syncing action:", action);
}

async function removeOfflineAction(actionId) {
    // Implementation for removing synced actions
    console.log("Removing offline action:", actionId);
}

// Push notification handling
self.addEventListener("push", (event) => {
    console.log("📬 Push notification received");

    if (!event.data) return;

    try {
        const data = event.data.json();
        const options = {
            body: data.body || "New notification",
            icon: "/static/icons/icon-192x192.png",
            badge: "/static/icons/badge-72x72.png",
            tag: data.tag || "general",
            data: data.data || {},
            actions: data.actions || [],
            requireInteraction: data.requireInteraction || false,
        };

        event.waitUntil(
            self.registration.showNotification(
                data.title || "GST Intelligence",
                options,
            ),
        );
    } catch (error) {
        console.error("Push notification handling failed:", error);
    }
});

// Notification click handling
self.addEventListener("notificationclick", (event) => {
    console.log("🔔 Notification clicked");

    event.notification.close();

    const urlToOpen = event.notification.data?.url || "/";

    event.waitUntil(
        clients
            .matchAll({ type: "window", includeUncontrolled: true })
            .then((clientList) => {
                // Check if app is already open
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin)) {
                        client.focus();
                        client.navigate(urlToOpen);
                        return;
                    }
                }

                // Open new window
                return clients.openWindow(urlToOpen);
            }),
    );
});

// Message handling from main thread
self.addEventListener("message", (event) => {
    console.log("💬 Message received:", event.data);

    if (event.data?.type === "SKIP_WAITING") {
        self.skipWaiting();
    }

    if (event.data?.type === "GET_VERSION") {
        event.ports[0].postMessage({ version: CACHE_VERSION });
    }

    if (event.data?.type === "CLEAR_CACHE") {
        clearAllCaches().then(() => {
            event.ports[0].postMessage({ success: true });
        });
    }
});

// Clear all caches
async function clearAllCaches() {
    try {
        const cacheNames = await caches.keys();
        const deletePromises = cacheNames
            .filter((name) => name.startsWith(CACHE_PREFIX))
            .map((name) => caches.delete(name));

        await Promise.all(deletePromises);
        console.log("🧹 All caches cleared");
    } catch (error) {
        console.error("Failed to clear caches:", error);
    }
}

console.log(`🚀 GST Intelligence Service Worker ${CACHE_VERSION} loaded`);
