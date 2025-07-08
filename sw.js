// /sw.js - Enhanced Service Worker for GST Intelligence Platform
const CACHE_VERSION = "v2.3.0";
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
    "/static/icons/favicon.svg",
    "/static/icons/favicon.png",
    "/offline.html", // Offline fallback page
];

const NETWORK_FIRST_PATTERNS = [
    "/api/",
    "/search",
    "/logout",
    "/health",
    "/admin",
];
const CACHE_FIRST_PATTERNS = ["/static/", "https://cdnjs.cloudflare.com/"];
const STALE_WHILE_REVALIDATE_PATTERNS = ["/dashboard", "/profile"];

// Install event - cache critical files
self.addEventListener("install", (event) => {
    console.log("🔧 Service Worker installing...");

    event.waitUntil(
        caches
            .open(STATIC_CACHE)
            .then((cache) => {
                console.log("📦 Caching critical static files");
                return cache.addAll(
                    CRITICAL_STATIC_FILES.filter(
                        (url) => url !== "/offline.html",
                    ),
                );
            })
            .then(() => {
                // Cache offline page separately to handle potential 404
                return caches.open(STATIC_CACHE).then((cache) => {
                    return fetch("/offline.html")
                        .then((response) => {
                            if (response.ok) {
                                return cache.put("/offline.html", response);
                            }
                        })
                        .catch(() => {
                            // Create a basic offline page if none exists
                            const offlineResponse = new Response(
                                createOfflineHTML(),
                                { headers: { "Content-Type": "text/html" } },
                            );
                            return cache.put("/offline.html", offlineResponse);
                        });
                });
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
                console.log("✅ Service Worker activated");
                return self.clients.claim();
            })
            .catch((error) => {
                console.error("❌ Service Worker activation failed:", error);
            }),
    );
});

// Fetch event - implement caching strategies
self.addEventListener("fetch", (event) => {
    const request = event.request;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== "GET") {
        return;
    }

    // Skip Chrome extensions and other non-http(s) requests
    if (!url.protocol.includes("http")) {
        return;
    }

    event.respondWith(handleRequest(request));
});

async function handleRequest(request) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    try {
        // Network first for API endpoints and dynamic content
        if (
            NETWORK_FIRST_PATTERNS.some((pattern) => pathname.includes(pattern))
        ) {
            return await networkFirst(request, API_CACHE);
        }

        // Cache first for static assets
        if (
            CACHE_FIRST_PATTERNS.some((pattern) =>
                request.url.includes(pattern),
            )
        ) {
            return await cacheFirst(request, STATIC_CACHE);
        }

        // Stale while revalidate for user pages
        if (
            STALE_WHILE_REVALIDATE_PATTERNS.some((pattern) =>
                pathname.includes(pattern),
            )
        ) {
            return await staleWhileRevalidate(request, DYNAMIC_CACHE);
        }

        // Default strategy: Network first with cache fallback
        return await networkFirst(request, DYNAMIC_CACHE);
    } catch (error) {
        console.error("Fetch error:", error);
        return await handleOffline(request);
    }
}

async function networkFirst(request, cacheName) {
    try {
        const networkResponse = await fetch(request);

        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;
    } catch (error) {
        console.log("Network failed, trying cache:", request.url);
        const cachedResponse = await caches.match(request);

        if (cachedResponse) {
            return cachedResponse;
        }

        throw error;
    }
}

async function cacheFirst(request, cacheName) {
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
        // Check if cache is expired
        const cacheTime = await getCacheTime(request);
        const now = Date.now();

        if (cacheTime && now - cacheTime > CACHE_CONFIG.staticTTL) {
            // Cache expired, update in background
            updateCache(request, cacheName);
        }

        return cachedResponse;
    }

    try {
        const networkResponse = await fetch(request);

        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            await cache.put(request, networkResponse.clone());
            await setCacheTime(request);
        }

        return networkResponse;
    } catch (error) {
        throw error;
    }
}

async function staleWhileRevalidate(request, cacheName) {
    const cachedResponse = await caches.match(request);

    // Always try to update from network in background
    const fetchPromise = fetch(request)
        .then(async (response) => {
            if (response.ok) {
                const cache = await caches.open(cacheName);
                await cache.put(request, response.clone());
                await setCacheTime(request);
            }
            return response;
        })
        .catch((error) => {
            console.log("Background update failed:", error);
        });

    // Return cached version immediately if available
    if (cachedResponse) {
        return cachedResponse;
    }

    // If no cache, wait for network
    return await fetchPromise;
}

async function updateCache(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            await cache.put(request, response.clone());
            await setCacheTime(request);
        }
    } catch (error) {
        console.log("Background cache update failed:", error);
    }
}

async function handleOffline(request) {
    const url = new URL(request.url);

    // Return offline page for navigation requests
    if (request.mode === "navigate") {
        const offlineResponse = await caches.match("/offline.html");
        if (offlineResponse) {
            return offlineResponse;
        }

        // Fallback offline page if not cached
        return new Response(createOfflineHTML(), {
            status: 200,
            statusText: "OK",
            headers: { "Content-Type": "text/html" },
        });
    }

    // Return a generic offline response for other requests
    return new Response(
        JSON.stringify({ error: "Offline", message: "No network connection" }),
        {
            status: 503,
            statusText: "Service Unavailable",
            headers: { "Content-Type": "application/json" },
        },
    );
}

