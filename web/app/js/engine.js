// Движок рендера страницы: порт engine.py на JavaScript (canvas + типизированные массивы).
// Расчёт полностью локальный, без сервера. Случайные части (края, пыль, шум) используют свой
// генератор, поэтому от десктопной версии отличаются деталями, а геометрия и растр совпадают.

import { CFG } from "./config.js";

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

// ---------------------------------------------------------------- случайные числа
function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

class Rng {
  constructor(seed) {
    this.f = mulberry32((seed ^ 0x9e3779b9) >>> 0);
  }
  random() { return this.f(); }
  uniform(a, b) { return a + (b - a) * this.f(); }
  int(a, b) { return a + Math.floor(this.f() * (b - a)); }
  normal() {
    let u = 0;
    while (u === 0) u = this.f();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * this.f());
  }
}

// ---------------------------------------------------------------- канвасы
export function makeCanvas(w, h) {
  const cw = Math.max(1, Math.round(w)), ch = Math.max(1, Math.round(h));
  if (typeof document === "undefined") return new OffscreenCanvas(cw, ch); // внутри воркера
  const c = document.createElement("canvas");
  c.width = cw;
  c.height = ch;
  return c;
}
const ctx2d = (c) => c.getContext("2d", { willReadFrequently: true });

export function mergeState(state) {
  const st = { ...CFG.DEFAULT_STATE, ...state };
  st.layout = CFG.LAYOUT_ALIASES[st.layout] || st.layout;
  return st;
}

// ---------------------------------------------------------------- растр
/** Амплитудный растр. gray: Uint8Array w*h. Возвращает Uint8Array: 1 = бумага, 0 = краска. */
export function halftoneBits(gray, w, h, dotSize, angleDeg) {
  const out = new Uint8Array(w * h);
  const rad = (angleDeg * Math.PI) / 180;
  const c = Math.cos(rad), s = Math.sin(rad);
  const ds = Math.max(2, dotSize);
  const maxR = ds * 0.7071;
  let i = 0;
  for (let y = 0; y < h; y++) {
    const ys = y * s, yc = y * c;
    for (let x = 0; x < w; x++, i++) {
      const xr = x * c - ys, yr = x * s + yc;
      const dx = xr - Math.round(xr / ds) * ds;
      const dy = yr - Math.round(yr / ds) * ds;
      const thr = (1 - gray[i] / 255) * maxR;
      out[i] = Math.sqrt(dx * dx + dy * dy) >= thr ? 1 : 0;
    }
  }
  return out;
}


const BAYER8 = [[0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],[12,44,4,36,14,46,6,38],[60,28,52,20,62,30,54,22],[3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],[15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]];
function hash01(cx, cy) {
  let h = (Math.imul(cx | 0, 374761393) + Math.imul(cy | 0, 668265263)) >>> 0;
  h = Math.imul((h ^ (h >>> 13)) >>> 0, 1274126177) >>> 0;
  h = (h ^ (h >>> 16)) >>> 0;
  return (h & 0xffff) / 65536;
}
/** Линейные и шумовые растры (те же формулы, что в engine.py): 1 = бумага, 0 = краска. */
export function patternBits(gray, w, h, dotSize, angleDeg, kind) {
  const out = new Uint8Array(w * h), ds = Math.max(2, dotSize);
  const rad = (angleDeg * Math.PI) / 180, c = Math.cos(rad), sn = Math.sin(rad);
  const cell = kind === "bayer" ? Math.max(1, Math.round(ds / 3)) : kind === "stipple" ? Math.max(1, Math.round(ds / 2)) : Math.max(1, Math.round(ds / 5));
  let i = 0;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++, i++) {
      const dark = 1 - gray[i] / 255;
      let ink;
      if (kind === "lines" || kind === "cross") {
        const yr = x * sn + y * c;
        ink = Math.abs(yr - Math.round(yr / ds) * ds) < dark * ds * 0.5;
        if (!ink && kind === "cross") {
          const xr = x * c - y * sn;
          ink = Math.abs(xr - Math.round(xr / ds) * ds) < Math.max(0, dark - 0.5) * ds;
        }
      } else if (kind === "bayer") {
        ink = dark > (BAYER8[Math.floor(y / cell) % 8][Math.floor(x / cell) % 8] + 0.5) / 64;
      } else {
        ink = dark > hash01(Math.floor(x / cell), Math.floor(y / cell));
      }
      out[i] = ink ? 0 : 1;
    }
  }
  return out;
}


const smooth = (e0, e1, x) => { const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t); };

/** Пятно от кофе (кольцо с неровным ободком и брызгами) или жира (мягкое, прозрачное). Умножением, как в engine.py. */
function applyStain(c, w, h, rng, cx, cy, r, grease, power) {
  const half = Math.floor(r * (grease ? 1.35 : 2.0)) + 3;
  const x0 = Math.max(0, Math.floor(cx) - half), y0 = Math.max(0, Math.floor(cy) - half);
  const x1 = Math.min(w, Math.floor(cx) + half), y1 = Math.min(h, Math.floor(cy) + half);
  if (x1 <= x0 || y1 <= y0) return;
  const ks = [2, 3, 4, 5, 7, 9];
  const amp = ks.map((k) => rng.uniform(0.02, 0.07) * (grease ? 1.7 : 1) / Math.sqrt(k));
  const ph = ks.map(() => rng.uniform(0, 6.2832));
  const ringPh = rng.uniform(0, 6.2832);
  const mp = [rng.uniform(0, 6.2832), rng.uniform(0, 6.2832), rng.uniform(0, 6.2832), rng.uniform(0, 6.2832)];
  const mf = [rng.uniform(3, 7), rng.uniform(3, 7)];
  const drops = [];
  if (!grease) for (let n = rng.int(2, 5); n > 0; n--) {
    const ang = rng.uniform(0, 6.2832), dd = r * rng.uniform(1.15, 1.7);
    drops.push([cx + dd * Math.cos(ang), cy + dd * Math.sin(ang), r * rng.uniform(0.05, 0.13)]);
  }
  const col = grease ? [124, 100, 46] : [98, 58, 24];
  const img = c.getImageData(x0, y0, x1 - x0, y1 - y0), d = img.data, bw = x1 - x0;
  for (let y = y0; y < y1; y++) {
    for (let x = x0; x < x1; x++) {
      const dx = x - cx, dy = y - cy, dist = Math.hypot(dx, dy), th = Math.atan2(dy, dx);
      let rr = 1;
      for (let k = 0; k < ks.length; k++) rr += amp[k] * Math.cos(ks[k] * th + ph[k]);
      const t = dist / (r * rr);
      const mottle = 0.5 + 0.5 * Math.sin(dx / r * mf[0] + mp[0]) * Math.sin(dy / r * mf[1] + mp[1]);
      let a;
      if (grease) {
        a = 0.36 * (1 - smooth(0.45, 1.0, t)) * (0.8 + 0.4 * mottle) + 0.07 * Math.exp(-(((t - 0.88) / 0.12) ** 2));
      } else {
        const inside = Math.min(1, Math.max(0, (1.03 - t) / 0.06));
        const ring = Math.exp(-(((t - 0.95) / 0.045) ** 2)) * (0.4 + 0.6 * (0.5 + 0.5 * Math.cos(th - ringPh)));
        a = inside * (0.11 + 0.05 * mottle) + ring * 0.62 + 0.05 * Math.exp(-(((t - 1.1) / 0.1) ** 2));
        for (const [px, py, rd] of drops) {
          const td = Math.hypot(x - px, y - py) / rd;
          if (td < 1.6) a += Math.min(1, Math.max(0, (1.05 - td) / 0.1)) * 0.2 + Math.exp(-(((td - 0.92) / 0.12) ** 2)) * 0.45;
        }
      }
      a = Math.min(0.88, Math.max(0, a * power));
      if (a <= 0.002) continue;
      const i = ((y - y0) * bw + (x - x0)) * 4;
      for (let k = 0; k < 3; k++) d[i + k] = d[i + k] * (1 - a + a * col[k] / 255);
    }
  }
  c.putImageData(img, x0, y0);
}


