// Мелкие помощники интерфейса: язык, диалоги, тосты, сохранение файлов, IndexedDB.

export const $ = (s, r = document) => r.querySelector(s);
export const $$ = (s, r = document) => [...r.querySelectorAll(s)];
export const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export const raf = () => new Promise((r) => requestAnimationFrame(() => r()));
export function debounce(fn, ms) {
  let t;
  const d = (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  d.flush = (...a) => { clearTimeout(t); fn(...a); };
  d.cancel = () => clearTimeout(t);
  return d;
}

// ---------------------------------------------------------------- язык
let stored = null;
try { stored = localStorage.getItem("zine.lang"); } catch { /* приватный режим */ }
export let LANG = stored || ((navigator.language || "en").toLowerCase().startsWith("ru") ? "ru" : "en");
export const T = (ru, en) => (LANG === "ru" ? ru : en);
export function setLang(l) {
  LANG = l;
  try { localStorage.setItem("zine.lang", l); } catch { /* ignore */ }
  document.documentElement.lang = l;
}

/** Подставляет тексты в статический HTML: data-ru/data-en, data-ru-title/…, data-ru-ph/… */
export function applyStaticLang(root = document) {
  document.documentElement.lang = LANG;
  for (const el of root.querySelectorAll("[data-ru]")) { const v = el.dataset[LANG]; if (v != null) el.innerHTML = v; }
  for (const el of root.querySelectorAll("[data-ru-title]")) { el.title = el.dataset[LANG === "ru" ? "ruTitle" : "enTitle"] || ""; }
  for (const el of root.querySelectorAll("[data-ru-ph]")) { el.placeholder = el.dataset[LANG === "ru" ? "ruPh" : "enPh"] || ""; }
  document.title = T("Xerox Zine Studio — веб-версия", "Xerox Zine Studio — web");
}

// ---------------------------------------------------------------- хранилище
export const ls = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch { return false; } },
  del(k) { try { localStorage.removeItem(k); } catch { /* ignore */ } },
};

let dbp = null;
function db() {
  if (dbp) return dbp;
  dbp = new Promise((res, rej) => {
    if (!window.indexedDB) return rej(new Error("no idb"));
    const rq = indexedDB.open("zine-studio", 1);
    rq.onupgradeneeded = () => rq.result.createObjectStore("kv");
    rq.onsuccess = () => res(rq.result);
    rq.onerror = () => rej(rq.error);
  });
  dbp.catch(() => { dbp = Promise.reject(new Error("idb unavailable")); dbp.catch(() => {}); });
  return dbp;
}
async function tx(mode, fn) {
  const d = await db();
  return new Promise((res, rej) => {
    const t = d.transaction("kv", mode), s = t.objectStore("kv");
    const r = fn(s);
    t.oncomplete = () => res(r && "result" in r ? r.result : undefined);
    t.onerror = t.onabort = () => rej(t.error);
  });
}
export const idb = {
  get: (k) => tx("readonly", (s) => s.get(k)).catch(() => undefined),
  set: (k, v) => tx("readwrite", (s) => s.put(v, k)),
  del: (k) => tx("readwrite", (s) => s.delete(k)).catch(() => {}),
  keys: () => tx("readonly", (s) => s.getAllKeys()).catch(() => []),
};

// ---------------------------------------------------------------- тост
let toastTimer = 0;
export function toast(msg, kind = "ok", ms = 2800) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = `toast ${kind}`;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, kind === "err" ? Math.max(ms, 5000) : ms);
}

// ---------------------------------------------------------------- диалоги
export function confirmDlg({ title, msg, ok = "OK", cancel = T("Отмена", "Cancel") }) {
  const d = $("#dlgConfirm");
  $("#confTitle").textContent = title;
  $("#confMsg").textContent = msg;
  $("#confOk").textContent = ok;
  $("#confCancel").textContent = cancel;
  return new Promise((res) => {
    d.addEventListener("close", () => res(d.returnValue === "ok"), { once: true });
    d.returnValue = "cancel";
    d.showModal();
  });
}

export function promptDlg({ title, msg = "", value = "", ok = "OK" }) {
  const d = $("#dlgPrompt"), inp = $("#promptInput");
  $("#promptTitle").textContent = title;
  $("#promptMsg").textContent = msg;
  $("#promptOk").textContent = ok;
  $("#promptCancel").textContent = T("Отмена", "Cancel");
  inp.value = value;
  return new Promise((res) => {
    d.addEventListener("close", () => res(d.returnValue === "ok" ? inp.value.trim() : null), { once: true });
    d.returnValue = "cancel";
    d.showModal();
    inp.focus(); inp.select();
  });
}

// ---------------------------------------------------------------- долгие задачи с прогрессом
export class Cancelled extends Error { constructor() { super("cancelled"); this.name = "Cancelled"; } }

export async function runJob(title, fn) {
  const d = $("#dlgJob"), bar = $("#jobBar"), msg = $("#jobMsg");
  let cancelled = false;
  $("#jobTitle").textContent = title;
  $("#jobCancel").textContent = T("Отмена", "Cancel");
  $("#jobCancel").onclick = () => { cancelled = true; $("#jobCancel").disabled = true; msg.textContent = T("Останавливаю…", "Stopping…"); };
  $("#jobCancel").disabled = false;
  msg.textContent = "";
  bar.style.width = "0%";
  d.addEventListener("cancel", (e) => e.preventDefault()); // Esc не закрывает
  d.showModal();
  const progress = async (text, frac) => {
    msg.textContent = text;
    bar.style.width = `${Math.round(clamp(frac, 0, 1) * 100)}%`;
    if (cancelled) throw new Cancelled();
    await raf(); // дать браузеру перерисовать
  };
  try { return await fn(progress); } finally { d.close(); }
}

// ---------------------------------------------------------------- сохранение файлов
const hasPicker = typeof window.showSaveFilePicker === "function" && !matchMedia("(pointer: coarse)").matches;

export function downloadBlob(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name; a.rel = "noopener";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

/**
 * Спрашивает, куда сохранить, ДО долгой работы (иначе браузер теряет жест пользователя).
 * Возвращает {name, write(blob)} или null, если человек отказался.
 * Без File System Access API файл просто скачивается.
 */
export async function askSave(name, { mime = "application/octet-stream", ext = "", desc = "" } = {}) {
  if (hasPicker) {
    try {
      const handle = await window.showSaveFilePicker({ suggestedName: name, types: ext ? [{ description: desc || ext, accept: { [mime]: [ext] } }] : undefined });
      return {
        name: handle.name, handle,
        async write(blob) { const w = await handle.createWritable(); await w.write(blob); await w.close(); },
      };
    } catch (e) {
      if (e && e.name === "AbortError") return null;
      /* другая ошибка: скачаем обычным способом */
    }
  }
  return { name, handle: null, async write(blob) { downloadBlob(blob, name); } };
}

export function baseName(name) { return String(name || "").replace(/\.[^.]+$/, ""); }
export function pad(n, w = 2) { return String(n).padStart(w, "0"); }
export const isTouch = () => matchMedia("(pointer: coarse)").matches;
export function fmtBytes(n) { return n > 1e6 ? `${(n / 1e6).toFixed(1)} МБ`.replace("МБ", LANG === "ru" ? "МБ" : "MB") : `${Math.round(n / 1e3)} ${LANG === "ru" ? "КБ" : "KB"}`; }
