// static/js/service-worker.js

const CACHE_NAME = 'my-site-cache-v1';
const STATIC_CACHE_NAME = 'static-cache-v1';
const DYNAMIC_CACHE_NAME = 'dynamic-cache-v1';
const API_CACHE_NAME = 'api-cache-v1';

// Static assets that should always be cached
const staticAssets = [
  '/static/styles.css',
  '/static/dashboard.css',
  '/static/dark-mode.css',
  '/static/auth.js',
  '/static/pwa.js',
  '/static/dark-mode.js',
  '/static/prefetch.js',
  '/static/script.js',
  '/static/settings.css',
  '/static/assets/der-volt-logo.png',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap'
];

// Pages that require authentication but should be cached
const authPages = [
  '/dashboard',
  '/help',
  '/settings',
  '/notifications',
  '/transactions'
];

// API endpoints that should be cached with specific strategies
const apiEndpoints = [
  '/api/accounts/',
  '/api/transaction-data',
  '/api/transactions-debug'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('[Service Worker] Installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Caching static assets');
        return cache.addAll(staticAssets);
      })
  );
  // Activate the service worker immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[Service Worker] Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(cacheName => {
          return (cacheName !== STATIC_CACHE_NAME && 
                 cacheName !== DYNAMIC_CACHE_NAME &&
                 cacheName !== API_CACHE_NAME);
        }).map(cacheName => {
          console.log('[Service Worker] Deleting old cache:', cacheName);
          return caches.delete(cacheName);
        })
      );
    })
  );
  // Ensure the service worker takes control of all clients
  return self.clients.claim();
});

// Helper function to check if URL is in the authPages list
function isAuthPage(url) {
  const pathname = new URL(url).pathname;
  return authPages.some(page => pathname === page);
}

// Helper function to check if URL is a static asset
function isStaticAsset(url) {
  return staticAssets.some(asset => url.endsWith(asset));
}

// Helper function to check if URL is an API endpoint
function isApiEndpoint(url) {
  return apiEndpoints.some(endpoint => url.includes(endpoint));
}

// Helper function to check if URL is auth check endpoint
function isAuthCheckEndpoint(url) {
  return url.includes('/api/check-auth');
}

// Fetch event - serve cached content when offline
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip auth check API requests from service worker caching
  // Let these go directly to network
  if (isAuthCheckEndpoint(request.url)) {
    return;
  }
  
  // Different caching strategies based on the request type
  
  // 1. For static assets: Cache first, then network
  if (isStaticAsset(request.url)) {
    event.respondWith(
      caches.match(request)
        .then(cachedResponse => {
          if (cachedResponse) {
            // Return the cached response
            return cachedResponse;
          }
          
          // If not in cache, fetch from network
          return fetch(request)
            .then(networkResponse => {
              // Cache the response for future
              const responseToCache = networkResponse.clone();
              caches.open(STATIC_CACHE_NAME)
                .then(cache => {
                  cache.put(request, responseToCache);
                });
              return networkResponse;
            });
        })
    );
    return;
  }
  
  // 2. For authenticated pages: Network first, then cache
  if (isAuthPage(request.url)) {
    event.respondWith(
      fetch(request)
        .then(networkResponse => {
          // Clone the response
          const responseToCache = networkResponse.clone();
          
          // Cache the fresh response
          caches.open(DYNAMIC_CACHE_NAME)
            .then(cache => {
              cache.put(request, responseToCache);
            });
            
          return networkResponse;
        })
        .catch(() => {
          // If network fails, try to serve from cache
          return caches.match(request)
            .then(cachedResponse => {
              if (cachedResponse) {
                return cachedResponse;
              }
              
              // If not in cache and network failed, return a custom offline page
              // or fallback to the cached homepage
              return caches.match('/');
            });
        })
    );
    return;
  }
  
  // 3. For API endpoints: Network with cache fallback, with 5-minute expiry
  if (isApiEndpoint(request.url)) {
    event.respondWith(
      fetch(request)
        .then(networkResponse => {
          // Clone the response for caching
          const responseToCache = networkResponse.clone();
          
          // Cache the new API response with expiration
          caches.open(API_CACHE_NAME)
            .then(cache => {
              // Add expiration information to the response
              const headers = new Headers(responseToCache.headers);
              const expirationDate = new Date();
              expirationDate.setMinutes(expirationDate.getMinutes() + 5); // 5-minute expiry
              headers.append('sw-cache-expires', expirationDate.getTime());
              
              // Create new response with expiration
              const responseWithExpiry = new Response(responseToCache.body, {
                status: responseToCache.status,
                statusText: responseToCache.statusText,
                headers: headers
              });
              
              cache.put(request, responseWithExpiry);
            });
            
          return networkResponse;
        })
        .catch(() => {
          // If network request fails, try to use cached response
          return caches.match(request)
            .then(cachedResponse => {
              if (cachedResponse) {
                // Check if the cached response has expired
                const expiryHeader = cachedResponse.headers.get('sw-cache-expires');
                if (expiryHeader) {
                  const expiryTime = parseInt(expiryHeader, 10);
                  const now = new Date().getTime();
                  
                  if (now < expiryTime) {
                    // Return the cached response if it hasn't expired
                    return cachedResponse;
                  }
                } else {
                  // No expiry header, return the cached response
                  return cachedResponse;
                }
              }
              
              // If no valid cached response, return an error response
              return new Response(JSON.stringify({
                error: 'Network error',
                offline: true
              }), {
                status: 503,
                headers: {'Content-Type': 'application/json'}
              });
            });
        })
    );
    return;
  }
  
  // 4. Default strategy for other requests: stale-while-revalidate
  event.respondWith(
    caches.match(request)
      .then(cachedResponse => {
        // Return cached response immediately if available
        const fetchPromise = fetch(request)
          .then(networkResponse => {
            // Update the cache with the new response
            caches.open(DYNAMIC_CACHE_NAME)
              .then(cache => {
                cache.put(request, networkResponse.clone());
              });
            return networkResponse;
          })
          .catch(error => {
            console.error('Fetch failed:', error);
            // If both cache and network fail, we still need to return something
            return new Response('Network error occurred', {
              status: 408,
              headers: { 'Content-Type': 'text/plain' }
            });
          });
          
        return cachedResponse || fetchPromise;
      })
  );
});


// push notifs

self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : {};

    self.registration.showNotification(data.title || "Notification", {
        body: data.body || "You have a new message!",
        icon: "/static/assets/logo.png",
        badge: "/static/assets/logo.png",
        data: {url: data.url || "/"}
    });
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});