/** Механика копира: эхо барабана, полосы тонера, заедание бумаги (аналог add_mechanism в engine.py). */
function addMechanism(canvas, st, seed, s) {
  const ghost = Number(st.ghost) || 0, bands = Number(st.bands) || 0, smear = Number(st.smear) || 0;
  const gutter = Number(st.gutter) || 0, recopy = Number(st.recopy) || 0;
  if (!(ghost > 0 || bands > 0 || smear > 0 || gutter > 0 || recopy > 0)) return;
  const w = canvas.width, h = canvas.height, c = ctx2d(canvas);
  if (smear > 0) { // бумага заела: одна строка тянется вниз полосой
    const y0 = Math.floor((0.15 + 0.65 * hash01(seed, 97)) * h), hb = Math.max(3, Math.floor((0.02 + 0.07 * smear / 100) * h));
    const row = makeCanvas(w, 1); ctx2d(row).drawImage(canvas, 0, y0, w, 1, 0, 0, w, 1);
    c.drawImage(row, 0, 0, w, 1, 0, y0, w, Math.min(hb, h - y0));
  }
  if (ghost > 0) { // изображение повторяется через длину окружности барабана, бледнее
    const tmp = makeCanvas(w, h); ctx2d(tmp).drawImage(canvas, 0, 0);
    const dy = Math.floor(h * 0.31), dx = Math.floor(4 * s);
    c.save(); c.globalCompositeOperation = "multiply"; c.globalAlpha = 0.38 * ghost / 100;
    c.drawImage(tmp, dx, dy); c.drawImage(tmp, dx, dy - h);
    c.restore();
  }
  if (bands > 0) { // периодические тёмные полосы поперёк листа
    const P = h / (5 + 3 * hash01(seed, 98)), phase = hash01(seed, 99) * Math.PI * 2;
    for (let y = 0; y < h; y++) {
      const a = (bands / 100) * 0.2 * (0.5 + 0.5 * Math.sin((2 * Math.PI * y) / P + phase));
      if (a > 0.004) { c.fillStyle = `rgba(0,0,0,${a.toFixed(4)})`; c.fillRect(0, y, w, 1); }
    }
  }
  if (gutter > 0) { // тёмный корешок по центру, как при копировании разворота книги
    const sig = w * (0.02 + 0.05 * gutter / 100);
    for (let x = 0; x < w; x++) {
      const a = 0.9 * gutter / 100 * Math.exp(-(((x - w * 0.5) / sig) ** 2));
      if (a > 0.004) { c.fillStyle = `rgba(0,0,0,${a.toFixed(4)})`; c.fillRect(x, 0, 1, h); }
    }
  }
  if (recopy > 0) { // лист пересняли несколько раз: каждый проход мутнее, контрастнее и теряет тонер
    const passes = 1 + Math.floor(recopy / 35), kc = 1.10 + 0.14 * recopy / 100, id = c.getImageData(0, 0, w, h), d = id.data;
    let a = new Float32Array(w * h * 3), b = new Float32Array(w * h * 3);
    for (let i = 0, p = 0; i < w * h; i++, p += 4) { a[i * 3] = d[p]; a[i * 3 + 1] = d[p + 1]; a[i * 3 + 2] = d[p + 2]; }
    for (let n = 0; n < passes; n++) {
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let ch = 0; ch < 3; ch++) {
        const o = (y * w + x) * 3 + ch, l = (y * w + Math.max(0, x - 1)) * 3 + ch, r = (y * w + Math.min(w - 1, x + 1)) * 3 + ch;
        b[o] = (a[l] + 2 * a[o] + a[r]) / 4;
      }
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let ch = 0; ch < 3; ch++) {
        const o = (y * w + x) * 3 + ch, u = (Math.max(0, y - 1) * w + x) * 3 + ch, dn = (Math.min(h - 1, y + 1) * w + x) * 3 + ch;
        let v = (b[u] + 2 * b[o] + b[dn]) / 4;
        v = Math.min(255, Math.max(0, (v - 128) * kc + 128));
        a[o] = 255 - (255 - v) * 0.97;
      }
    }
    for (let i = 0, p = 0; i < w * h; i++, p += 4) { d[p] = Math.round(a[i * 3]); d[p + 1] = Math.round(a[i * 3 + 1]); d[p + 2] = Math.round(a[i * 3 + 2]); }
    c.putImageData(id, 0, 0);
  }
}

/** Износ листа поверх готового кадра: пятна, пыль и волоски, сгиб, дырки, штамп (аналог add_wear в engine.py). */
function addWear(canvas, st, seed, s) {
  const stains = Number(st.stains), dust = Number(st.dust), fold = Number(st.fold), holes = Number(st.holes), stamp = String(st.stamp || "").replace(/\n/g, " ").trim();
  if (!(stains > 0 || dust > 0 || fold > 0 || holes || stamp)) return;
  const w = canvas.width, h = canvas.height, m = Math.min(w, h), c = ctx2d(canvas), rng = new Rng(seed);
  if (stains > 0) {
    for (let i = 0; i < 1 + Math.floor(stains / 25); i++) {
      const cx = rng.uniform(0.1, 0.9) * w, cy = rng.uniform(0.1, 0.9) * h, r = rng.uniform(0.04, 0.1) * m * (0.6 + stains / 100);
      applyStain(c, w, h, rng, cx, cy, r, i % 2 === 1, 0.55 + stains / 220);
    }
  }
  if (dust > 0) {
    c.fillStyle = "rgba(20,20,20,.78)";
    const n = Math.floor((dust * w * h) / 60000);
    for (let i = 0; i < n; i++) { const r = rng.uniform(0.6, 2.2) * s; c.beginPath(); c.arc(rng.uniform(0, w), rng.uniform(0, h), r, 0, Math.PI * 2); c.fill(); }
    c.strokeStyle = "rgba(30,30,30,.66)"; c.lineWidth = Math.max(1, s);
    for (let i = 0; i < Math.floor(dust / 20); i++) {
      let x = rng.uniform(0, w), y = rng.uniform(0, h); c.beginPath(); c.moveTo(x, y);
      for (let k = 0; k < 5; k++) { x += rng.normal() * 14 * s; y += rng.normal() * 14 * s; c.lineTo(x, y); }
      c.stroke();
    }
  }
  if (fold > 0) {
    const band = (horizontal, k) => {
      const n = horizontal ? h : w, pos = n / 2, sig = Math.max(2, n * 0.025);
      const g = horizontal ? c.createLinearGradient(0, pos - sig * 2.5, 0, pos + sig * 2.5) : c.createLinearGradient(pos - sig * 2.5, 0, pos + sig * 2.5, 0);
      for (let i = 0; i <= 10; i++) { const t = i / 10, d = (t - 0.5) * 5; g.addColorStop(t, `rgba(0,0,0,${(Math.exp(-d * d) * (fold / 100) * 70 * k) / 255})`); }
      c.fillStyle = g;
      if (horizontal) c.fillRect(0, pos - sig * 2.5, w, sig * 5); else c.fillRect(pos - sig * 2.5, 0, sig * 5, h);
    };
    band(true, 1); if (fold >= 50) band(false, 0.6);
    c.fillStyle = `rgba(255,255,255,${(40 + fold * 1.2) / 255})`; c.fillRect(0, h / 2 + Math.max(2, 2 * s), w, Math.max(1, s));
  }
  if (holes) {
    const r = 0.014 * w;
    for (const fy of [0.2, 0.5, 0.8]) {
      c.fillStyle = "rgba(0,0,0,.16)"; c.beginPath(); c.arc(0.05 * w, fy * h, r + 2 * s, 0, Math.PI * 2); c.fill();
      c.fillStyle = "#1a1a1a"; c.beginPath(); c.arc(0.05 * w, fy * h, r, 0, Math.PI * 2); c.fill();
    }
  }
  if (stamp) {
    const size = Math.max(14, Math.round(0.06 * w)), text = stamp.toUpperCase(), pad = 0.02 * w;
    c.save();
    c.font = fontSpec(st.font, size);
    const tw = c.measureText(text).width, sw = tw + 2 * pad, sh = size * 1.2 + 2 * pad;
    const tmp = makeCanvas(Math.ceil(sw) + 4, Math.ceil(sh) + 4), t = ctx2d(tmp);
    t.font = c.font; t.textBaseline = "middle"; t.fillStyle = t.strokeStyle = "rgb(190,30,30)";
    t.lineWidth = Math.max(3, 4 * s); t.strokeRect(2, 2, sw, sh); t.fillText(text, 2 + pad, 2 + sh / 2);
    t.globalCompositeOperation = "destination-out"; t.fillStyle = "#000";
    const sr = new Rng(seed + 1);
    for (let i = 0; i < sw * sh * 0.2 / 6; i++) t.fillRect(sr.uniform(0, sw), sr.uniform(0, sh), 2, 2);
    c.globalAlpha = 0.85;
    c.translate(0.66 * w, 0.8 * h); c.rotate((Number(st.stamp_rot) * Math.PI) / -180);
    c.drawImage(tmp, -tmp.width / 2, -tmp.height / 2);
    c.restore();
  }
}