// Cache timestamp management
async function setCacheTime(request) {
    const cache = await caches.open(`${CACHE_PREFIX}-timestamps`);
    const timestamp = new Response(Date.now().toString());
    return cache.put(request.url + ":timestamp", timestamp);
}

async function getCacheTime(request) {
    try {
        const cache = await caches.open(`${CACHE_PREFIX}-timestamps`);
        const response = await cache.match(request.url + ":timestamp");
        if (response) {
            const timestamp = await response.text();
            return parseInt(timestamp);
        }
    } catch (error) {
        console.log("Error getting cache time:", error);
    }
    return null;
}

// Clean up old cache entries
async function cleanupCache(cacheName, maxEntries) {
    try {
        const cache = await caches.open(cacheName);
        const requests = await cache.keys();

        if (requests.length > maxEntries) {
            const entriesToDelete = requests.slice(
                0,
                requests.length - maxEntries,
            );
            await Promise.all(
                entriesToDelete.map((request) => cache.delete(request)),
            );
            console.log(
                `Cleaned up ${entriesToDelete.length} entries from ${cacheName}`,
            );
        }
    } catch (error) {
        console.error("Cache cleanup failed:", error);
    }
}

// Background sync for failed requests
self.addEventListener("sync", (event) => {
    if (event.tag === "background-sync") {
        event.waitUntil(processBackgroundSync());
    }
});

async function processBackgroundSync() {
    // Handle any queued requests when connection is restored
    console.log("Processing background sync...");

    // Clean up old caches
    await cleanupCache(DYNAMIC_CACHE, CACHE_CONFIG.maxEntries.dynamic);
    await cleanupCache(API_CACHE, CACHE_CONFIG.maxEntries.api);
    await cleanupCache(STATIC_CACHE, CACHE_CONFIG.maxEntries.static);
}

// Handle push notifications (if implemented)
self.addEventListener("push", (event) => {
    if (!event.data) return;

    const data = event.data.json();
    const options = {
        body: data.body || "New notification",
        icon: "/static/icons/favicon.png",
        badge: "/static/icons/favicon.png",
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: data.primaryKey || 1,
        },
        actions: [
            {
                action: "explore",
                title: "View",
                icon: "/static/icons/favicon.png",
            },
            {
                action: "close",
                title: "Close",
                icon: "/static/icons/favicon.png",
            },
        ],
    };

    event.waitUntil(
        self.registration.showNotification(
            data.title || "GST Intelligence",
            options,
        ),
    );
});

// Handle notification clicks
self.addEventListener("notificationclick", (event) => {
    event.notification.close();

    if (event.action === "explore") {
        event.waitUntil(clients.openWindow("/dashboard"));
    }
});

// Message handling for communication with main thread
self.addEventListener("message", (event) => {
    if (event.data && event.data.type === "SKIP_WAITING") {
        self.skipWaiting();
    }

    if (event.data && event.data.type === "CACHE_UPDATE") {
        event.waitUntil(
            caches.open(STATIC_CACHE).then((cache) => {
                return cache.addAll(event.data.urls || []);
            }),
        );
    }
});

// Periodic background sync for cache maintenance
self.addEventListener("periodicsync", (event) => {
    if (event.tag === "cache-cleanup") {
        event.waitUntil(processBackgroundSync());
    }
});

// Create offline HTML page
function createOfflineHTML() {
    return `
    <!DOCTYPE html>
    <html lang="en" data-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Offline - GST Intelligence Platform</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #f8fafc;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2rem;
            }
            .container {
                text-align: center;
                max-width: 500px;
                background: rgba(30, 41, 59, 0.8);
                padding: 3rem 2rem;
                border-radius: 16px;
                border: 1px solid #334155;
                backdrop-filter: blur(10px);
            }
            .icon {
                font-size: 4rem;
                margin-bottom: 1.5rem;
                opacity: 0.7;
            }
            h1 {
                font-size: 2rem;
                margin-bottom: 1rem;
                color: #7c3aed;
            }
            p {
                font-size: 1.1rem;
                line-height: 1.6;
                margin-bottom: 2rem;
                color: #cbd5e1;
            }
            .btn {
                background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
                color: white;
                border: none;
                padding: 0.75rem 2rem;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
                text-decoration: none;
                display: inline-block;
            }
            .btn:hover {
                transform: translateY(-2px);
            }
            .status {
                margin-top: 2rem;
                padding: 1rem;
                background: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 8px;
                color: #fca5a5;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">📡</div>
            <h1>You're Offline</h1>
            <p>
                It looks like you've lost your internet connection. 
                Don't worry - some features may still work from cache.
            </p>
            <button class="btn" onclick="window.location.reload()">
                Try Again
            </button>
            <div class="status">
                <strong>Connection Status:</strong> <span id="status">Offline</span>
            </div>
        </div>

        <script>
            // Check connection status
            function updateStatus() {
                const status = document.getElementById('status');
                if (navigator.onLine) {
                    status.textContent = 'Online';
                    status.style.color = '#10b981';
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    status.textContent = 'Offline';
                    status.style.color = '#ef4444';
                }
            }

            window.addEventListener('online', updateStatus);
            window.addEventListener('offline', updateStatus);
            updateStatus();
        </script>
    </body>
    </html>
    `;
}

console.log("🚀 GST Intelligence Platform Service Worker loaded successfully");
