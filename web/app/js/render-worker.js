// Рендер страницы в отдельном потоке: интерфейс не замирает на больших размерах.
// Протокол: init → ready; src (картинка) ; render → done | fail.
import { renderPage } from "./engine.js";
import { initFaces } from "./faces.js";

const sources = new Map(); // id → {canvas: OffscreenCanvas}
let fontsDone = null;
let faceUrl = "data/face.json";

// Шрифты в воркере не берутся из CSS: читаем fonts.css и создаём FontFace сами.
function loadFonts(cssUrl) {
  return fetch(cssUrl).then((r) => r.text()).then(async (css) => {
    const base = new URL(".", cssUrl).href;
    const blocks = css.match(/@font-face\s*{[^}]*}/g) || [];
    await Promise.all(blocks.map(async (b) => {
      const fam = /font-family:\s*'([^']+)'/.exec(b), url = /url\(([^)]+)\)/.exec(b);
      if (!fam || !url) return;
      const w = /font-weight:\s*(\d+)/.exec(b), ur = /unicode-range:\s*([^;]+);/.exec(b);
      const desc = { display: "swap" };
      if (w) desc.weight = w[1];
      if (ur) desc.unicodeRange = ur[1].trim();
      try {
        const face = new FontFace(fam[1], `url(${new URL(url[1].trim(), base).href})`, desc);
        await face.load();
        self.fonts.add(face);
      } catch (e) { /* без этого шрифта будет запасной */ }
    }));
  });
}

self.onmessage = async (ev) => {
  const m = ev.data;
  try {
    if (m.type === "init") {
      if (typeof OffscreenCanvas === "undefined" || !self.fonts || typeof FontFace === "undefined") {
        self.postMessage({ type: "ready", ok: false }); return;
      }
      const probe = new OffscreenCanvas(2, 2).getContext("2d", { willReadFrequently: true });
      if (!probe) { self.postMessage({ type: "ready", ok: false }); return; }
      faceUrl = m.faceUrl || faceUrl;
      fontsDone = loadFonts(m.fontsCss).catch(() => null);
      await fontsDone;
      self.postMessage({ type: "ready", ok: true });
    } else if (m.type === "src") {
      const bmp = m.bitmap, c = new OffscreenCanvas(bmp.width, bmp.height);
      c.getContext("2d", { willReadFrequently: true }).drawImage(bmp, 0, 0);
      bmp.close();
      sources.set(m.id, { canvas: c });
    } else if (m.type === "drop") {
      sources.delete(m.id);
    } else if (m.type === "render") {
      await fontsDone;
      if (m.state && m.state.censor) await initFaces(faceUrl);
      const src = m.src != null ? sources.get(m.src) || null : null;
      if (m.src != null && !src) throw new Error("source missing");
      const r = await renderPage(src, m.state, m.opts || {});
      const bitmap = r.canvas.transferToImageBitmap ? r.canvas.transferToImageBitmap() : await createImageBitmap(r.canvas);
      const out = { type: "done", id: m.id, bitmap, bits: r.bits, plate2: r.plate2 || null, extraPlates: r.extraPlates || null, inks: r.inks, width: r.width, height: r.height };
      const tr = [bitmap], seen = new Set();
      const take = (a) => { if (a && a.buffer && a.byteOffset === 0 && a.byteLength === a.buffer.byteLength && !seen.has(a.buffer)) { seen.add(a.buffer); tr.push(a.buffer); } };
      take(r.bits); take(r.plate2);
      for (const k in r.extraPlates || {}) take(r.extraPlates[k].bits);
      self.postMessage(out, tr);
    }
  } catch (e) {
    self.postMessage({ type: "fail", id: m.id, message: String((e && e.message) || e) });
  }
};