const rgbCss = (c) => `rgb(${Math.round(c[0])},${Math.round(c[1])},${Math.round(c[2])})`;
/** Рисует один стикер в квадрат size x size с центром в (0,0). Режимы: f/s - цвет слоя, p/k - цвет бумаги. */
export function drawSticker(c, name, size, color, paper) {
  const spec = CFG.STICKERS[name]; if (!spec) return;
  const k = size / 100; c.save(); c.translate(-size / 2, -size / 2); c.scale(k, k);
  c.lineJoin = "round"; c.lineCap = "round";
  for (const pr of spec.prims) {
    const m = pr.m || "f", col = m === "f" || m === "s" ? color : paper;
    c.fillStyle = c.strokeStyle = col; c.lineWidth = 6;
    if (pr.t === "poly") {
      c.beginPath(); pr.p.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath();
      if (m === "f" || m === "p") c.fill(); else c.stroke();
    } else if (pr.t === "circle") {
      c.beginPath(); c.arc(pr.c[0], pr.c[1], pr.r, 0, Math.PI * 2);
      if (m === "f" || m === "p") c.fill(); else c.stroke();
    } else if (pr.t === "line") {
      c.strokeStyle = color; c.lineWidth = pr.w || 6; c.beginPath(); pr.p.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.stroke();
    } else if (pr.t === "text") {
      c.fillStyle = paper; c.font = `900 ${pr.h}px "Arial Black", Rubik, sans-serif`; c.textAlign = "center"; c.textBaseline = "middle"; c.fillText(pr.s, pr.c[0], pr.c[1]);
    }
  }
  c.restore();
}
/** Свободные слои поверх листа (аналог draw_layers в engine.py). */
// «Записка из газетных букв»: каждая буква на своём клочке, свой шрифт, размер и наклон (раскладка детерминирована: тот же результат в engine.py).
const RANSOM_FONTS = ["Arial Black", "Times New Roman Bold", "Courier New Bold", "Impact", "Rubik Mono One", "Rubik Distressed", "Marck Script"];
function drawRansom(c, text, fpx, color, paper, accent) {
  const lines = text.split("\n"), rows = []; let n = 0, maxW = 0;
  for (const l of lines) {
    const row = []; let wsum = 0;
    for (const ch of [...l]) {
      const i = n++;
      if (ch === " ") { row.push({ sp: true, w: fpx * 0.45 }); wsum += fpx * 0.45; continue; }
      const f = RANSOM_FONTS[Math.floor(hash01(i, 11) * RANSOM_FONTS.length)], sz = Math.round(fpx * (0.78 + 0.5 * hash01(i, 12)));
      const rot = (hash01(i, 13) - 0.5) * 0.28, mode = hash01(i, 14), dy = (hash01(i, 15) - 0.5) * 0.22 * fpx;
      c.font = fontSpec(f, sz);
      const pad = sz * 0.16, w = c.measureText(ch).width + 2 * pad, h = sz * 1.05 + 2 * pad;
      row.push({ ch, f, sz, rot, mode, dy, w, h }); wsum += w - fpx * 0.02;
    }
    rows.push(row); maxW = Math.max(maxW, wsum);
  }
  const lh = fpx * 1.55, top = (-lh * lines.length) / 2;
  rows.forEach((row, ri) => {
    const rw = row.reduce((a, it) => a + it.w - (it.sp ? 0 : fpx * 0.02), 0);
    let x = -rw / 2;
    for (const it of row) {
      if (it.sp) { x += it.w; continue; }
      c.save(); c.translate(x + it.w / 2, top + ri * lh + lh / 2 + it.dy); c.rotate(it.rot);
      const inv = it.mode >= 0.45 && it.mode < 0.75, acc = it.mode >= 0.75 && it.mode < 0.9;
      c.fillStyle = inv ? color : acc ? accent : paper; c.fillRect(-it.w / 2, -it.h / 2, it.w, it.h);
      if (!inv && !acc) { c.strokeStyle = "rgba(0,0,0,.35)"; c.lineWidth = Math.max(1, fpx * 0.03); c.strokeRect(-it.w / 2, -it.h / 2, it.w, it.h); }
      c.fillStyle = inv || acc ? paper : color; c.font = fontSpec(it.f, it.sz); c.textAlign = "center"; c.textBaseline = "middle";
      c.fillText(it.ch, 0, it.sz * 0.05); c.restore();
      x += it.w - fpx * 0.02;
    }
  });
}

// Износ стикера: пропуски тонера, пятна, царапины. Те же формулы, что _wear_sticker в engine.py.
function wearSticker(off, px, seed) {
  const c = ctx2d(off), W = off.width, H = off.height, u = Math.max(1.2, px / 150), k = seed * 100;
  c.globalCompositeOperation = "destination-out";
  const dot = (x, y, r, a) => { c.fillStyle = `rgba(0,0,0,${a})`; c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill(); };
  const n = Math.min(1600, Math.floor((px * px) / 40));
  for (let i = 0; i < n; i++) dot(hash01(i, k + 21) * W, hash01(i, k + 22) * H, (0.4 + hash01(i, k + 23) ** 2 * 1.6) * u, 0.55 + 0.45 * hash01(i, k + 24));
  for (let j = 0; j < 9; j++) {
    const cx = hash01(j, k + 31) * W, cy = hash01(j, k + 32) * H;
    for (let i = 0; i < 18; i++) {
      const a = hash01(i + 100 * j, k + 33) * 6.2832, rr = hash01(i + 100 * j, k + 34) * px * 0.1, r = (0.8 + hash01(i + 100 * j, k + 35) * 2.2) * u;
      dot(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr, r, 0.8);
    }
  }
  for (let j = 0; j < 10; j++) dot(hash01(j, k + 51) * W, hash01(j, k + 52) * H, px * (0.03 + hash01(j, k + 53) * 0.06), 70 / 255);
  c.strokeStyle = "rgba(0,0,0,0.9)"; c.lineWidth = Math.max(1, Math.round(px / 220)); c.lineCap = "butt";
  for (let j = 0; j < 5; j++) {
    const x = hash01(j, k + 41) * W, y = hash01(j, k + 42) * H, a = hash01(j, k + 43) * 6.2832, ln = px * (0.2 + hash01(j, k + 44) * 0.4);
    c.beginPath(); c.moveTo(x, y); c.lineTo(x + Math.cos(a) * ln, y + Math.sin(a) * ln); c.stroke();
  }
  c.globalCompositeOperation = "source-over";
}

// Фото-объект: растр из фото, вырезанный как маска краски (alpha = краска). Подложка из бумаги с рваным краем, как приклеенная ксерокопия.
function bitmapLayer(m, wpx, ly, color, paper, li) {
  const hpx = Math.max(4, Math.round((wpx * m.height) / m.width)), off = makeCanvas(wpx, hpx), oc = ctx2d(off);
  const backed = ly.backing !== false;
  if (backed) { oc.fillStyle = paper; oc.fillRect(0, 0, wpx, hpx); }
  const tint = makeCanvas(wpx, hpx), tc = ctx2d(tint);
  tc.drawImage(m, 0, 0, wpx, hpx); tc.globalCompositeOperation = "source-in"; tc.fillStyle = color; tc.fillRect(0, 0, wpx, hpx);
  oc.drawImage(tint, 0, 0);
  if (backed && ly.torn !== false) {
    const al = tornAlpha(wpx, hpx, 7, 7, 700 + li), id = oc.getImageData(0, 0, wpx, hpx), d = id.data;
    for (let i = 0, p = 3; i < al.length; i++, p += 4) d[p] = (d[p] * al[i]) / 255;
    oc.putImageData(id, 0, 0);
  }
  wearSticker(off, wpx, li + 1);
  return off;
}

/** Растягивает тона так, чтобы 2% самых тёмных стали чёрными, 2% самых светлых белыми: слишком светлое или тёмное фото не пропадает. */
function autoLevels(d, n) {
  const hist = new Uint32Array(256);
  for (let p = 0; p < d.length; p += 4) hist[Math.floor((d[p] * 299 + d[p + 1] * 587 + d[p + 2] * 114) / 1000)]++;
  let acc = 0, lo = 0, hi = 255;
  for (let i = 0; i < 256; i++) { acc += hist[i]; if (acc >= 0.02 * n) { lo = i; break; } }
  acc = 0; for (let i = 0; i < 256; i++) { acc += hist[i]; if (acc >= 0.98 * n) { hi = i; break; } }
  if (hi - lo < 16) return;
  const k = 255 / (hi - lo);
  for (let p = 0; p < d.length; p += 4) for (let c = 0; c < 3; c++) d[p + c] = Math.max(0, Math.min(255, (d[p + c] - lo) * k));
}
function brightGamma(d, b) {
  const lut = new Uint8Array(256); for (let i = 0; i < 256; i++) lut[i] = Math.round(255 * Math.pow(i / 255, 1 / b));
  for (let p = 0; p < d.length; p += 4) for (let c = 0; c < 3; c++) d[p + c] = lut[d[p + c]];
}

/** Превращает фото в маску краски для фото-объекта: полутон + (по желанию) вырезка фона. alpha 255 = краска. */
export function makePhotoMask(canvas, { maxSide = 720, dot = 5, contrast = 1.6, cutout = false, bright = 1, cov = 0 } = {}) {
  const k = Math.min(1, maxSide / Math.max(canvas.width, canvas.height)), w = Math.max(8, Math.round(canvas.width * k)), h = Math.max(8, Math.round(canvas.height * k));
  let src = makeCanvas(w, h); ctx2d(src).drawImage(canvas, 0, 0, w, h);
  let keep = null;
  if (cutout) {
    const cut = stickerCutout(src), cd = ctx2d(cut).getImageData(0, 0, w, h).data;
    keep = new Uint8Array(w * h); for (let i = 0, p = 3; i < keep.length; i++, p += 4) keep[i] = cd[p] ? 1 : 0;
    // контур вырезки превращаем в серый фон: за краями пусто
  }
  const id = ctx2d(src).getImageData(0, 0, w, h);
  autoLevels(id.data, w * h); if (bright !== 1) brightGamma(id.data, bright);
  contrastRGB(id.data, contrast, cov);
  const gray = grayOf(id.data, w * h), bits = halftoneBits(gray, w, h, dot, 45);
  const out = new ImageData(w, h), o = out.data;
  for (let i = 0, p = 0; i < bits.length; i++, p += 4) { o[p + 3] = bits[i] === 0 && (!keep || keep[i]) ? 255 : 0; }
  const res = makeCanvas(w, h); ctx2d(res).putImageData(out, 0, 0);
  return res;
}


/** Искажение надписи по столбцам: арка, прогиб, волна, раздувание, наклон (аналог _warp_image в engine.py). */
function warpCanvas(src, kind, k, bh) {
  const W = src.width, H = src.height, out = makeCanvas(W, H), oc = ctx2d(out);
  for (let x = 0; x < W; x++) {
    const t = ((x + 0.5) / W) * 2 - 1;
    if (kind === "bulge") {
      const sy = 1 + k * 0.8 * (1 - t * t);
      oc.drawImage(src, x, 0, 1, H, x, (H - H * sy) / 2, 1, H * sy);
      continue;
    }
    let dy = 0;
    if (kind === "arch") dy = -k * bh * 1.1 * (1 - t * t) + k * bh * 0.55;
    else if (kind === "dip") dy = k * bh * 1.1 * (1 - t * t) - k * bh * 0.55;
    else if (kind === "wave") dy = k * bh * 0.55 * Math.sin(t * Math.PI * 2);
    else if (kind === "slant") dy = k * bh * 0.7 * t;
    oc.drawImage(src, x, 0, 1, H, x, Math.round(dy), 1, H);
  }
  return out;
}

