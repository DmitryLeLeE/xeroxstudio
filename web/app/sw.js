// Автогенерация (tools/gen_sw.py). Офлайн-кэш: после первого запуска приложение открывается без сети.
const CACHE = "zine-studio-06fd01dc49";
const CORE = ['./', 'data/face.json', 'fonts/LICENSE-MarckScript.txt', 'fonts/LICENSE-PermanentMarker.txt', 'fonts/LICENSE-PressStart2P.txt', 'fonts/LICENSE-RubikFiltered.txt', 'fonts/LICENSE-RubikMonoOne.txt', 'fonts/LICENSE-SpecialElite.txt', 'fonts/MarckScript-Regular.ttf', 'fonts/OFL-JetBrainsMono.txt', 'fonts/OFL-Oswald.txt', 'fonts/OFL-PTSerif.txt', 'fonts/OFL-Rubik.txt', 'fonts/PermanentMarker-Regular.ttf', 'fonts/PressStart2P-Regular.ttf', 'fonts/RubikDirt-Regular.woff2', 'fonts/RubikDistressed-Regular.woff2', 'fonts/RubikGlitch-Regular.woff2', 'fonts/RubikMonoOne-Regular.ttf', 'fonts/RubikSprayPaint-Regular.woff2', 'fonts/RubikWetPaint-Regular.woff2', 'fonts/SpecialElite-Regular.ttf', 'fonts/fonts.css', 'fonts/jetbrains-mono-cyrillic-700-normal.woff2', 'fonts/jetbrains-mono-latin-700-normal.woff2', 'fonts/oswald-cyrillic-700-normal.woff2', 'fonts/oswald-latin-700-normal.woff2', 'fonts/pt-serif-cyrillic-700-normal.woff2', 'fonts/pt-serif-latin-700-normal.woff2', 'fonts/rubik-cyrillic-700-normal.woff2', 'fonts/rubik-cyrillic-900-normal.woff2', 'fonts/rubik-latin-700-normal.woff2', 'fonts/rubik-latin-900-normal.woff2', 'icons/apple-180.png', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/maskable-512.png', 'index.html', 'js/app.js', 'js/config.js', 'js/engine.js', 'js/faces.js', 'js/io.js', 'js/render-client.js', 'js/render-worker.js', 'js/theme-init.js', 'js/util.js', 'licenses.txt', 'manifest.webmanifest', 'style.css', '../img/sample.jpg', '../img/favicon.png', '../img/xerox.png', '../index.html', '../style.css', '../landing.js'];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE && k.startsWith("zine-studio-")).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(async (c) => {
    const hit = await c.match(req, { ignoreSearch: true });
    if (hit) return hit;
    try {
      const res = await fetch(req);
      if (res.ok) c.put(req, res.clone());
      return res;
    } catch (err) {
      if (req.mode === "navigate") return (await c.match("./")) || Response.error();
      throw err;
    }
  }));
});
