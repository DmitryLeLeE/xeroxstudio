// Обёртка над renderPage: считает в воркерах, а если воркеров нет (старый браузер,
// ошибка загрузки, ?noworker) — на главном потоке, как раньше.
// Несколько воркеров нужны для экспорта многостраничной книги: страницы считаются параллельно.
import * as E from "./engine.js";
import { makeCanvas } from "./engine.js";

let state = "idle"; // idle | starting | ready | off
let readyP = null, nextId = 1;
let pool = [];                // {w, busy, sent: Map}
const pending = new Map();    // id → {resolve, reject, slot}
const srcIds = new WeakMap(); // canvas → id

export const renderMode = () => (state === "ready" ? "worker" : "main");
export const poolSize = () => pool.length;

function wantedWorkers() {
  const m = /[?&]workers=(\d+)/.exec(location.search);
  if (m) return Math.min(6, Math.max(1, +m[1]));
  const cores = navigator.hardwareConcurrency || 2;
  const phone = typeof matchMedia === "function" && matchMedia("(pointer: coarse)").matches;
  return phone ? 1 : Math.max(1, Math.min(3, cores - 1)); // на телефоне память важнее скорости
}

function turnOff(reason) {
  if (state === "off") return;
  state = "off";
  if (reason) console.warn("Воркер рендера отключён:", reason);
  for (const s of pool) { try { s.w.terminate(); } catch (e) { /* нет */ } }
  pool = [];
  for (const [, p] of pending) p.reject(Object.assign(new Error("worker down"), { workerDown: true }));
  pending.clear();
}

function spawn() {
  return new Promise((resolve) => {
    let w;
    try { w = new Worker(new URL("./render-worker.js", import.meta.url), { type: "module" }); }
    catch (e) { resolve(null); return; }
    const slot = { w, busy: 0, sent: new Map() };
    const timer = setTimeout(() => { try { w.terminate(); } catch (e) { /* нет */ } resolve(null); }, 15000);
    w.onerror = (e) => { clearTimeout(timer); if (pool.includes(slot)) turnOff(e.message || "error"); else resolve(null); };
    w.onmessage = (ev) => {
      if (ev.data.type !== "ready") return;
      clearTimeout(timer);
      if (!ev.data.ok) { try { w.terminate(); } catch (e) { /* нет */ } resolve(null); return; }
      w.onmessage = onMsg;
      resolve(slot);
    };
    w.postMessage({
      type: "init",
      fontsCss: new URL("../fonts/fonts.css", import.meta.url).href,
      faceUrl: new URL("../data/face.json", import.meta.url).href,
    });
  });
}

function start() {
  if (readyP) return readyP;
  if (typeof Worker === "undefined" || /[?&]noworker\b/.test(location.search)) { state = "off"; return (readyP = Promise.resolve(false)); }
  state = "starting";
  readyP = (async () => {
    const first = await spawn();               // первый — отдельно: если не вышло, остальные не нужны
    if (!first) { turnOff("no worker support"); return false; }
    pool = [first]; state = "ready";
    const rest = await Promise.all(Array.from({ length: wantedWorkers() - 1 }, spawn));
    for (const s of rest) if (s) pool.push(s);
    return true;
  })();
  return readyP;
}

function onMsg(ev) {
  const m = ev.data, p = pending.get(m.id);
  if (!p) { if (m.bitmap) m.bitmap.close(); return; }
  pending.delete(m.id);
  p.slot.busy--;
  if (m.type === "fail") { p.reject(new Error(m.message)); return; }
  const canvas = makeCanvas(m.width, m.height);
  canvas.getContext("2d").drawImage(m.bitmap, 0, 0);
  m.bitmap.close();
  p.resolve({ canvas, bits: m.bits, plate2: m.plate2, extraPlates: m.extraPlates || {}, inks: m.inks, width: m.width, height: m.height });
}

async function shipSource(slot, source) {
  const c = source.canvas;
  let id = srcIds.get(c);
  if (!id) { id = nextId++; srcIds.set(c, id); }
  const sig = c.width + "x" + c.height, have = slot.sent.get(id);
  if (!have || have.sig !== sig) {
    // кладём обещание сразу: параллельные запросы с тем же источником ждут одну и ту же отправку
    const p = createImageBitmap(c).then((bitmap) => slot.w.postMessage({ type: "src", id, bitmap }, [bitmap]));
    slot.sent.set(id, { sig, p });
    await p;
  } else await have.p;
  return id;
}

export async function renderPage(source, state_, opts = {}) {
  if (state === "idle" || state === "starting") await start();
  if (state !== "ready" || !pool.length) return E.renderPage(source, state_, opts);
  const slot = pool.reduce((a, b) => (b.busy < a.busy ? b : a));
  slot.busy++;
  try {
    const src = source && source.canvas ? await shipSource(slot, source) : null;
    const id = nextId++;
    const res = new Promise((resolve, reject) => pending.set(id, { resolve, reject, slot }));
    slot.w.postMessage({ type: "render", id, src, state: state_, opts });
    return await res;
  } catch (e) {
    if (e && e.workerDown) return E.renderPage(source, state_, opts);
    throw e;
  }
}

// Прогрев: чтобы первый кадр не ждал загрузки шрифтов в воркере.
export const warmUp = () => start();