/** Фигура-слой: rect / ellipse / triangle; заливка solid, outline, stripes, fade (растровое затухание), dots. Рисуется вокруг (0, 0). */
function drawShape(c, ly, W, color) {
  const H = Math.max(4, Math.round(W * (Number(ly.aspect) || 0.6))), kind = ly.shape || "rect", fill = ly.fill || "solid";
  c.save(); c.translate(-W / 2, -H / 2); c.fillStyle = color; c.strokeStyle = color;
  const path = () => {
    c.beginPath();
    if (kind === "ellipse") c.ellipse(W / 2, H / 2, W / 2, H / 2, 0, 0, Math.PI * 2);
    else if (kind === "triangle") { c.moveTo(W / 2, 0); c.lineTo(W, H); c.lineTo(0, H); c.closePath(); }
    else c.rect(0, 0, W, H);
  };
  path();
  if (fill === "solid") c.fill();
  else if (fill === "outline") { c.save(); c.clip(); c.lineWidth = 2 * Math.max(2, W * 0.02); path(); c.stroke(); c.restore(); }
  else {
    c.save(); c.clip();
    if (fill === "stripes") {
      const sp = W * 0.06; c.lineWidth = Math.max(1, sp / 2);
      c.beginPath(); for (let t = -H; t < W + H; t += sp) { c.moveTo(t, H); c.lineTo(t + H, 0); } c.stroke();
    } else {
      const step = Math.max(5, W * 0.022);
      c.beginPath();
      for (let j = 0, y = 0; y <= H; j++, y += step) {
        const r = step * (fill === "fade" ? 0.72 * (1 - y / H) : 0.36);
        if (r < 0.8) continue;
        for (let x = (j % 2) * step / 2; x <= W; x += step) { c.moveTo(x + r, y); c.arc(x, y, r, 0, Math.PI * 2); }
      }
      c.fill();
    }
    c.restore();
  }
  c.restore();
}

function drawLayers(canvas, st, paper, ink, masks = {}) {
  const layers = st.layers; if (!Array.isArray(layers) || !layers.length) return;
  const w = canvas.width, c = ctx2d(canvas), h = canvas.height;
  const cols = { ink: rgbCss(ink), paper: rgbCss(paper), ink2: rgbCss(st.ink2 || [255, 60, 140]), ink3: rgbCss(st.ink3 || [0, 120, 190]), ink4: rgbCss(st.ink4 || [255, 200, 0]) };
  let li = -1;
  for (const ly of layers) {
    li++;
    if (ly.hidden) continue;
    const color = cols[ly.color] || cols.ink, size = Math.max(0.02, Number(ly.size) || 0.2);
    c.save(); c.translate((Number(ly.x) || 0.5) * w, (Number(ly.y) || 0.5) * h); c.rotate(((Number(ly.rot) || 0) * Math.PI) / 180);
    if (ly.flipx) c.scale(-1, 1);
    c.globalAlpha = clamp(ly.opacity == null ? 1 : Number(ly.opacity), 0, 1);
    if (ly.blend === "multiply" || ly.blend === "screen" || ly.blend === "difference") c.globalCompositeOperation = ly.blend;
    const shd = clamp(Number(ly.shadow) || 0, 0, 1);
    if (shd > 0) { c.shadowColor = cols[ly.shadow_c] || cols.ink; c.shadowOffsetX = c.shadowOffsetY = Math.round(shd * 0.035 * w); c.shadowBlur = 0; }
    if (ly.type === "sticker") {
      const px = Math.max(8, Math.floor(size * w)), off = makeCanvas(px, px), oc = ctx2d(off);
      oc.translate(px / 2, px / 2); drawSticker(oc, ly.sticker, px, color, cols.paper); wearSticker(off, px, li + 1);
      c.drawImage(off, -px / 2, -px / 2);
    } else if (ly.type === "shape") {
      drawShape(c, ly, Math.max(8, Math.floor(size * w)), color);
    } else if (ly.type === "bitmap") {
      const m = masks[ly.img]; if (!m) { c.restore(); continue; }
      const px = Math.max(8, Math.floor(size * w)), off = bitmapLayer(m, px, ly, color, cols.paper, li);
      c.drawImage(off, -off.width / 2, -off.height / 2);
    }
    else {
      const text = String(ly.text || "").trim(); if (!text) { c.restore(); continue; }
      const fpx = Math.max(8, Math.round(size * w * 0.5));
      const sx = clamp(Number(ly.sx) || 1, 0.4, 3), warp = ly.warp && ly.warp !== "none" ? ly.warp : null, wk = clamp(ly.warp_k == null ? 0.5 : Number(ly.warp_k), 0, 1);
      if (sx !== 1) c.scale(sx, 1);
      if (ly.style === "ransom") { drawRansom(c, text, fpx, color, cols.paper, cols.ink2); c.restore(); continue; }
      const lines = text.split("\n"), pad = fpx * 0.3, lh = fpx * 1.15;
      c.font = fontSpec(ly.font || "Arial Black", fpx); c.textBaseline = "top"; c.textAlign = "left";
      const tw = Math.max(...lines.map((l) => c.measureText(l).width)), th = lh * lines.length, bw = tw + 2 * pad, bh = th + 2 * pad;
      const style = ly.style || "box";
      const paint = (cc) => {
        cc.font = fontSpec(ly.font || "Arial Black", fpx); cc.textBaseline = "top"; cc.textAlign = "left";
        if (style === "box") { cc.fillStyle = cols.paper; cc.fillRect(-bw / 2, -bh / 2, bw, bh); cc.fillStyle = color; }
        else if (style === "tape") { cc.fillStyle = color; cc.fillRect(-bw / 2, -bh / 2, bw, bh); cc.fillStyle = cols.paper; }
        else { cc.fillStyle = color; cc.strokeStyle = cols.paper; cc.lineWidth = Math.max(2, fpx * 0.16); cc.lineJoin = "round"; }
        lines.forEach((l, i) => { const y = -bh / 2 + pad + i * lh; if (style === "plain") cc.strokeText(l, -bw / 2 + pad, y); cc.fillText(l, -bw / 2 + pad, y); });
      };
      if (!warp) paint(c);
      else {
        const m = Math.ceil(bh * (0.15 + wk * 0.9)), W = Math.ceil(bw) + 4, Hh = Math.ceil(bh) + 2 * m, off = makeCanvas(W, Hh), oc = ctx2d(off);
        oc.translate(W / 2, Hh / 2); paint(oc);
        c.drawImage(warpCanvas(off, warp, wk, bh), -W / 2, -Hh / 2);
      }
    }
    c.restore();
  }
}

function stencilBits(gray, w, h) {
  const out = new Uint8Array(w * h);
  for (let i = 0; i < out.length; i++) out[i] = gray[i] >= 128 ? 1 : 0;
  return out;
}

function floydBits(gray, w, h) {
  const buf = Float32Array.from(gray);
  const out = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      const old = buf[i];
      const nv = old >= 128 ? 255 : 0;
      out[i] = nv ? 1 : 0;
      const err = old - nv;
      if (x + 1 < w) buf[i + 1] += (err * 7) / 16;
      if (y + 1 < h) {
        if (x > 0) buf[i + w - 1] += (err * 3) / 16;
        buf[i + w] += (err * 5) / 16;
        if (x + 1 < w) buf[i + w + 1] += err / 16;
      }
    }
  }
  return out;
}

// ---------------------------------------------------------------- пиксельные операции
function grayOf(data, n) {
  const g = new Uint8Array(n);
  for (let i = 0, p = 0; i < n; i++, p += 4) g[i] = (data[p] * 299 + data[p + 1] * 587 + data[p + 2] * 114) / 1000;
  return g;
}

/** Как PIL ImageEnhance.Contrast: опорная точка - среднее серого. */
function contrastRGB(data, factor, cov = 0) {
  let sum = 0;
  const n = data.length / 4;
  for (let p = 0; p < data.length; p += 4) sum += (data[p] * 299 + data[p + 1] * 587 + data[p + 2] * 114) / 1000;
  let mean = Math.floor(sum / n + 0.5);
  // cov: доля листа, занятая этим фото; контраст на листе считается от среднего всего листа, где много светлой бумаги
  if (cov > 0) mean = Math.round((1 - cov) * 235 + cov * mean);
  for (let p = 0; p < data.length; p += 4) {
    data[p] = mean + (data[p] - mean) * factor;
    data[p + 1] = mean + (data[p + 1] - mean) * factor;
    data[p + 2] = mean + (data[p + 2] - mean) * factor;
  }
}

function boxesForGauss(sigma, n) {
  const wIdeal = Math.sqrt((12 * sigma * sigma) / n + 1);
  let wl = Math.floor(wIdeal);
  if (wl % 2 === 0) wl--;
  const wu = wl + 2;
  const m = Math.round((12 * sigma * sigma - n * wl * wl - 4 * n * wl - 3 * n) / (-4 * wl - 4));
  return Array.from({ length: n }, (_, i) => (i < m ? wl : wu));
}

