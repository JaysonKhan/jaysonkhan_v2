/* Self-unregistering Service Worker
 *
 * Emoji-cache feature was removed. This is a cleanup SW: existing
 * installations will fetch this updated file, activate it, clear all
 * caches, and unregister. Fresh visits don't register any SW at all.
 */
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
      await self.registration.unregister();
    } catch (e) { /* ignore */ }
  })());
});
