const SHELL_CACHE = 'bam-shell-v1';
const RUNTIME_CACHE = 'bam-runtime-v1';
const SHELL_ASSETS = ["/", "/index.html", "/styles.css?v=4b67781a", "/script.js?v=40fd28f4", "/manifest.json", "/offline.html", "/icons/icon-192.png", "/icons/icon-512.png", "/icons/apple-touch-icon.png"];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then(function(cache) { return cache.addAll(SHELL_ASSETS); })
      .then(function() { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(
        names
          .filter(function(name) { return name !== SHELL_CACHE && name !== RUNTIME_CACHE; })
          .map(function(name) { return caches.delete(name); })
      );
    }).then(function() { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(event) {
  var request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) {
    return;
  }
  event.respondWith(
    fetch(request).then(function(response) {
      if (response && response.ok) {
        var copy = response.clone();
        caches.open(RUNTIME_CACHE).then(function(cache) { cache.put(request, copy); });
      }
      return response;
    }).catch(function() {
      return caches.match(request).then(function(cached) {
        if (cached) return cached;
        if (request.mode === 'navigate') return caches.match('/offline.html');
        return undefined;
      });
    })
  );
});