function boxBlurPass(src, dst, w, h, r, horizontal) {
  const len = horizontal ? w : h, lines = horizontal ? h : w;
  const stride = horizontal ? 4 : 4 * w, lineStride = horizontal ? 4 * w : 4;
  const inv = 1 / (r + r + 1);
  for (let l = 0; l < lines; l++) {
    const base = l * lineStride;
    for (let ch = 0; ch < 3; ch++) {
      const first = src[base + ch];
      let acc = (r + 1) * first;
      for (let k = 1; k <= r; k++) acc += src[base + Math.min(k, len - 1) * stride + ch];
      for (let j = 0; j < len; j++) {
        dst[base + j * stride + ch] = acc * inv;
        acc += src[base + Math.min(j + 1 + r, len - 1) * stride + ch] - (j - r >= 0 ? src[base + (j - r) * stride + ch] : first);
      }
    }
  }
}

/** Приближение гауссова размытия тремя проходами box blur (канал альфа не трогается). */
function gaussBlur(imgData, sigma) {
  if (sigma < 0.3) return;
  const { data, width: w, height: h } = imgData;
  const tmp = new Uint8ClampedArray(data.length);
  tmp.set(data);
  for (const box of boxesForGauss(sigma, 3)) {
    const r = (box - 1) >> 1;
    if (r < 1) continue;
    boxBlurPass(data, tmp, w, h, r, true);
    boxBlurPass(tmp, data, w, h, r, false);
  }
}

// ---------------------------------------------------------------- маска рваного края
function tornAlpha(w, h, roughX, roughY, seed) {
  if (roughX <= 0 && roughY <= 0) return null;
  const fx = Math.max(0.005, (roughX / 100) * 0.4), fy = Math.max(0.005, (roughY / 100) * 0.45);
  const rng = new Rng(seed);
  const gw = Math.max(3, Math.floor(w / 24)), gh = Math.max(3, Math.floor(h / 24));
  const grid = new Float32Array(gw * gh);
  for (let i = 0; i < grid.length; i++) grid[i] = rng.uniform(-0.35, 0.35);

  const rampX = new Float32Array(w), gx0 = new Int32Array(w), gxt = new Float32Array(w);
  for (let x = 0; x < w; x++) {
    const t = w > 1 ? x / (w - 1) : 0;
    rampX[x] = clamp(Math.min(t, 1 - t) / fx, 0, 1);
    const g = t * (gw - 1);
    gx0[x] = Math.min(gw - 2, Math.floor(g));
    gxt[x] = g - gx0[x];
  }
  const alpha = new Uint8ClampedArray(w * h);
  for (let y = 0; y < h; y++) {
    const t = h > 1 ? y / (h - 1) : 0;
    const rampY = clamp(Math.min(t, 1 - t) / fy, 0, 1);
    const g = t * (gh - 1), y0 = Math.min(gh - 2, Math.floor(g)), ty = g - y0;
    const row0 = y0 * gw, row1 = (y0 + 1) * gw;
    for (let x = 0; x < w; x++) {
      const ramp = Math.min(rampX[x], rampY);
      const a = grid[row0 + gx0[x]], b = grid[row0 + gx0[x] + 1], c = grid[row1 + gx0[x]], d = grid[row1 + gx0[x] + 1];
      const tx = gxt[x];
      const n = (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty;
      let v = clamp(ramp + n * (1 - ramp * 0.7), 0, 1);
      v = v * v * (3 - 2 * v);
      alpha[y * w + x] = v * 255;
    }
  }
  return alpha;
}

// ---------------------------------------------------------------- вырезка-стикер
function otsu(gray) {
  const hist = new Float64Array(256);
  for (let i = 0; i < gray.length; i++) hist[gray[i]]++;
  const total = gray.length;
  let sum = 0;
  for (let t = 0; t < 256; t++) sum += t * hist[t];
  let sumB = 0, wB = 0, best = 0, thr = 0;
  for (let t = 0; t < 256; t++) {
    wB += hist[t];
    if (!wB) continue;
    const wF = total - wB;
    if (!wF) break;
    sumB += t * hist[t];
    const mB = sumB / wB, mF = (sum - sumB) / wF;
    const between = wB * wF * (mB - mF) * (mB - mF);
    if (between > best) { best = between; thr = t; }
  }
  return thr;
}

/** Расстояние (приближённо евклидово, чамфер 1/√2) до ближайшего пикселя со значением 1. */
function distanceTo(mask, w, h) {
  const INF = 1e9, B = 1.4142;
  const d = new Float32Array(w * h);
  for (let i = 0; i < d.length; i++) d[i] = mask[i] ? 0 : INF;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      let v = d[i];
      if (x > 0) v = Math.min(v, d[i - 1] + 1);
      if (y > 0) {
        v = Math.min(v, d[i - w] + 1);
        if (x > 0) v = Math.min(v, d[i - w - 1] + B);
        if (x + 1 < w) v = Math.min(v, d[i - w + 1] + B);
      }
      d[i] = v;
    }
  }
  for (let y = h - 1; y >= 0; y--) {
    for (let x = w - 1; x >= 0; x--) {
      const i = y * w + x;
      let v = d[i];
      if (x + 1 < w) v = Math.min(v, d[i + 1] + 1);
      if (y + 1 < h) {
        v = Math.min(v, d[i + w] + 1);
        if (x + 1 < w) v = Math.min(v, d[i + w + 1] + B);
        if (x > 0) v = Math.min(v, d[i + w - 1] + B);
      }
      d[i] = v;
    }
  }
  return d;
}

function stickerCutout(canvas) {
  const w = canvas.width, h = canvas.height;
  const src = ctx2d(canvas).getImageData(0, 0, w, h);
  const gray = grayOf(src.data, w * h);
  const t = otsu(gray);
  let mask = new Uint8Array(w * h);
  for (let i = 0; i < mask.length; i++) mask[i] = gray[i] <= t ? 1 : 0;
  const k = Math.max(1, Math.floor(Math.max(w, h) / 500));

  const dist1 = distanceTo(mask, w, h);                // закрытие: расширить на 2k, затем сузить на 2k
  const grown = new Uint8Array(w * h);
  for (let i = 0; i < grown.length; i++) grown[i] = dist1[i] <= 2 * k ? 1 : 0;
  const inv = new Uint8Array(w * h);
  for (let i = 0; i < inv.length; i++) inv[i] = grown[i] ? 0 : 1;
  const dist2 = distanceTo(inv, w, h);
  for (let i = 0; i < mask.length; i++) mask[i] = dist2[i] > 2 * k ? 1 : 0;

  const dist3 = distanceTo(mask, w, h);
  const out = new ImageData(w, h);
  const o = out.data;
  for (let i = 0, p = 0; i < mask.length; i++, p += 4) {
    if (mask[i]) { o[p] = src.data[p]; o[p + 1] = src.data[p + 1]; o[p + 2] = src.data[p + 2]; o[p + 3] = 255; }
    else if (dist3[i] <= 4 * k) { o[p] = o[p + 1] = o[p + 2] = 255; o[p + 3] = 255; }
    else if (dist3[i] <= 5 * k) { o[p] = o[p + 1] = o[p + 2] = 0; o[p + 3] = 255; }
  }
  const res = makeCanvas(w, h);
  ctx2d(res).putImageData(out, 0, 0);
  return res;
}

