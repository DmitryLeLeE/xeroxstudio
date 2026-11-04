"""Генерирует app/sw.js: список файлов для офлайн-кэша берётся из каталога сайта."""
import os, hashlib, sys
args = [a for a in sys.argv[1:] if not a.startswith('--')]
root = args[0] if args else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web')
files = []
for base, _, names in os.walk(os.path.join(root, 'app')):
    for n in names:
        p = os.path.join(base, n)
        rel = os.path.relpath(p, os.path.join(root, 'app')).replace(os.sep, '/')
        if rel in ('sw.js',) or rel.startswith('test_') or n.startswith('_'): continue
        files.append(rel)
files = sorted(files)
extra = ['../img/sample.jpg', '../img/favicon.png', '../img/xerox.png', '../index.html', '../style.css', '../landing.js'] 
extra = [e for e in extra if os.path.exists(os.path.normpath(os.path.join(root, 'app', e)))]
h = hashlib.sha1()
for f in files + extra:
    h.update(f.encode()); h.update(open(os.path.normpath(os.path.join(root, 'app', f)), 'rb').read())
ver = h.hexdigest()[:10]
core = ['./'] + files + extra
src = f'''// Автогенерация (tools/gen_sw.py). Офлайн-кэш: после первого запуска приложение открывается без сети.
const CACHE = "zine-studio-{ver}";
const CORE = {core!r};

self.addEventListener("install", (e) => {{
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
}});
self.addEventListener("activate", (e) => {{
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE && k.startsWith("zine-studio-")).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
}});
self.addEventListener("fetch", (e) => {{
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(async (c) => {{
    const hit = await c.match(req, {{ ignoreSearch: true }});
    if (hit) return hit;
    try {{
      const res = await fetch(req);
      if (res.ok) c.put(req, res.clone());
      return res;
    }} catch (err) {{
      if (req.mode === "navigate") return (await c.match("./")) || Response.error();
      throw err;
    }}
  }}));
}});
'''
target = os.path.join(root, 'app', 'sw.js')
if '--check' in sys.argv:
    if not os.path.exists(target) or open(target, encoding='utf-8', newline='').read() != src:
        sys.exit('web/app/sw.js is stale: run python tools/gen_sw.py')
    print('sw.js is up to date')
    sys.exit(0)
open(target, 'w', encoding='utf-8', newline='\n').write(src)
print('sw.js', ver, len(core), 'files')
