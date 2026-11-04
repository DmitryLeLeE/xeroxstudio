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
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.round(w));
  c.height = Math.max(1, Math.round(h));
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
function contrastRGB(data, factor) {
  let sum = 0;
  const n = data.length / 4;
  for (let p = 0; p < data.length; p += 4) sum += (data[p] * 299 + data[p + 1] * 587 + data[p + 2] * 114) / 1000;
  const mean = Math.floor(sum / n + 0.5);
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
  if (!document.fonts || !document.fonts.load) return;
  const st = mergeState(state);
  const sample = (text || `${st.txt_top} ${st.txt_bottom}`) + " ABCabc012";
  const jobs = [document.fonts.load(fontSpec(st.font, 40), sample)];
  if (st.layout === "contact_sheet") jobs.push(document.fonts.load(fontSpec("Courier New Bold", 15), "0123456789A"));
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
  addPaper(o, cw, ch, Number(st.paper), seed + 21, s);
  const result = makeCanvas(cw, ch);
  ctx2d(result).putImageData(out, 0, 0);
  return { canvas: result, bits, plate2, inks: { paper, ink, ink2: plate2 ? st.ink2 : null }, width: cw, height: ch };
}
