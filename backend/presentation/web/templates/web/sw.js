/* Apple Emoji Service Worker
 *
 * Strategiya: cache-first for emoji CDN (cdn.jsdelivr.net/emoji-datasource-apple)
 *
 * Ish faoliyati:
 *   1. Foydalanuvchi sayt ochganda — SW registratsiyadan o'tadi (bir marta)
 *   2. Twemoji emoji'larni <img src=".../1f525.png"> bilan almashtiradi
 *   3. Har img request'ini SW ushlab oladi
 *   4. Agar cache'da bor — darhol beradi (0 network, 0 latency)
 *   5. Agar yo'q — download qiladi + cache'ga saqlaydi (bir marta)
 *
 * Emojilar hech qachon o'zgarmaydi (immutable CDN URL), shuning uchun
 * forever-cache xavfsiz. TTL yo'q.
 */
const CACHE_VERSION = 'apple-emoji-v1';
const EMOJI_HOSTS = ['cdn.jsdelivr.net'];
const EMOJI_PATH = 'emoji-datasource-apple';

self.addEventListener('install', (event) => {
  // Yangi SW darhol activate bo'ladi
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  // Eski cache versiyalarni tozalash
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k.startsWith('apple-emoji-') && k !== CACHE_VERSION)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  let url;
  try { url = new URL(req.url); } catch { return; }

  // Faqat Apple emoji CDN requestlarni ushlaymiz
  if (!EMOJI_HOSTS.includes(url.hostname)) return;
  if (!url.pathname.includes(EMOJI_PATH)) return;

  event.respondWith(
    caches.open(CACHE_VERSION).then((cache) =>
      cache.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((resp) => {
          // Faqat muvaffaqiyatli javoblarni cache'laymiz
          if (resp.ok) {
            cache.put(req, resp.clone()).catch(() => {});
          }
          return resp;
        }).catch(() => cached || Response.error());
      })
    )
  );
});
