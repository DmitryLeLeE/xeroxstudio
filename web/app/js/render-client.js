// Обёртка над renderPage: считает в воркере, а если воркера нет (старый браузер,
// ошибка загрузки, ?noworker) — на главном потоке, как раньше.
import * as E from "./engine.js";
import { makeCanvas } from "./engine.js";

let worker = null, state = "idle"; // idle | starting | ready | off
let readyP = null, nextId = 1;
const pending = new Map();
const srcIds = new WeakMap(); // canvas → id
const sent = new Map();       // id → "WxH" (то, что уже лежит в воркере)

export const renderMode = () => (state === "ready" ? "worker" : "main");

function turnOff(reason) {
  if (state === "off") return;
  state = "off";
  if (reason) console.warn("Воркер рендера отключён:", reason);
  if (worker) { try { worker.terminate(); } catch (e) { /* нет */ } worker = null; }
  for (const [, p] of pending) p.reject(Object.assign(new Error("worker down"), { workerDown: true }));
  pending.clear();
}

function start() {
  if (readyP) return readyP;
  const off = typeof Worker === "undefined" || /[?&]noworker\b/.test(location.search);
  if (off) { state = "off"; return (readyP = Promise.resolve(false)); }
  state = "starting";
  readyP = new Promise((resolve) => {
    try {
      worker = new Worker(new URL("./render-worker.js", import.meta.url), { type: "module" });
    } catch (e) { turnOff(String(e)); resolve(false); return; }
    const timer = setTimeout(() => { turnOff("timeout"); resolve(false); }, 15000);
    worker.onerror = (e) => { clearTimeout(timer); turnOff(e.message || "error"); resolve(false); };
    worker.onmessage = (ev) => {
      const m = ev.data;
      if (m.type === "ready") {
        clearTimeout(timer);
        if (m.ok) { state = "ready"; worker.onmessage = onMsg; resolve(true); }
        else { turnOff("no OffscreenCanvas"); resolve(false); }
      }
    };
    worker.postMessage({
      type: "init",
      fontsCss: new URL("../fonts/fonts.css", import.meta.url).href,
      faceUrl: new URL("../data/face.json", import.meta.url).href,
    });
  });
  return readyP;
}

function onMsg(ev) {
  const m = ev.data, p = pending.get(m.id);
  if (!p) { if (m.bitmap) m.bitmap.close(); return; }
  pending.delete(m.id);
  if (m.type === "fail") { p.reject(new Error(m.message)); return; }
  const canvas = makeCanvas(m.width, m.height);
  canvas.getContext("2d").drawImage(m.bitmap, 0, 0);
  m.bitmap.close();
  p.resolve({ canvas, bits: m.bits, plate2: m.plate2, extraPlates: m.extraPlates || {}, inks: m.inks, width: m.width, height: m.height });
}

async function shipSource(source) {
  const c = source.canvas;
  let id = srcIds.get(c);
  if (!id) { id = nextId++; srcIds.set(c, id); }
  const sig = c.width + "x" + c.height;
  if (sent.get(id) !== sig) {
    const bitmap = await createImageBitmap(c);
    worker.postMessage({ type: "src", id, bitmap }, [bitmap]);
    sent.set(id, sig);
  }
  return id;
}

export async function renderPage(source, state_, opts = {}) {
  if (state === "idle" || state === "starting") await start();
  if (state !== "ready") return E.renderPage(source, state_, opts);
  try {
    const src = source && source.canvas ? await shipSource(source) : null;
    const id = nextId++;
    const res = new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
    worker.postMessage({ type: "render", id, src, state: state_, opts });
    return await res;
  } catch (e) {
    if (e && e.workerDown) return E.renderPage(source, state_, opts);
    throw e;
  }
}

// Прогрев: чтобы первый кадр не ждал загрузки шрифтов в воркере.
export const warmUp = () => start();