// ---------------------------------------------------------------- макеты
export function layoutBoxes(layout, cw, ch, rows, ext) {
  rows = Math.max(1, Math.floor(rows));
  const boxes = [];
  if (layout === "column") {
    const colW = Math.floor(cw * 0.46), rowH = Math.floor(ch / rows);
    for (let r = 0; r < rows; r++) boxes.push([Math.floor(cw * 0.05), r * rowH, colW, rowH + ext]);
  } else if (layout === "contact_sheet") {
    const cols = 3, margin = Math.floor(cw * 0.04), gap = Math.max(2, Math.floor(cw * 0.012));
    const tw = Math.floor((cw - 2 * margin - (cols - 1) * gap) / cols);
    const th = Math.floor((ch - 2 * margin - (rows - 1) * gap) / rows);
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) boxes.push([margin + c * (tw + gap), margin + r * (th + gap), tw, th]);
  } else if (layout === "center_hero") {
    boxes.push([Math.floor(cw * 0.1), Math.floor(ch * 0.12), Math.floor(cw * 0.8), Math.floor(ch * 0.54)]);
    const n = Math.min(5, Math.max(3, rows)), gap = Math.max(2, Math.floor(cw * 0.012));
    const tw = Math.floor((Math.floor(cw * 0.8) - (n - 1) * gap) / n);
    for (let i = 0; i < n; i++) boxes.push([Math.floor(cw * 0.1) + i * (tw + gap), Math.floor(ch * 0.78), tw, Math.floor(ch * 0.14)]);
  } else if (layout === "column_right") {
    const colW = Math.floor(cw * 0.46), rowH = Math.floor(ch / rows);
    for (let r = 0; r < rows; r++) boxes.push([Math.floor(cw * 0.49), r * rowH, colW, rowH + ext]);
  } else if (layout === "diagonal") {
    const n = Math.min(rows, 8), bw = Math.floor(cw * 0.5), bh = Math.min(ch, Math.floor((ch / n) * 1.45));
    for (let r = 0; r < n; r++) boxes.push([Math.floor(cw * 0.04 + cw * 0.42 * (n > 1 ? r / (n - 1) : 0.5)), n > 1 ? Math.floor((r * (ch - bh)) / (n - 1)) : 0, bw, bh]);
  } else if (layout === "pile") {
    const n = Math.min(Math.max(2, rows), 6), bw = Math.floor(cw * 0.62), bh = Math.floor(ch * 0.4);
    for (let i = 0; i < n; i++) boxes.push([Math.floor((cw - bw) * (((i * 618) % 1000) / 1000)), Math.floor((ch - bh) * (i / (n - 1))), bw, bh]);
  } else if (layout === "two_columns") {
    const margin = Math.floor(cw * 0.05), gap = Math.max(2, Math.floor(cw * 0.02)), tw = Math.floor((cw - 2 * margin - gap) / 2), rowH = Math.floor(ch / rows);
    for (let r = 0; r < rows; r++) for (let c = 0; c < 2; c++) boxes.push([margin + c * (tw + gap), r * rowH + (c ? Math.floor(rowH / 2) : 0), tw, rowH - gap]);
  } else if (layout === "mosaic") {
    const n = Math.min(Math.max(2, rows), 6), gap = Math.max(2, Math.floor(cw * 0.012)), fullW = Math.floor(cw * 0.88);
    boxes.push([Math.floor(cw * 0.06), Math.floor(ch * 0.05), fullW, Math.floor(ch * 0.46)]);
    const tw = Math.floor((fullW - 2 * gap) / 3), lines = Math.floor((n + 2) / 3), th = Math.floor((Math.floor(ch * 0.4) - (lines - 1) * gap) / lines);
    for (let i = 0; i < n; i++) boxes.push([Math.floor(cw * 0.06) + (i % 3) * (tw + gap), Math.floor(ch * 0.55) + Math.floor(i / 3) * (th + gap), tw, th]);
  } else if (layout === "duo") {
    boxes.push([Math.floor(cw * 0.08), Math.floor(ch * 0.05), Math.floor(cw * 0.84), Math.floor(ch * 0.43)]);
    boxes.push([Math.floor(cw * 0.08), Math.floor(ch * 0.52), Math.floor(cw * 0.84), Math.floor(ch * 0.43)]);
  } else if (layout === "triptych") {
    const margin = Math.floor(cw * 0.04), gap = Math.max(2, Math.floor(cw * 0.015)), tw = Math.floor((cw - 2 * margin - 2 * gap) / 3);
    for (let c = 0; c < 3; c++) boxes.push([margin + c * (tw + gap), Math.floor(ch * 0.06) + (c === 1 ? Math.floor(ch * 0.04) : 0), tw, Math.floor(ch * 0.82)]);
  } else if (layout === "ribbon") {
    const n = Math.min(Math.max(3, rows), 6), margin = Math.floor(cw * 0.04), gap = Math.max(2, Math.floor(cw * 0.012)), tw = Math.floor((cw - 2 * margin - (n - 1) * gap) / n);
    for (let i = 0; i < n; i++) boxes.push([margin + i * (tw + gap), Math.floor(ch * 0.38), tw, Math.floor(ch * 0.24)]);
  } else if (layout === "full_page") {
    boxes.push([0, 0, cw, ch]);
  } else if (layout === "free") {
    return boxes; // кадров нет: лист собирается слоями
  } else {
    const colW = Math.floor(cw * 0.58), rowH = Math.floor(ch / rows);
    for (let r = 0; r < rows; r++) boxes.push([r % 2 === 0 ? Math.floor(cw * 0.05) : Math.floor(cw * 0.37), r * rowH, colW, rowH + ext]);
  }
  return boxes;
}


// ---------------------------------------------------------------- скотч, бумага
function drawTape(ctx, boxes, amount, seed, s) {
  if (amount <= 0) return;
  const rng = new Rng(seed), p = amount / 100;
  const strip = (cx, cy, ang) => {
    const len = rng.uniform(64, 96) * s, wid = rng.uniform(20, 28) * s, a = (ang * Math.PI) / 180;
    const ca = Math.cos(a), sa = Math.sin(a), nz = Math.max(1, 2.5 * s);
    ctx.beginPath();
    [[-1, -1], [-1, -0.33], [-1, 0.33], [-1, 1], [1, 1], [1, 0.33], [1, -0.33], [1, -1]].forEach(([u, v], i) => {
      const jx = Math.abs(u) === 1 && Math.abs(v) !== 1 ? rng.uniform(-nz, nz) : 0;
      const x = (u * len) / 2 + jx, y = (v * wid) / 2;
      const px = cx + x * ca - y * sa, py = cy + x * sa + y * ca;
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    });
    ctx.closePath();
    ctx.fill();
  };
  ctx.save();
  ctx.fillStyle = "rgba(178,178,178,0.92)";
  for (const [bx, by, bw, bh] of boxes) {
    if (bw < 4 || bh < 4) continue;
    if (rng.random() < p) strip(bx + bw / 2 + rng.uniform(-0.1, 0.1) * bw, by + 4 * s, rng.uniform(-9, 9));
    for (const [cx, cy, base] of [[bx + 6 * s, by + 6 * s, -40], [bx + bw - 6 * s, by + bh - 6 * s, -40], [bx + bw - 6 * s, by + 6 * s, 40], [bx + 6 * s, by + bh - 6 * s, 40]]) {
      if (rng.random() < p * 0.35) strip(cx, cy, base + rng.uniform(-8, 8));
    }
  }
  ctx.restore();
}

/** Шум с размером пятна cell пикселей (билинейная интерполяция сетки). */
function noiseField(w, h, cell, rng) {
  const gw = Math.max(2, Math.floor(w / cell)), gh = Math.max(2, Math.floor(h / cell));
  const g = new Float32Array(gw * gh);
  for (let i = 0; i < g.length; i++) g[i] = rng.normal();
  const out = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const fy = (y / Math.max(1, h - 1)) * (gh - 1), y0 = Math.min(gh - 2, Math.floor(fy)), ty = fy - y0;
    for (let x = 0; x < w; x++) {
      const fx = (x / Math.max(1, w - 1)) * (gw - 1), x0 = Math.min(gw - 2, Math.floor(fx)), tx = fx - x0;
      const a = g[y0 * gw + x0], b = g[y0 * gw + x0 + 1], c = g[(y0 + 1) * gw + x0], d = g[(y0 + 1) * gw + x0 + 1];
      out[y * w + x] = (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty;
    }
  }
  return out;
}

function addPaper(o, w, h, amount, seed, s) {
  if (amount <= 0) return;
  const rng = new Rng(seed), k = amount / 100, sc = Math.max(s, 0.5);
  const big = noiseField(w, h, 90 * sc, rng), fibre = noiseField(w, h, 5 * sc, rng);
  for (let y = 0; y < h; y++) {
    const ey = Math.abs(y / h - 0.5) * 2;
    for (let x = 0; x < w; x++) {
      const i = y * w + x, edge = Math.max(Math.abs(x / w - 0.5) * 2, ey);
      const v = 0.05 * rng.normal() + 0.055 * (0.35 * big[i] + 0.65 * fibre[i]) + (0.1 * Math.pow(clamp(edge - 0.6, 0, 1), 2)) / 0.16;
      const f = 1 - k * v, p = i * 4;
      o[p] = clamp(o[p] * f, 0, 255); o[p + 1] = clamp(o[p + 1] * f, 0, 255); o[p + 2] = clamp(o[p + 2] * f, 0, 255);
    }
  }
}

// ---------------------------------------------------------------- движок
let faceDetector = null; // (canvas) => [[x, y, w, h], ...]
export function setFaceDetector(fn) { faceDetector = fn; }
export const hasFaceDetector = () => !!faceDetector;

let placeholderCanvas = null;
function placeholder() {
  if (placeholderCanvas) return placeholderCanvas;
  const w = 600, h = 800, c = makeCanvas(w, h), ctx = ctx2d(c);
  const id = ctx.createImageData(w, h), d = id.data;
  for (let y = 0; y < h; y++) {
    const bg = 235 - 90 * (y / h);
    for (let x = 0; x < w; x++) {
      const r = Math.hypot((x - w * 0.5) / (w * 0.36), (y - h * 0.4) / (h * 0.27));
      const lit = Math.hypot((x - w * 0.4) / (w * 0.36), (y - h * 0.32) / (h * 0.27));
      let v = r < 1 ? 25 + 205 * Math.pow(clamp(1 - lit * 0.75, 0, 1), 1.3) : bg;
      if (y % 6 === 0) v *= 0.82;
      const p = (y * w + x) * 4;
      d[p] = d[p + 1] = d[p + 2] = v;
      d[p + 3] = 255;
    }
  }
  ctx.putImageData(id, 0, 0);
  ctx.font = "400 54px Impact, Oswald, sans-serif";
  const label = "NO SIGNAL", tw = ctx.measureText(label).width;
  ctx.fillStyle = "#000";
  ctx.fillRect((w - tw) / 2 - 16, 690, tw + 32, 72);
  ctx.fillStyle = "#fff";
  ctx.textBaseline = "top";
  ctx.fillText(label, (w - tw) / 2, 700);
  placeholderCanvas = c;
  return c;
}

