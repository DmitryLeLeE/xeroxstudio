// Поиск лиц в браузере: каскад Хаара (frontalface_default, Intel/OpenCV, BSD) на чистом JS.
// Нужен только для функции «чёрная полоса на глазах»; модель грузится один раз, при первом включении.
import { setFaceDetector, makeCanvas } from "./engine.js";

let model = null, loading = null;

export function facesReady() { return !!model; }

export function initFaces(url = "data/face.json") {
  if (model) return Promise.resolve(true);
  if (!loading) {
    loading = fetch(url)
      .then((r) => { if (!r.ok) throw new Error(`face.json: ${r.status}`); return r.json(); })
      .then((j) => {
        const foff = new Int32Array(j.f.length + 1), fdat = [];
        j.f.forEach((f, i) => { foff[i] = fdat.length; fdat.push(...f); foff[i + 1] = fdat.length; });
        const nodeCount = j.s.reduce((n, s) => n + s.n.length, 0);
        const nf = new Int32Array(nodeCount), nt = new Float32Array(nodeCount), nl = new Float32Array(nodeCount), nr = new Float32Array(nodeCount);
        const sStart = new Int32Array(j.s.length + 1), sThr = new Float32Array(j.s.length);
        let k = 0;
        j.s.forEach((s, si) => {
          sStart[si] = k; sThr[si] = s.t;
          for (const [fi, thr, lv, rv] of s.n) { nf[k] = fi; nt[k] = thr; nl[k] = lv; nr[k] = rv; k++; }
        });
        sStart[j.s.length] = k;
        model = { fdat: Float32Array.from(fdat), foff, nf, nt, nl, nr, sStart, sThr, ns: j.s.length, w: j.w, h: j.h };
        setFaceDetector(detectFaces);
        return true;
      })
      .catch((e) => { loading = null; console.warn("Каскад лиц не загружен:", e); return false; });
  }
  return loading;
}

function grayInt(canvas) {
  const w = canvas.width, h = canvas.height;
  const d = canvas.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, w, h).data;
  const W = w + 1;
  const sum = new Float64Array(W * (h + 1)), sq = new Float64Array(W * (h + 1));
  for (let y = 0; y < h; y++) {
    let rs = 0, rq = 0;
    for (let x = 0; x < w; x++) {
      const p = (y * w + x) * 4;
      const g = Math.round(0.299 * d[p] + 0.587 * d[p + 1] + 0.114 * d[p + 2]);
      rs += g; rq += g * g;
      const i = (y + 1) * W + x + 1;
      sum[i] = sum[i - W] + rs;
      sq[i] = sq[i - W] + rq;
    }
  }
  return { sum, sq, W };
}

function scan(model, canvas, factor, out) {
  const { sum, sq, W } = grayInt(canvas);
  const w = canvas.width, h = canvas.height, win = model.w;
  const area = (win - 2) * (win - 2);
  const { fdat, foff, nf: nodeF, nt, nl, nr, sStart, sThr, ns } = model;
  for (let y = 0; y + win <= h; y += 2) {
    for (let x = 0; x + win <= w; x += 2) {
      const s0 = sum[(y + win - 1) * W + x + win - 1] - sum[(y + 1) * W + x + win - 1] - sum[(y + win - 1) * W + x + 1] + sum[(y + 1) * W + x + 1];
      const q0 = sq[(y + win - 1) * W + x + win - 1] - sq[(y + 1) * W + x + win - 1] - sq[(y + win - 1) * W + x + 1] + sq[(y + 1) * W + x + 1];
      let nf = area * q0 - s0 * s0;
      nf = nf > 0 ? Math.sqrt(nf) : 1;
      const base = y * W + x;
      let si = 0;
      for (; si < ns; si++) {
        let acc = 0;
        for (let k = sStart[si], e = sStart[si + 1]; k < e; k++) {
          const fi = nodeF[k];
          let v = 0;
          for (let j = foff[fi], je = foff[fi + 1]; j < je; j += 5) {
            const p = base + fdat[j + 1] * W + fdat[j], rw = fdat[j + 2], rh = fdat[j + 3] * W;
            v += fdat[j + 4] * (sum[p + rh + rw] - sum[p + rw] - sum[p + rh] + sum[p]);
          }
          acc += v < nt[k] * nf ? nl[k] : nr[k];
        }
        if (acc < sThr[si]) break;
      }
      if (si === ns) out.push([x * factor, y * factor, win * factor, win * factor]);
    }
  }
}

// Группировка как в OpenCV groupRectangles(minNeighbors, eps=0.2)
function group(rects, minNeighbors, eps = 0.2) {
  const n = rects.length, parent = Array.from({ length: n }, (_, i) => i);
  const find = (i) => { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; };
  const similar = (a, b) => {
    const d = eps * (Math.min(a[2], b[2]) + Math.min(a[3], b[3])) * 0.5;
    return Math.abs(a[0] - b[0]) <= d && Math.abs(a[1] - b[1]) <= d &&
      Math.abs(a[0] + a[2] - b[0] - b[2]) <= d && Math.abs(a[1] + a[3] - b[1] - b[3]) <= d;
  };
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (similar(rects[i], rects[j])) parent[find(i)] = find(j);
  const cl = new Map();
  rects.forEach((r, i) => {
    const k = find(i);
    const c = cl.get(k) || { n: 0, x: 0, y: 0, w: 0, h: 0 };
    c.n++; c.x += r[0]; c.y += r[1]; c.w += r[2]; c.h += r[3];
    cl.set(k, c);
  });
  const avg = [...cl.values()].filter((c) => c.n > minNeighbors).map((c) => ({ n: c.n, r: [c.x / c.n, c.y / c.n, c.w / c.n, c.h / c.n] }));
  return avg.filter((a, i) => !avg.some((b, j) => {
    if (i === j) return false;
    const [x, y, w, h] = a.r, [X, Y, W, H] = b.r, dx = W * 0.2, dy = H * 0.2;
    const inside = x >= X - dx && y >= Y - dy && x + w <= X + W + dx && y + h <= Y + H + dy;
    return inside && (b.n > Math.max(3, a.n) || a.n < 3);
  })).map((a) => a.r);
}

/** canvas -> [[x, y, w, h], ...] в пикселях canvas. */
export function detectFaces(canvas) {
  if (!model) return [];
  const k = Math.min(1, 900 / Math.max(canvas.width, canvas.height));
  const bw = Math.max(1, Math.round(canvas.width * k)), bh = Math.max(1, Math.round(canvas.height * k));
  const base = makeCanvas(bw, bh);
  const bc = base.getContext("2d");
  bc.imageSmoothingQuality = "high";
  bc.drawImage(canvas, 0, 0, bw, bh);
  const found = [];
  for (let f = 1; Math.min(bw, bh) / f >= 24; f *= 1.1) {
    const sw = Math.round(bw / f), sh = Math.round(bh / f);
    if (sw < 24 || sh < 24) break;
    let c = base;
    if (f > 1) {
      c = makeCanvas(sw, sh);
      const cc = c.getContext("2d");
      cc.imageSmoothingQuality = "medium";
      cc.drawImage(base, 0, 0, sw, sh);
    }
    scan(model, c, f, found);
  }
  const minSize = 24; // как minSize=(24, 24) в десктопной версии
  return group(found, 4).filter((r) => r[2] >= minSize).map(([x, y, w, h]) => [x / k, y / k, w / k, h / k]);
}