// Кэш выреза/стикера/лиц: по объекту-источнику и параметрам. Несколько записей, чтобы миниатюры
// других страниц не сбрасывали кэш текущей (поиск лиц дорогой).
const sampleCaches = new WeakMap();
const SAMPLE_CACHE_LIMIT = 6;
function getSample(source, st) {
  if (!source) return placeholder();
  const crop = st.crop.map(Number);
  const key = `${crop.join(",")}|${st.censor}|${st.sticker}`;
  let per = sampleCaches.get(source);
  if (!per) { per = new Map(); sampleCaches.set(source, per); }
  if (per.has(key)) { const hit = per.get(key); per.delete(key); per.set(key, hit); return hit; }

  const iw = source.canvas.width, ih = source.canvas.height;
  let [x1, y1, x2, y2] = crop.map((v) => clamp(v, 0, 1));
  if (x1 > x2) [x1, x2] = [x2, x1];
  if (y1 > y2) [y1, y2] = [y2, y1];
  let ix1 = Math.floor(x1 * iw), ix2 = Math.floor(x2 * iw), iy1 = Math.floor(y1 * ih), iy2 = Math.floor(y2 * ih);
  if (ix2 - ix1 < 8 || iy2 - iy1 < 8) { ix1 = 0; iy1 = 0; ix2 = iw; iy2 = ih; }
  let canvas = makeCanvas(ix2 - ix1, iy2 - iy1);
  ctx2d(canvas).drawImage(source.canvas, ix1, iy1, ix2 - ix1, iy2 - iy1, 0, 0, canvas.width, canvas.height);

  if (st.censor && faceDetector) {
    const c = ctx2d(canvas);
    c.fillStyle = "#000";
    for (const [fx, fy, fw, fh] of faceDetector(canvas)) {
      const pad = fw * 0.06;
      c.fillRect(fx - pad, fy + fh * 0.28, fw + 2 * pad, fh * 0.2);
    }
  }
  if (st.sticker) canvas = stickerCutout(canvas);
  per.set(key, canvas);
  if (per.size > SAMPLE_CACHE_LIMIT) per.delete(per.keys().next().value);
  return canvas;
}

function fitBase(sample, tw, th, fit, brightness) {
  const base = makeCanvas(tw, th), c = ctx2d(base);
  c.fillStyle = "#fff";
  c.fillRect(0, 0, tw, th);
  c.imageSmoothingEnabled = true;
  c.imageSmoothingQuality = "high";
  const sw = sample.width, sh = sample.height;
  if (fit === "cover") {
    const k = Math.max(tw / sw, th / sh), cw = tw / k, chh = th / k;
    c.drawImage(sample, (sw - cw) / 2, (sh - chh) / 2, cw, chh, 0, 0, tw, th);
  } else {
    const k = Math.min(tw / sw, th / sh);
    const nw = Math.max(1, Math.floor(sw * k)), nh = Math.max(1, Math.floor(sh * k));
    c.drawImage(sample, 0, 0, sw, sh, (tw - nw) >> 1, (th - nh) >> 1, nw, nh);
  }
  if (brightness !== 1) {
    const id = c.getImageData(0, 0, tw, th), d = id.data;
    for (let p = 0; p < d.length; p += 4) { d[p] *= brightness; d[p + 1] *= brightness; d[p + 2] *= brightness; }
    c.putImageData(id, 0, 0);
  }
  return base;
}

function fontSpec(name, size) {
  const f = CFG.FONTS[name] || CFG.FONTS["Arial Bold"];
  return `${f.weight} ${size}px ${f.css}`;
}

export async function ensureFonts(state, text) {
  const fonts = typeof document !== "undefined" ? document.fonts : self.fonts;
  if (!fonts || !fonts.load) return;
  const st = mergeState(state);
  const sample = (text || `${st.txt_top} ${st.txt_bottom}`) + " ABCabc012";
  const jobs = [fonts.load(fontSpec(st.font, 40), sample)];
  const layerFonts = new Set();
  for (const ly of Array.isArray(st.layers) ? st.layers : []) if (ly.type !== "sticker") { layerFonts.add(ly.font || "Arial Black"); if (ly.style === "ransom") RANSOM_FONTS.forEach((f) => layerFonts.add(f)); }
  for (const f of layerFonts) jobs.push(fonts.load(fontSpec(f, 40), sample));
  if (st.layout === "contact_sheet") jobs.push(fonts.load(fontSpec("Courier New Bold", 15), "0123456789A"));
  await Promise.all(jobs.map((p) => p.catch(() => null)));
}

/**
 * Рендер страницы.
 * source: {canvas} или null; opts: {scale, outSize:[w,h], customQuote:[top,bottom]}
 * Возвращает {canvas, bits (Uint8Array, 1 = бумага), width, height}.
 */
export async function renderPage(source, state, opts = {}) {
  const st = mergeState(state);
  await ensureFonts(st, opts.customQuote ? opts.customQuote.join(" ") : undefined);

  const [baseW, baseH] = CFG.CANVAS_FORMATS[st.format] || [1000, 1500];
  let cw, ch, s;
  if (opts.outSize) { cw = Math.round(opts.outSize[0]); ch = Math.round(opts.outSize[1]); s = cw / baseW; }
  else { s = opts.scale || 1; cw = Math.max(16, Math.floor(baseW * s)); ch = Math.max(16, Math.floor(baseH * s)); }

  const canvas = makeCanvas(cw, ch), ctx = ctx2d(canvas);
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, cw, ch);

  const seed = Math.floor(st.seed);
  const rng = new Rng(seed);
  const tilt = Number(st.tilt);
  const ext = Math.floor(st.edge_y * 0.4 * s);

  // --- кадры
  const sample = getSample(source, st);
  const boxes = layoutBoxes(st.layout, cw, ch, st.rows, ext);
  const baseCache = new Map();
  const labelFont = fontSpec("Courier New Bold", Math.max(8, Math.round(15 * s)));

  boxes.forEach(([bx, by, bw, bh], idx) => {
    if (bw < 4 || bh < 4) return;
    const key = `${bw}x${bh}`;
    if (!baseCache.has(key)) baseCache.set(key, fitBase(sample, bw, bh, st.fit_mode, Number(st.bright)));
    const baseCtx = ctx2d(baseCache.get(key));
    const img = baseCtx.getImageData(0, 0, bw, bh);

    const k = (st.loss / 100) * idx; // поколение копии: каждое следующее мутнее и контрастнее
    if (k > 0) { gaussBlur(img, 0.35 * k * s); contrastRGB(img.data, 1 + 0.1 * k); }
    const alpha = tornAlpha(bw, bh, st.edge_x, st.edge_y, seed + idx * 11);
    const d = img.data;
    for (let i = 0, p = 3; i < bw * bh; i++, p += 4) d[p] = alpha ? alpha[i] : 255;

    const tile = makeCanvas(bw, bh);
    ctx2d(tile).putImageData(img, 0, 0);
    ctx.save();
    ctx.translate(bx + bw / 2, by + bh / 2);
    if (tilt > 0) ctx.rotate((-rng.uniform(-tilt, tilt) * Math.PI) / 180);
    ctx.drawImage(tile, -bw / 2, -bh / 2);
    ctx.restore();

    if (st.layout === "contact_sheet") { // номер кадра поверх рваного края, как на плёнке
      const label = `${String(idx + 1).padStart(2, "0")}A`;
      ctx.font = labelFont;
      ctx.textBaseline = "top";
      const lw = ctx.measureText(label).width;
      const lx = bx + Math.floor(3 * s), ly = by + Math.floor(3 * s);
      ctx.fillStyle = "#fff";
      ctx.fillRect(lx, ly, lw + 8 * s, 15 * s + 6 * s);
      ctx.fillStyle = "#000";
      ctx.fillText(label, lx + 4 * s, ly + 2 * s);
    }
  });

  drawTape(ctx, boxes, Number(st.tape), seed + 31, s);

  // --- серый холст: полосы сканера и тень края копира
  {
    const id = ctx.getImageData(0, 0, cw, ch), d = id.data, n = cw * ch;
    const gray = grayOf(d, n);
    const k = st.streaks / 100;
    if (k > 0) {
      const srng = new Rng(seed + 7);
      const overlay = new Float32Array(n).fill(255);
      for (let a = 0, cnt = Math.floor(3 + k * 5); a < cnt; a++) {
        const x = srng.int(0, cw), sw = Math.max(1, Math.floor(srng.int(1, 4) * s)), amt = srng.uniform(20, 90) * k;
        for (let y = 0; y < ch; y++) for (let xx = Math.max(0, x - sw); xx < Math.min(cw, x + sw); xx++) overlay[y * cw + xx] -= amt;
      }
      for (let a = 0, cnt = Math.floor(k * 120 * Math.max(1, s * s * 0.5)); a < cnt; a++) {
        const x = srng.int(0, cw), y0 = srng.int(0, ch), len = Math.floor(srng.int(4, 30) * s), amt = srng.uniform(40, 120);
        for (let y = y0; y < Math.min(ch, y0 + len); y++) overlay[y * cw + x] -= amt;
      }
      for (let i = 0; i < n; i++) gray[i] = (gray[i] * clamp(overlay[i], 0, 255)) / 255;
    }
    if (st.copier_edge > 0) {
      const erng = new Rng(seed + 13);
      const band = Math.max(2, (cw * 0.045 * st.copier_edge) / 100);
      const wobble = (len) => {
        const knots = Math.max(4, Math.floor(len / Math.floor(24 * Math.max(s, 0.5))));
        const v = Float32Array.from({ length: knots }, () => erng.uniform(0.55, 1.45));
        return Float32Array.from({ length: len }, (_, i) => {
          const t = (i / Math.max(1, len - 1)) * (knots - 1), i0 = Math.min(knots - 2, Math.floor(t));
          return v[i0] * (1 - (t - i0)) + v[i0 + 1] * (t - i0);
        });
      };
      const wy = wobble(ch), wx = wobble(cw);
      for (let y = 0; y < ch; y++) {
        const wl = band * wy[y];
        for (let x = 0; x < cw; x++) {
          const left = clamp(1 - x / wl, 0, 1);
          const bottom = clamp(1 - (ch - 1 - y) / (band * 0.7 * wx[x]), 0, 1);
          gray[y * cw + x] *= 1 - Math.max(left, bottom);
        }
      }
    }
    for (let i = 0, p = 0; i < n; i++, p += 4) { d[p] = d[p + 1] = d[p + 2] = gray[i]; d[p + 3] = 255; }
    ctx.putImageData(id, 0, 0);
  }

  // --- текст
  const [topTxt, botTxt] = opts.customQuote || [st.txt_top, st.txt_bottom];
  const style = st.tstyle, align = st.text_align, rot = Number(st.text_rot);
  const drawBlock = (text, yPct) => {
    if (!text) return;
    const padX = Math.round(12 * s), padY = Math.round(8 * s), spacing = Math.round(8 * s);
    const stroke = style === "outline" ? Math.max(1, Math.round(3 * s)) : 0;
    const lines = text.split("\n");
    const mctx = ctx2d(makeCanvas(4, 4));
    let size = st.font_size * s, tw, th, ascent, lineH;
    for (;;) {
      mctx.font = fontSpec(st.font, size);
      const maxW = Math.max(...lines.map((l) => mctx.measureText(l).width));
      const m = mctx.measureText("Hg");
      ascent = m.fontBoundingBoxAscent ?? size * 0.92;
      lineH = ascent + (m.fontBoundingBoxDescent ?? size * 0.25);
      tw = Math.ceil(maxW + 2 * stroke) + 2 * padX;
      th = Math.ceil(lines.length * lineH + (lines.length - 1) * spacing + 2 * stroke) + 2 * padY;
      if (tw <= cw * 0.94 || size <= 10 * s) break;
      size *= 0.9; // длинная строка: уменьшаем, чтобы не вылезла за край листа
    }
    let layer = makeCanvas(tw, th);
    const l = ctx2d(layer);
    if (style === "dymo_tape") { l.fillStyle = "#000"; l.fillRect(0, 0, tw, th); }
    else if (style !== "outline") { l.fillStyle = "#fff"; l.fillRect(0, 0, tw, th); }
    l.font = fontSpec(st.font, size);
    l.textBaseline = "alphabetic";
    l.textAlign = align;
    l.lineJoin = "round";
    const tx = align === "left" ? padX + stroke : align === "right" ? tw - padX - stroke : tw / 2;
    lines.forEach((line, i) => {
      const ty = padY + stroke + ascent + i * (lineH + spacing);
      if (style === "outline") { l.lineWidth = stroke * 2; l.strokeStyle = "#fff"; l.strokeText(line, tx, ty); l.fillStyle = "#000"; }
      else l.fillStyle = style === "dymo_tape" ? "#fff" : "#000";
      l.fillText(line, tx, ty);
    });
    if (rot !== 0) {
      const a = (-rot * Math.PI) / 180, cs = Math.abs(Math.cos(a)), sn = Math.abs(Math.sin(a));
      const rw = Math.ceil(tw * cs + th * sn), rh = Math.ceil(tw * sn + th * cs);
      const rc = makeCanvas(rw, rh), r = ctx2d(rc);
      r.translate(rw / 2, rh / 2);
      r.rotate(a);
      r.drawImage(layer, -tw / 2, -th / 2);
      layer = rc;
    }
    const x = clamp(Math.floor((cw * st.txt_x) / 100), 0, Math.max(0, cw - layer.width));
    const y = clamp(Math.floor((ch * yPct) / 100), 0, Math.max(0, ch - layer.height));
    ctx.drawImage(layer, x, y);
  };
  drawBlock(topTxt, st.txt_y1);
  drawBlock(botTxt, st.txt_y2);

  // --- тоновая компрессия и растрирование
  const src = ctx.getImageData(0, 0, cw, ch);
  const n = cw * ch;
  const gray = grayOf(src.data, n);
  {
    let sum = 0;
    for (let i = 0; i < n; i++) sum += gray[i];
    const mean = Math.floor(sum / n + 0.5);
    const f = Number(st.contrast);
    const nrng = new Rng(seed + 1), noise = Number(st.noise);
    for (let i = 0; i < n; i++) {
      let v = mean + (gray[i] - mean) * f;
      v = clamp(v, 0, 255);
      if (noise > 0) v = clamp(v + nrng.normal() * noise, 0, 255);
      gray[i] = v;
    }
  }
  let bits;
  if (st.dither === "halftone") bits = halftoneBits(gray, cw, ch, st.dot_size * s, st.angle);
  else if (["lines", "cross", "stipple", "mezzo", "bayer"].includes(st.dither)) bits = patternBits(gray, cw, ch, st.dot_size * s, st.angle, st.dither);
  else if (st.dither === "stencil") bits = stencilBits(gray, cw, ch);
  else bits = floydBits(gray, cw, ch);

  // --- палитра Риso, приводка (призрак краски)
  let [paper, ink] = st.palette === CFG.CUSTOM_PALETTE ? st.custom_colors : (CFG.RISO_PALETTES[st.palette] || CFG.RISO_PALETTES["Classic B&W (Xerox)"]);
  if (st.invert) [paper, ink] = [ink, paper];
  const out = new ImageData(cw, ch), o = out.data;
  const mis = Math.round(st.misreg * s);
  const dx = mis, dy = Math.max(1, mis >> 1);
  const ghost = paper.map((p, i) => Math.trunc(p + (ink[i] - p) * 0.45));
  for (let y = 0; y < ch; y++) {
    for (let x = 0; x < cw; x++) {
      const i = y * cw + x, p = i * 4;
      let col = paper;
      if (bits[i] === 0) col = ink;
      else if (mis > 0 && x >= dx && y >= dy && bits[(y - dy) * cw + (x - dx)] === 0) col = ghost;
      o[p] = col[0]; o[p + 1] = col[1]; o[p + 2] = col[2]; o[p + 3] = 255;
    }
  }
  // --- второй цвет (оверпринт): другой экран растра, свой сдвиг, смешение умножением
  const over = Number(st.overprint);
  let plate2 = null;
  if (over > 0) {
    const k2 = Math.min(1, over / 100) * 0.9, lighter = new Uint8Array(n);
    for (let i = 0; i < n; i++) lighter[i] = 255 - (255 - gray[i]) * k2;
    const bits2 = halftoneBits(lighter, cw, ch, st.dot_size * s * 1.3, (Number(st.angle) + 30) % 90);
    plate2 = bits2;
    const sx = Math.round((3 + Number(st.misreg)) * s), sy = Math.round((2 + Number(st.misreg) / 2) * s);
    const [r2, g2, b2] = st.ink2;
    for (let y = sy; y < ch; y++) {
      for (let x = 0; x < cw - sx; x++) {
        if (bits2[(y - sy) * cw + x + sx] === 0) {
          const p = (y * cw + x) * 4;
          o[p] = (o[p] * r2) / 255; o[p + 1] = (o[p + 1] * g2) / 255; o[p + 2] = (o[p + 2] * b2) / 255;
        }
      }
    }
  }
  // --- третья и четвёртая краска: свои тона, углы и сдвиги (те же формулы, что в engine.py)
  const extraPlates = {};
  {
    const m = Number(st.misreg);
    const defs = [
      ["ink3", Number(st.overprint3), 1.15, 60, [Math.round((2 + m) * s), Math.round((1 + m / 3) * s)], (g) => 1 - Math.abs(g / 255 - 0.5) * 2],
      ["ink4", Number(st.overprint4), 1.5, 15, [-Math.round((1 + m * 0.5) * s), -Math.round((3 + m) * s)], (g) => Math.max(0, g / 255 - 0.35) / 0.65],
    ];
    for (const [name, amount, dotK, angK, [dx, dy], tone] of defs) {
      if (!(amount > 0)) continue;
      const k = Math.min(1, amount / 100) * 0.9, lt = new Uint8Array(n);
      for (let i = 0; i < n; i++) lt[i] = 255 - 255 * Math.min(1, Math.max(0, tone(gray[i]))) * k;
      const bx = halftoneBits(lt, cw, ch, st.dot_size * s * dotK, (Number(st.angle) + angK) % 90);
      extraPlates[name] = { bits: bx, rgb: st[name] };
      const [r3, g3, b3] = st[name];
      for (let y = 0; y < ch; y++) {
        const sy = y - dy; if (sy < 0 || sy >= ch) continue;
        for (let x = 0; x < cw; x++) {
          const sx = x - dx; if (sx < 0 || sx >= cw) continue;
          if (bx[sy * cw + sx] === 0) { const p = (y * cw + x) * 4; o[p] = (o[p] * r3) / 255; o[p + 1] = (o[p + 1] * g3) / 255; o[p + 2] = (o[p + 2] * b3) / 255; }
        }
      }
    }
  }
  addPaper(o, cw, ch, Number(st.paper), seed + 21, s);
  const result = makeCanvas(cw, ch);
  ctx2d(result).putImageData(out, 0, 0);
  addWear(result, st, seed + 51, s);
  addMechanism(result, st, seed + 61, s);
  drawLayers(result, st, paper, ink, opts.masks || {});
  return { canvas: result, bits, plate2, extraPlates, inks: { paper, ink, ink2: plate2 ? st.ink2 : null }, width: cw, height: ch };
}

// для проверки совпадения с Python-движком
export { drawLayers };
