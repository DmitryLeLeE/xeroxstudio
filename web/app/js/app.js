// Xerox Zine Studio — веб-версия. Всё работает в браузере, фото никуда не отправляются.
import { CFG } from "./config.js";
import * as E from "./engine.js";
import * as IO from "./io.js";
import { initFaces } from "./faces.js";
import {
  $, $$, clamp, debounce, sleep, T, LANG, setLang, applyStaticLang, ls, idb, toast, confirmDlg, promptDlg,
  runJob, Cancelled, askSave, downloadBlob, baseName, pad, isTouch,
} from "./util.js";

const DEF = CFG.DEFAULT_STATE;
const FORMAT_KEYS = Object.keys(CFG.CANVAS_FORMATS);
const TOUCH = isTouch();
const MAX_SIDE = TOUCH ? 3072 : 4096; // длинная сторона загруженного фото: защита памяти

// ---------------------------------------------------------------- подписи (RU — как в .zine и десктопе)
const EN = {
  "2:3 Постер (1000×1500)": "2:3 Poster (1000×1500)", "1:1 Квадрат / Обложка (1200×1200)": "1:1 Square / Cover (1200×1200)",
  "9:16 Stories / Обои (1080×1920)": "9:16 Stories / Wallpaper (1080×1920)", "3:4 Принт (1200×1600)": "3:4 Print (1200×1600)",
  staggered: "Staggered (zigzag)", column: "Column (room for text)", contact_sheet: "Contact sheet (frames)", center_hero: "Hero + copies",
  column_right: "Column on the right", diagonal: "Diagonal cascade", pile: "Pile (overlapping collage)", two_columns: "Two columns",
  mosaic: "Mosaic (one big + small)", duo: "Diptych (two large)", triptych: "Triptych (three strips)", ribbon: "Ribbon (a row of frames)", full_page: "Full page",
  halftone: "Halftone (dots)", floyd: "Floyd–Steinberg grain", stencil: "Stencil (threshold)",
  contain: "Fit whole photo", cover: "Fill the frame",
  white_box: "White box", dymo_tape: "Black tape (Dymo)", outline: "Outline (black, white stroke)",
  left: "Left", center: "Center", right: "Right",
  "Пользовательская (Custom)": "Custom",
  "Классический ксерокс": "Classic Xerox", "Газетная печать": "Newsprint", "Кислотный райот": "Acid Riot", "Панк-флаер": "Punk Flyer",
  "Синька (cyanotype)": "Cyanotype", "Контактный лист 35 мм": "35 mm Contact Sheet", "Ночное видение": "Night Vision", "Ризо-оверпринт": "Riso Overprint", "Склейка со скотчем": "Tape Collage",
  "Мои": "Mine",
};
const lbl = (ru, key) => (LANG === "ru" ? ru : EN[key] || EN[ru] || ru);
const pairs = (list) => list.map(([ru, v]) => [v, lbl(ru, v)]);

// ---------------------------------------------------------------- состояние
const S = {
  pages: [], cur: 0, images: new Map(), blobs: new Map(), name: "zine", handle: null, dirty: false, counter: 0,
};
const page = () => S.pages[S.cur];
const srcFor = (st) => (st && st.img && S.images.get(st.img)) || null;
const baseSize = (st = page()) => CFG.CANVAS_FORMATS[st.format] || CFG.CANVAS_FORMATS[FORMAT_KEYS[0]];
const sigOf = (st) => JSON.stringify(st);
const rnd = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
const clone = (o) => JSON.parse(JSON.stringify(o));
const newSeed = () => rnd(1, 1e6);

function newKey() {
  let k;
  do { k = `web${++S.counter}`; } while (S.images.has(k));
  return k;
}

function normalizePage(p) {
  const st = { ...clone(DEF), ...p };
  st.layout = CFG.LAYOUT_ALIASES[st.layout] || st.layout;
  if (!CFG.CANVAS_FORMATS[st.format]) st.format = DEF.format;
  if (!Array.isArray(st.crop) || st.crop.length !== 4) st.crop = [0, 0, 1, 1];
  if (!Array.isArray(st.custom_colors) || st.custom_colors.length !== 2) st.custom_colors = clone(DEF.custom_colors);
  if (st.img && !S.images.has(st.img)) st.img = null;
  return st;
}

function firstQuote() { return CFG.MANIFESTOS[0]; }
function freshPage(extra = {}) {
  const q = firstQuote();
  return { ...clone(DEF), txt_top: q.top, txt_bottom: q.bottom, ...extra };
}

// ---------------------------------------------------------------- история (отмена / возврат)
const H = { stack: [], idx: -1 };
const snap = () => JSON.stringify({ pages: S.pages, cur: S.cur });
const commitSoon = debounce(() => commit(), 700);

function commit({ dirty = true } = {}) {
  commitSoon.cancel();
  const s = snap();
  if (H.stack[H.idx] === s) return;
  H.stack.length = H.idx + 1;
  H.stack.push(s);
  if (H.stack.length > 150) H.stack.shift();
  H.idx = H.stack.length - 1;
  if (dirty) markDirty();
  updateUndoButtons();
  gcImages();
}
const flushCommit = () => commitSoon.flush();
function resetHistory() { H.stack = []; H.idx = -1; commit({ dirty: false }); }

function restoreSnap(str) {
  const d = JSON.parse(str), before = `${S.cur}|${page().format}`;
  S.pages = d.pages.map(normalizePage);
  S.cur = clamp(d.cur, 0, S.pages.length - 1);
  afterPageSwitch({ refit: before !== `${S.cur}|${page().format}` });
  markDirty();
  updateUndoButtons();
}
function undo() { flushCommit(); if (H.idx > 0) { H.idx--; restoreSnap(H.stack[H.idx]); toast(T("↶ Отменено", "↶ Undone"), "ok", 900); } }
function redo() { flushCommit(); if (H.idx < H.stack.length - 1) { H.idx++; restoreSnap(H.stack[H.idx]); toast(T("↷ Возвращено", "↷ Redone"), "ok", 900); } }
function updateUndoButtons() { $("#btnUndo").disabled = H.idx <= 0; $("#btnRedo").disabled = H.idx >= H.stack.length - 1; }

/** Убираем фото, которых нет ни на одной странице и ни в одном шаге истории. */
function gcImages() {
  if (S.images.size < 6) return;
  const all = H.stack.join("\n");
  for (const k of [...S.images.keys()]) {
    if (!S.pages.some((p) => p.img === k) && !all.includes(`"img":"${k}"`)) { S.images.delete(k); S.blobs.delete(k); }
  }
}

function markDirty() {
  S.dirty = true;
  document.title = `• ${T("Xerox Zine Studio — веб-версия", "Xerox Zine Studio — web")}`;
  autosaveSoon();
}
function markClean() {
  S.dirty = false;
  document.title = T("Xerox Zine Studio — веб-версия", "Xerox Zine Studio — web");
}
window.addEventListener("beforeunload", (e) => { if (S.dirty) { e.preventDefault(); e.returnValue = ""; } });

// ---------------------------------------------------------------- панель настроек
const SECTIONS = () => [
  { tab: "style", title: T("1. ФОРМАТ И СЕТКА", "1. FORMAT & GRID"), items: [
    { k: "format", t: "select", label: T("Формат холста", "Canvas format"), opts: () => FORMAT_KEYS.map((k) => [k, lbl(k, k)]) },
    { k: "layout", t: "select", label: T("Раскладка кадров", "Frame layout"), opts: () => pairs(CFG.LAYOUTS) },
    { k: "rows", t: "range", label: T("Строк / копий", "Rows / copies"), min: 3, max: 16, step: 1 },
    { k: "tilt", t: "range", label: T("Наклон кадров (°)", "Frame tilt (°)"), min: 0, max: 5, step: 0.2 },
  ] },
  { tab: "style", title: T("2. ФОТО И КАДРЫ", "2. PHOTO & FRAMES"), items: [
    { k: "fit_mode", t: "select", label: T("Как класть фото в кадр", "Fit photo into frame"), opts: () => pairs(CFG.FIT_MODES) },
    { k: "bright", t: "range", label: T("Яркость фото", "Photo brightness"), min: 0.6, max: 2, step: 0.05 },
    { k: "edge_x", t: "range", label: T("Рваный край по X", "Torn edge X"), min: 0, max: 50, step: 1 },
    { k: "edge_y", t: "range", label: T("Рваный край по Y", "Torn edge Y"), min: 0, max: 50, step: 1 },
    { k: "loss", t: "range", label: T("Потеря качества копий", "Generation loss"), min: 0, max: 100, step: 1 },
    { k: "tape", t: "range", label: T("Малярный скотч на кадрах", "Masking tape on frames"), min: 0, max: 100, step: 1 },
    { k: "censor", t: "check", label: T("Чёрная полоса на глазах (поиск лиц)", "Black bar over eyes (face detection)") },
    { k: "sticker", t: "check", label: T("Вырезка-стикер (тёмный объект на светлом фоне)", "Sticker cut-out (dark object on light background)") },
    { t: "button", label: T("🎲 Другие края и пыль", "🎲 New edges & dust"), act: () => { flushCommit(); page().seed = newSeed(); commit(); requestRender(); } },
  ] },
  { tab: "style", title: T("3. РАСТР И ТОНЕР", "3. HALFTONE & TONER"), items: [
    { k: "dither", t: "select", label: T("Тип растра", "Raster type"), opts: () => pairs(CFG.DITHERS) },
    { k: "dot_size", t: "range", label: T("Размер точки растра", "Dot size"), min: 3, max: 22, step: 1 },
    { k: "angle", t: "range", label: T("Угол растра (°)", "Screen angle (°)"), min: 0, max: 90, step: 1 },
    { k: "contrast", t: "range", label: T("Контраст", "Contrast"), min: 1, max: 4.5, step: 0.1 },
    { k: "noise", t: "range", label: T("Шум тонера", "Toner noise"), min: 0, max: 100, step: 1 },
    { k: "streaks", t: "range", label: T("Полосы сканера", "Scanner streaks"), min: 0, max: 100, step: 1 },
    { k: "misreg", t: "range", label: T("Приводка (сдвиг краски)", "Misregistration"), min: 0, max: 12, step: 1 },
    { k: "copier_edge", t: "range", label: T("Тень края копира", "Copier edge shadow"), min: 0, max: 100, step: 1 },
    { k: "paper", t: "range", label: T("Фактура бумаги", "Paper texture"), min: 0, max: 100, step: 1 },
    { k: "overprint", t: "range", label: T("Второй цвет (оверпринт)", "Second ink (overprint)"), min: 0, max: 100, step: 1 },
    { k: "ink2", t: "color2", label: T("Цвет второй краски", "Second ink colour") },
  ] },
  { tab: "style", title: T("4. ПАЛИТРА (RISOGRAPH)", "4. PALETTE (RISOGRAPH)"), items: [
    { k: "palette", t: "select", label: T("Бумага / краска", "Paper / ink"),
      opts: () => [...Object.keys(CFG.RISO_PALETTES).map((k) => [k, k]), [CFG.CUSTOM_PALETTE, lbl(CFG.CUSTOM_PALETTE, CFG.CUSTOM_PALETTE)]] },
    { t: "swatches" },
    { k: "invert", t: "check", label: T("Инвертировать цвета", "Invert colors") },
  ] },
  { tab: "text", title: T("5. МАНИФЕСТЫ И ТИПОГРАФИКА", "5. MANIFESTOS & TYPOGRAPHY"), items: [
    { k: "txt_top", t: "text", label: T("Верхняя надпись", "Top caption") },
    { k: "txt_bottom", t: "text", label: T("Нижняя надпись", "Bottom caption") },
    { t: "button", kind: "primary", label: T("📚 Библиотека манифестов…", "📚 Manifesto library…"), act: () => openManifest() },
    { t: "buttons", items: [
      [T("🎲 Случайный", "🎲 Random"), () => randomQuote()],
      [T("★ В мои", "★ Save to mine"), () => saveMyManifesto()],
    ] },
    { k: "font", t: "select", label: T("Шрифт", "Font"), opts: () => Object.keys(CFG.FONTS).map((k) => [k, k]) },
    { k: "tstyle", t: "select", label: T("Подложка", "Backing"), opts: () => pairs(CFG.TEXT_STYLES) },
    { k: "text_align", t: "select", label: T("Выравнивание", "Alignment"), opts: () => pairs(CFG.TEXT_ALIGNS) },
    { k: "font_size", t: "range", label: T("Размер шрифта", "Font size"), min: 14, max: 120, step: 1 },
    { k: "txt_x", t: "range", label: T("Позиция X (%)", "Position X (%)"), min: 2, max: 85, step: 1 },
    { k: "txt_y1", t: "range", label: T("Верхняя надпись Y (%)", "Top caption Y (%)"), min: 2, max: 50, step: 1 },
    { k: "txt_y2", t: "range", label: T("Нижняя надпись Y (%)", "Bottom caption Y (%)"), min: 30, max: 95, step: 1 },
    { k: "text_rot", t: "range", label: T("Поворот надписи (°)", "Caption rotation (°)"), min: -45, max: 45, step: 1 },
  ] },
];

const ctlEls = {}; // k -> {el, out}
const decimals = (step) => (String(step).split(".")[1] || "").length;
let presetSel = null;

function buildSettings() {
  const host = $("#sections");
  host.textContent = "";
  for (const k of Object.keys(ctlEls)) delete ctlEls[k];
  buildPresetRow();
  for (const sec of SECTIONS()) {
    const det = document.createElement("details");
    det.className = "sect"; det.open = true; det.dataset.tab = sec.tab;
    det.innerHTML = `<summary>${sec.title}</summary>`;
    const body = document.createElement("div");
    body.className = "sect-body";
    det.append(body);
    for (const it of sec.items) body.append(buildControl(it));
    host.append(det);
  }
  syncUI();
}

function buildControl(it) {
  const wrap = document.createElement("div");
  wrap.className = "ctl";
  const id = `c_${it.k || Math.random().toString(36).slice(2)}`;
  const touch = () => { resetPresetLabel(); };

  if (it.t === "select") {
    wrap.innerHTML = `<div class="ctl-h"><label for="${id}">${it.label}</label></div>`;
    const sel = document.createElement("select");
    sel.className = "sel"; sel.id = id;
    for (const [v, text] of it.opts()) sel.append(new Option(text, v));
    sel.addEventListener("change", () => {
      flushCommit();
      page()[it.k] = sel.value;
      touch();
      if (it.k === "format") { fitView(); }
      if (it.k === "palette") updateSwatches();
      commit(); requestRender();
    });
    wrap.append(sel);
    ctlEls[it.k] = { el: sel };
  } else if (it.t === "range") {
    const dec = decimals(it.step);
    wrap.innerHTML = `<div class="ctl-h"><label for="${id}">${it.label}</label><output></output></div>`;
    const inp = document.createElement("input");
    inp.type = "range"; inp.id = id; inp.min = it.min; inp.max = it.max; inp.step = it.step;
    const out = $("output", wrap);
    inp.addEventListener("input", () => {
      page()[it.k] = Number(inp.value);
      out.textContent = Number(inp.value).toFixed(dec);
      touch(); requestRender({ draft: true });
    });
    inp.addEventListener("change", () => { commit(); requestRender(); });
    inp.addEventListener("dblclick", () => { // двойной клик возвращает значение по умолчанию
      flushCommit(); page()[it.k] = DEF[it.k]; syncUI(); commit(); requestRender();
    });
    wrap.append(inp);
    ctlEls[it.k] = { el: inp, out, dec };
  } else if (it.t === "check") {
    wrap.innerHTML = `<label class="chk"><input type="checkbox" id="${id}"><span>${it.label}</span></label>`;
    const cb = $("input", wrap);
    cb.addEventListener("change", async () => {
      flushCommit();
      if (it.k === "censor" && cb.checked) {
        setBusy(true, T("Загружаю поиск лиц…", "Loading face detection…"));
        const ok = await initFaces();
        setBusy(false);
        if (!ok) { cb.checked = false; toast(T("Не удалось загрузить поиск лиц (нужен интернет при первом запуске)", "Could not load face detection (needs a connection the first time)"), "err"); return; }
      }
      page()[it.k] = cb.checked;
      touch(); commit(); requestRender();
    });
    ctlEls[it.k] = { el: cb };
  } else if (it.t === "text") {
    wrap.innerHTML = `<div class="ctl-h"><label for="${id}">${it.label}</label></div>`;
    const ta = document.createElement("textarea");
    ta.id = id; ta.rows = 2; ta.spellcheck = false; ta.autocapitalize = "characters";
    ta.addEventListener("input", () => { page()[it.k] = ta.value; touch(); requestRender(); commitSoon(); });
    ta.addEventListener("blur", () => flushCommit());
    wrap.append(ta);
    ctlEls[it.k] = { el: ta };
  } else if (it.t === "color2") {
    wrap.innerHTML = `<div class="ctl-h"><label for="${id}">${it.label}</label></div><input type="color" id="${id}" class="col2" aria-label="${it.label}">`;
    const col = $("input", wrap);
    col.addEventListener("input", () => { page().ink2 = hexRgb(col.value); touch(); requestRender({ draft: true }); });
    col.addEventListener("change", () => { commit(); requestRender(); });
    ctlEls[it.k] = { el: col, rgb: true };
  } else if (it.t === "button") {
    const b = document.createElement("button");
    b.className = `btn wide ${it.kind || ""}`; b.textContent = it.label;
    b.addEventListener("click", it.act);
    return b;
  } else if (it.t === "buttons") {
    wrap.className = "row gap";
    for (const [text, fn] of it.items) {
      const b = document.createElement("button");
      b.className = "btn grow"; b.textContent = text; b.addEventListener("click", fn);
      wrap.append(b);
    }
  } else if (it.t === "swatches") {
    wrap.innerHTML = `<div class="swatches"><div class="sw" id="swPaper" title="${T("Бумага", "Paper")}"></div><div class="sw" id="swInk" title="${T("Краска", "Ink")}"></div>
      <span class="sw-btn"><button class="btn sm" id="pickPaper">${T("Бумага…", "Paper…")}</button><input type="color" id="colPaper" tabindex="-1" aria-label="${T("Цвет бумаги", "Paper color")}"></span>
      <span class="sw-btn"><button class="btn sm" id="pickInk">${T("Краска…", "Ink…")}</button><input type="color" id="colInk" tabindex="-1" aria-label="${T("Цвет краски", "Ink color")}"></span></div>`;
    for (const [i, nm] of [[0, "Paper"], [1, "Ink"]]) {
      const btn = $(`#pick${nm}`, wrap), col = $(`#col${nm}`, wrap);
      btn.addEventListener("click", () => {
        const [p0, p1] = paletteColors(page(), false);
        col.value = rgbHex(i === 0 ? p0 : p1);
        col.click();
      });
      col.addEventListener("input", () => {
        const st = page();
        if (st.palette !== CFG.CUSTOM_PALETTE) { st.custom_colors = paletteColors(st, false).map((c) => [...c]); st.palette = CFG.CUSTOM_PALETTE; ctlEls.palette.el.value = st.palette; }
        st.custom_colors[i] = hexRgb(col.value);
        resetPresetLabel(); updateSwatches(); requestRender({ draft: true });
      });
      col.addEventListener("change", () => { commit(); requestRender(); });
    }
  }
  return wrap;
}

const rgbHex = (c) => `#${c.map((v) => pad(Math.round(v).toString(16), 2)).join("")}`;
const hexRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
function paletteColors(st, applyInvert = true) {
  let pair = st.palette === CFG.CUSTOM_PALETTE ? st.custom_colors : CFG.RISO_PALETTES[st.palette] || CFG.RISO_PALETTES["Classic B&W (Xerox)"];
  pair = [pair[0], pair[1]];
  return applyInvert && st.invert ? [pair[1], pair[0]] : pair;
}
function updateSwatches() {
  const [p, i] = paletteColors(page());
  const a = $("#swPaper"), b = $("#swInk");
  if (a) { a.style.background = rgbHex(p); b.style.background = rgbHex(i); }
}

/** Значения из состояния страницы -> элементы управления. */
function syncUI() {
  const st = page();
  if (!st) return;
  for (const [k, c] of Object.entries(ctlEls)) {
    const v = st[k];
    if (c.rgb) c.el.value = rgbHex(v || [255, 60, 140]);
    else if (c.el.type === "checkbox") c.el.checked = !!v;
    else { c.el.value = v ?? ""; if (c.out) c.out.textContent = Number(v).toFixed(c.dec); }
  }
  updateSwatches();
}

// ---------------------------------------------------------------- пресеты
const userPresets = () => ls.get("zine.presets", {});
function allPresets() { return { ...CFG.BUILTIN_PRESETS, ...userPresets() }; }
function buildPresetRow() {
  const row = $("#presetRow");
  row.textContent = "";
  row.innerHTML = `<span class="cap">${T("СТИЛЬ", "STYLE")}</span>`;
  presetSel = document.createElement("select");
  presetSel.className = "sel"; presetSel.setAttribute("aria-label", T("Пресет стиля", "Style preset"));
  fillPresets();
  presetSel.addEventListener("change", () => { if (presetSel.value) applyPreset(presetSel.value); });
  const save = document.createElement("button");
  save.className = "btn icon"; save.textContent = "＋"; save.title = T("Сохранить текущий стиль как пресет", "Save current style as a preset");
  save.addEventListener("click", savePreset);
  const del = document.createElement("button");
  del.className = "btn icon"; del.textContent = "🗑"; del.title = T("Удалить выбранный свой пресет", "Delete selected custom preset");
  del.addEventListener("click", deletePreset);
  row.append(presetSel, save, del);
}
function fillPresets(selected = "") {
  presetSel.textContent = "";
  presetSel.append(new Option(T("Выберите пресет…", "Choose a preset…"), ""));
  const g1 = document.createElement("optgroup"); g1.label = T("Встроенные", "Built-in");
  for (const n of Object.keys(CFG.BUILTIN_PRESETS)) g1.append(new Option(lbl(n, n), n));
  presetSel.append(g1);
  const user = Object.keys(userPresets());
  if (user.length) {
    const g2 = document.createElement("optgroup"); g2.label = T("Мои", "Mine");
    for (const n of user) g2.append(new Option(n, n));
    presetSel.append(g2);
  }
  presetSel.value = selected;
}
function resetPresetLabel() { if (presetSel && presetSel.value) presetSel.value = ""; }
function applyPreset(name) {
  const p = allPresets()[name];
  if (!p) return;
  flushCommit();
  const st = page();
  for (const k of CFG.STYLE_KEYS) if (k in p) st[k] = clone(p[k]);
  syncUI(); commit(); requestRender();
  toast(T(`Стиль применён: ${lbl(name, name)}`, `Style applied: ${lbl(name, name)}`), "ok", 1400);
}
async function savePreset() {
  const name = await promptDlg({ title: T("Сохранить стиль", "Save style"), msg: T("Название пресета (фото, кадр и тексты не сохраняются):", "Preset name (photo, crop and captions are not saved):"), ok: T("Сохранить", "Save") });
  if (!name) return;
  if (name in CFG.BUILTIN_PRESETS) { toast(T("Это имя занято встроенным пресетом", "That name belongs to a built-in preset"), "err"); return; }
  const u = userPresets();
  u[name] = Object.fromEntries(CFG.STYLE_KEYS.map((k) => [k, clone(page()[k])]));
  ls.set("zine.presets", u);
  fillPresets(name);
  toast(T(`Пресет «${name}» сохранён`, `Preset “${name}” saved`));
}
async function deletePreset() {
  const name = presetSel.value, u = userPresets();
  if (!(name in u)) { toast(T("Выберите свой пресет — встроенные удалить нельзя", "Pick one of your presets — built-ins can't be deleted"), "err"); return; }
  if (!(await confirmDlg({ title: T("Удалить пресет?", "Delete preset?"), msg: name, ok: T("Удалить", "Delete") }))) return;
  delete u[name]; ls.set("zine.presets", u); fillPresets();
}
function applyStyleToAll() {
  flushCommit();
  const src = page();
  S.pages.forEach((st, i) => { if (i !== S.cur) for (const k of CFG.STYLE_KEYS) st[k] = clone(src[k]); });
  commit(); renderStrip();
  toast(T(`Стиль применён к страницам: ${S.pages.length - 1}`, `Style applied to ${S.pages.length - 1} page(s)`));
}

// ---------------------------------------------------------------- рендер
const R = { running: false, again: false, draft: false, timer: 0, final: 0 };
const preview = $("#preview");
const pctx = preview.getContext("2d");

function requestRender({ draft = false } = {}) {
  R.draft = draft;
  clearTimeout(R.timer);
  R.timer = setTimeout(pump, draft ? 10 : 50);
  clearTimeout(R.final);
  if (draft) R.final = setTimeout(() => requestRender(), 380);
}
const previewScale = (draft) => (TOUCH ? 0.7 : 1) * (draft ? 0.55 : 1);

async function pump() {
  if (R.running) { R.again = true; return; }
  R.running = true;
  setBusy(true);
  try {
    do {
      R.again = false;
      const draft = R.draft; R.draft = false;
      const st = clone(page()), idx = S.cur;
      try {
        const res = await E.renderPage(srcFor(st), st, { scale: previewScale(draft) });
        if (idx === S.cur) {
          if (preview.width !== res.width || preview.height !== res.height) { preview.width = res.width; preview.height = res.height; }
          pctx.drawImage(res.canvas, 0, 0);
          if (!draft) { setThumb(sigOf(st), res.canvas); paintThumbs(); }
        }
      } catch (e) {
        console.error(e);
        toast(T("Не удалось собрать страницу: ", "Could not render the page: ") + (e.message || e), "err");
      }
    } while (R.again);
  } finally {
    R.running = false;
    setBusy(false);
    pumpThumbs();
  }
}
function setBusy(on, text = "") {
  $("#busy").hidden = !on;
  $("#busyTxt").textContent = text;
}

// ---------------------------------------------------------------- миниатюры страниц
const thumbCache = new Map(); // подпись состояния -> canvas
const THUMB_SCALE = 0.16;
function setThumb(sig, canvas) {
  const w = 130, h = Math.round((canvas.height / canvas.width) * w);
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  const x = c.getContext("2d"); x.imageSmoothingQuality = "high"; x.drawImage(canvas, 0, 0, w, h);
  thumbCache.set(sig, c);
  if (thumbCache.size > 80) thumbCache.delete(thumbCache.keys().next().value);
}
const T_ = { running: false, again: false };
async function pumpThumbs() {
  if (T_.running) { T_.again = true; return; }
  T_.running = true;
  try {
    do {
      T_.again = false;
      for (let i = 0; i < S.pages.length; i++) {
        const st = S.pages[i], sig = sigOf(st);
        if (thumbCache.has(sig)) continue;
        if (R.running) { T_.again = true; break; } // главное превью важнее
        try {
          const r = await E.renderPage(srcFor(st), st, { scale: THUMB_SCALE });
          setThumb(sig, r.canvas); paintThumbs();
        } catch (e) { console.warn("миниатюра", e); thumbCache.set(sig, document.createElement("canvas")); }
        await sleep(15);
        if (T_.again) break;
      }
      if (T_.again) await sleep(250);
    } while (T_.again);
  } finally { T_.running = false; }
}

function renderStrip() {
  const box = $("#thumbs");
  box.textContent = "";
  S.pages.forEach((st, i) => {
    const b = document.createElement("button");
    b.className = "th"; b.setAttribute("role", "tab"); b.setAttribute("aria-selected", String(i === S.cur));
    b.setAttribute("aria-label", T(`Страница ${i + 1}`, `Page ${i + 1}`));
    b.innerHTML = `<canvas width="130" height="195"></canvas><b>${i + 1}</b>`;
    b.addEventListener("click", () => gotoPage(i));
    box.append(b);
  });
  $("#pageInfo").textContent = T(`${S.cur + 1} из ${S.pages.length}`, `${S.cur + 1} of ${S.pages.length}`);
  paintThumbs();
  pumpThumbs();
  const sel = box.children[S.cur];
  if (sel && sel.scrollIntoView) sel.scrollIntoView({ block: "nearest", inline: "center" });
}
function paintThumbs() {
  const btns = $("#thumbs").children;
  S.pages.forEach((st, i) => {
    const b = btns[i];
    if (!b) return;
    const c = $("canvas", b), src = thumbCache.get(sigOf(st));
    if (src && src.width) { c.width = src.width; c.height = src.height; c.getContext("2d").drawImage(src, 0, 0); }
  });
}

// ---------------------------------------------------------------- вид (панорама и зум)
const V = { zoom: 1, tx: 0, ty: 0, fitted: true };
const vp = $("#viewport");
function applyView() {
  const [bw, bh] = baseSize();
  preview.style.width = `${bw * V.zoom}px`;
  preview.style.height = `${bh * V.zoom}px`;
  preview.style.transform = `translate(${V.tx}px, ${V.ty}px)`;
  preview.classList.toggle("px", V.zoom * (window.devicePixelRatio || 1) > 2.2);
  $("#zoomLbl").textContent = `${Math.round(V.zoom * 100)}%`;
}
function fitView() {
  const [bw, bh] = baseSize(), r = vp.getBoundingClientRect();
  if (r.width < 10 || r.height < 40) return;
  V.zoom = Math.max(0.02, Math.min((r.width - 20) / bw, (r.height - 20) / bh));
  V.tx = (r.width - bw * V.zoom) / 2; V.ty = (r.height - bh * V.zoom) / 2;
  V.fitted = true; applyView();
}
function zoomAt(factor, cx, cy) {
  const nz = clamp(V.zoom * factor, 0.05, 8), k = nz / V.zoom;
  V.tx = cx - (cx - V.tx) * k; V.ty = cy - (cy - V.ty) * k; V.zoom = nz; V.fitted = false; applyView();
}
function zoom100() {
  const r = vp.getBoundingClientRect(), [bw, bh] = baseSize();
  V.zoom = 1; V.tx = (r.width - bw) / 2; V.ty = (r.height - bh) / 2; V.fitted = false; applyView();
}
new ResizeObserver(() => requestAnimationFrame(() => { if (V.fitted) fitView(); })).observe(vp);

const ptrs = new Map();
let gesture = null;
vp.addEventListener("pointerdown", (e) => {
  vp.setPointerCapture(e.pointerId);
  ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (ptrs.size === 1) gesture = { moved: 0, t: performance.now(), shift: e.shiftKey, x0: e.clientX, y0: e.clientY };
  if (ptrs.size === 2) { const [a, b] = [...ptrs.values()]; gesture = { pinch: true, d: Math.hypot(a.x - b.x, a.y - b.y), moved: 99 }; }
  vp.classList.add("drag");
});
vp.addEventListener("pointermove", (e) => {
  const p = ptrs.get(e.pointerId);
  if (!p || !gesture) return;
  const dx = e.clientX - p.x, dy = e.clientY - p.y;
  if (gesture.pinch && ptrs.size === 2) {
    const other = [...ptrs.entries()].find(([id]) => id !== e.pointerId)[1];
    const prevD = Math.hypot(p.x - other.x, p.y - other.y), nd = Math.hypot(e.clientX - other.x, e.clientY - other.y);
    const r = vp.getBoundingClientRect();
    zoomAt(nd / (prevD || 1), (e.clientX + other.x) / 2 - r.left, (e.clientY + other.y) / 2 - r.top);
    V.tx += dx / 2; V.ty += dy / 2; applyView();
  } else if (ptrs.size === 1) {
    gesture.moved = Math.max(gesture.moved, Math.hypot(e.clientX - gesture.x0, e.clientY - gesture.y0));
    V.tx += dx; V.ty += dy; V.fitted = false; applyView();
  }
  p.x = e.clientX; p.y = e.clientY;
});
const endPtr = (e) => {
  if (!ptrs.has(e.pointerId)) return;
  const wasSingle = ptrs.size === 1;
  ptrs.delete(e.pointerId);
  if (wasSingle && gesture && !gesture.pinch && e.type === "pointerup" && gesture.moved < 6 && performance.now() - gesture.t < 700 && (gesture.shift || textMode)) {
    relocateText(e.clientX, e.clientY);
  }
  if (!ptrs.size) { gesture = null; vp.classList.remove("drag"); }
};
vp.addEventListener("pointerup", endPtr);
vp.addEventListener("pointercancel", endPtr);
vp.addEventListener("wheel", (e) => {
  e.preventDefault();
  const r = vp.getBoundingClientRect();
  zoomAt(Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0016)), e.clientX - r.left, e.clientY - r.top);
}, { passive: false });
vp.addEventListener("dblclick", () => { if (!textMode) V.fitted ? zoom100() : fitView(); });

let textMode = false;
function setTextMode(on) {
  textMode = on;
  $("#btnTextMode").setAttribute("aria-pressed", String(on));
  vp.classList.toggle("place", on);
  if (on) toast(T("Тапните по листу — подпись переедет туда", "Tap the sheet — the caption moves there"), "ok", 1800);
}
function relocateText(cx, cy) {
  const r = preview.getBoundingClientRect();
  const nx = (cx - r.left) / r.width, ny = (cy - r.top) / r.height;
  if (nx < 0 || nx > 1 || ny < 0 || ny > 1) return;
  flushCommit();
  const st = page(), y = ny * 100;
  st.txt_x = clamp(Math.round(nx * 100), 2, 85);
  if (Math.abs(y - st.txt_y1) <= Math.abs(y - st.txt_y2)) st.txt_y1 = clamp(Math.round(y), 2, 50);
  else st.txt_y2 = clamp(Math.round(y), 30, 95);
  syncUI(); commit(); requestRender();
}

// ---------------------------------------------------------------- фото страницы и кадрирование
const srcCv = $("#srcCanvas");
function drawSrc() {
  const st = page(), src = srcFor(st), wrap = $("#srcWrap");
  $("#srcEmpty").hidden = !!src;
  srcCv.hidden = !src;
  $("#srcInfo").textContent = src ? `${src.canvas.width}×${src.canvas.height} px` : "";
  if (!src) { wrap.style.minHeight = "140px"; return; }
  const iw = src.canvas.width, ih = src.canvas.height;
  const maxW = Math.max(120, wrap.clientWidth || 240), maxH = TOUCH ? 220 : 280;
  const k = Math.min(maxW / iw, maxH / ih), cw = Math.round(iw * k), ch = Math.round(ih * k), dpr = Math.min(2, window.devicePixelRatio || 1);
  srcCv.style.width = `${cw}px`; srcCv.style.height = `${ch}px`;
  if (srcCv.width !== Math.round(cw * dpr)) { srcCv.width = Math.round(cw * dpr); srcCv.height = Math.round(ch * dpr); }
  const c = srcCv.getContext("2d");
  c.imageSmoothingQuality = "high";
  c.drawImage(src.canvas, 0, 0, srcCv.width, srcCv.height);
  const cr = dragCrop || st.crop, full = cr[0] <= 0 && cr[1] <= 0 && cr[2] >= 1 && cr[3] >= 1;
  if (!full) {
    const [x1, y1, x2, y2] = [Math.min(cr[0], cr[2]), Math.min(cr[1], cr[3]), Math.max(cr[0], cr[2]), Math.max(cr[1], cr[3])];
    const W = srcCv.width, Hh = srcCv.height;
    c.fillStyle = "rgba(0,0,0,.6)";
    c.fillRect(0, 0, W, y1 * Hh); c.fillRect(0, y2 * Hh, W, Hh - y2 * Hh);
    c.fillRect(0, y1 * Hh, x1 * W, (y2 - y1) * Hh); c.fillRect(x2 * W, y1 * Hh, W - x2 * W, (y2 - y1) * Hh);
    c.strokeStyle = "#d6ff00"; c.lineWidth = 2 * dpr; c.strokeRect(x1 * W, y1 * Hh, (x2 - x1) * W, (y2 - y1) * Hh);
  }
}
let dragCrop = null, cropStart = null;
srcCv.addEventListener("pointerdown", (e) => {
  if (!srcFor(page())) return;
  srcCv.setPointerCapture(e.pointerId);
  const r = srcCv.getBoundingClientRect();
  cropStart = [clamp((e.clientX - r.left) / r.width, 0, 1), clamp((e.clientY - r.top) / r.height, 0, 1)];
  dragCrop = [...cropStart, ...cropStart];
});
srcCv.addEventListener("pointermove", (e) => {
  if (!cropStart) return;
  const r = srcCv.getBoundingClientRect();
  dragCrop = [cropStart[0], cropStart[1], clamp((e.clientX - r.left) / r.width, 0, 1), clamp((e.clientY - r.top) / r.height, 0, 1)];
  drawSrc();
});
const endCrop = () => {
  if (!cropStart) return;
  const c = dragCrop; cropStart = null; dragCrop = null;
  if (!c || Math.abs(c[2] - c[0]) < 0.04 || Math.abs(c[3] - c[1]) < 0.04) { drawSrc(); return; }
  flushCommit();
  page().crop = [Math.min(c[0], c[2]), Math.min(c[1], c[3]), Math.max(c[0], c[2]), Math.max(c[1], c[3])].map((v) => +v.toFixed(4));
  drawSrc(); commit(); requestRender();
};
srcCv.addEventListener("pointerup", endCrop);
srcCv.addEventListener("pointercancel", () => { cropStart = null; dragCrop = null; drawSrc(); });
function resetCrop() {
  flushCommit();
  page().crop = [0, 0, 1, 1];
  drawSrc(); commit(); requestRender();
}
srcCv.addEventListener("dblclick", resetCrop);
$("#btnCropReset").addEventListener("click", resetCrop);

// ---------------------------------------------------------------- загрузка фото
async function decodeFile(file) {
  let bmp;
  try { bmp = await createImageBitmap(file); } catch {
    const url = URL.createObjectURL(file);
    try { const img = new Image(); img.src = url; await img.decode(); bmp = img; } finally { setTimeout(() => URL.revokeObjectURL(url), 2000); }
  }
  const w = bmp.width || bmp.naturalWidth, h = bmp.height || bmp.naturalHeight;
  if (!w || !h) throw new Error("empty image");
  const k = Math.min(1, MAX_SIDE / Math.max(w, h));
  const cv = E.makeCanvas(Math.round(w * k), Math.round(h * k)), c = cv.getContext("2d", { willReadFrequently: true });
  c.fillStyle = "#fff"; c.fillRect(0, 0, cv.width, cv.height);
  c.imageSmoothingQuality = "high";
  c.drawImage(bmp, 0, 0, cv.width, cv.height);
  if (bmp.close) bmp.close();
  return cv;
}
const isImageFile = (f) => f.type.startsWith("image/") || /\.(jpe?g|png|webp|gif|bmp|avif|tiff?)$/i.test(f.name);

async function addPhotos(files) {
  const list = [...files].filter(isImageFile);
  if (!list.length) { toast(T("Это не картинка. Нужны JPG, PNG, WebP…", "That is not an image. Use JPG, PNG, WebP…"), "err"); return; }
  flushCommit();
  setBusy(true, T("Загружаю фото…", "Loading photos…"));
  const loaded = [], failed = [];
  for (const f of list) {
    try { loaded.push([f, await decodeFile(f)]); } catch (e) { console.warn(f.name, e); failed.push(f.name); }
  }
  setBusy(false);
  if (!loaded.length) {
    toast(T("Не удалось открыть файл. Если это HEIC — сохраните его как JPEG.", "Could not open the file. If it is HEIC, export it as JPEG."), "err");
    return;
  }
  loaded.forEach(([f, cv], i) => {
    const key = newKey();
    S.images.set(key, { canvas: cv });
    if (i === 0) { const st = page(); st.img = key; st.crop = [0, 0, 1, 1]; if (!S.dirty && S.pages.length === 1) S.name = baseName(f.name) || "zine"; }
    else { const st = clone(page()); Object.assign(st, { img: key, crop: [0, 0, 1, 1], seed: newSeed() }); S.pages.splice(S.cur + i, 0, st); }
  });
  commit();
  afterPageSwitch();
  const n = loaded.length;
  toast((n === 1 ? T(`Фото загружено: ${loaded[0][0].name}`, `Photo loaded: ${loaded[0][0].name}`) : T(`Загружено фото: ${n} (добавлено страниц: ${n - 1})`, `Loaded ${n} photos (${n - 1} pages added)`)) +
    (failed.length ? T(` · не открылись: ${failed.length}`, ` · failed: ${failed.length}`) : ""), failed.length ? "err" : "ok");
}

function transformPhoto(kind) {
  const st = page(), src = srcFor(st);
  if (!src) { toast(T("Сначала загрузите фото", "Add a photo first"), "err"); return; }
  flushCommit();
  const { width: w, height: h } = src.canvas, swap = kind !== "flip";
  const cv = E.makeCanvas(swap ? h : w, swap ? w : h), c = cv.getContext("2d", { willReadFrequently: true });
  c.translate(cv.width / 2, cv.height / 2);
  if (kind === "rotL") c.rotate(-Math.PI / 2); else if (kind === "rotR") c.rotate(Math.PI / 2); else c.scale(-1, 1);
  c.drawImage(src.canvas, -w / 2, -h / 2);
  const key = newKey();
  S.images.set(key, { canvas: cv });
  st.img = key; st.crop = [0, 0, 1, 1];
  commit(); drawSrc(); requestRender();
}

// ---------------------------------------------------------------- страницы
function afterPageSwitch({ refit = true } = {}) {
  syncUI(); drawSrc(); renderStrip(); resetPresetLabel();
  if (refit) fitView(); else applyView();
  requestRender(); updateUndoButtons();
}
function gotoPage(i) {
  if (i === S.cur || i < 0 || i >= S.pages.length) return;
  flushCommit(); S.cur = i; afterPageSwitch();
}
function addPage() {
  flushCommit();
  const q = pick(CFG.MANIFESTOS), st = clone(page());
  Object.assign(st, { img: null, crop: [0, 0, 1, 1], seed: newSeed(), txt_top: q.top, txt_bottom: q.bottom });
  S.pages.splice(S.cur + 1, 0, st); S.cur++;
  commit(); afterPageSwitch();
  toast(T(`Добавлена страница ${S.cur + 1} — загрузите для неё фото`, `Page ${S.cur + 1} added — load a photo for it`));
}
function duplicatePage() {
  flushCommit();
  const st = clone(page()); st.seed = newSeed();
  S.pages.splice(S.cur + 1, 0, st); S.cur++;
  commit(); afterPageSwitch();
}
function movePage(d) {
  const j = S.cur + d;
  if (j < 0 || j >= S.pages.length) return;
  flushCommit();
  [S.pages[S.cur], S.pages[j]] = [S.pages[j], S.pages[S.cur]]; S.cur = j;
  commit(); renderStrip();
}
function deletePage() {
  if (S.pages.length < 2) { toast(T("Нельзя удалить единственную страницу", "Can't delete the only page"), "err"); return; }
  flushCommit();
  S.pages.splice(S.cur, 1); S.cur = Math.min(S.cur, S.pages.length - 1);
  commit(); afterPageSwitch();
}

// ---------------------------------------------------------------- манифесты
const userManifests = () => ls.get("zine.manifestos", []);
const allManifests = () => [...CFG.MANIFESTOS.map((m) => ({ ...m })), ...userManifests().map((m) => ({ lang: "user", cat: "Мои", top: m.top, bottom: m.bottom }))];
const M = { items: [], shown: [], sel: -1 };
const mDlg = $("#dlgManifest");

function openManifest() {
  M.items = allManifests();
  const cats = [...new Set(M.items.map((m) => m.cat).filter(Boolean))];
  const cs = $("#mCat");
  cs.textContent = "";
  cs.append(new Option(T("Все категории", "All categories"), ""));
  for (const c of cats) cs.append(new Option(c === "Мои" ? lbl(c, c) : c, c));
  if (!mDlg.open) { TOUCH || innerWidth <= 860 ? mDlg.showModal() : mDlg.show(); }
  filterManifests();
  $("#mQuery").focus();
}
function filterManifests() {
  const cat = $("#mCat").value, q = $("#mQuery").value.trim().toLowerCase();
  M.shown = M.items.filter((m) => (!cat || m.cat === cat) && (!q || `${m.top} ${m.bottom}`.toLowerCase().includes(q)));
  const ul = $("#mList");
  ul.textContent = "";
  M.shown.forEach((m, i) => {
    const li = document.createElement("li");
    li.setAttribute("role", "option"); li.setAttribute("aria-selected", "false");
    li.innerHTML = `<small></small><span></span>`;
    $("small", li).textContent = m.cat === "Мои" ? lbl(m.cat, m.cat) : m.cat;
    $("span", li).textContent = `${m.top.replace(/\n/g, " ")} / ${m.bottom.replace(/\n/g, " ")}`;
    li.addEventListener("click", () => selectManifest(i));
    li.addEventListener("dblclick", () => { selectManifest(i); applyManifest(); });
    ul.append(li);
  });
  $("#mCount").textContent = T(`${M.shown.length} из ${M.items.length}`, `${M.shown.length} of ${M.items.length}`);
  selectManifest(M.shown.length ? 0 : -1);
}
function selectManifest(i) {
  M.sel = i;
  $$("#mList li").forEach((li, j) => li.setAttribute("aria-selected", String(j === i)));
  const m = M.shown[i];
  $("#mPrev").textContent = m ? `${m.top}\n— — —\n${m.bottom}` : T("Ничего не найдено", "Nothing found");
  $("#mPrevCat").textContent = m ? (m.cat === "Мои" ? lbl(m.cat, m.cat) : m.cat) : "";
  $("#mDelete").hidden = !(m && m.lang === "user");
  const li = $$("#mList li")[i];
  if (li) li.scrollIntoView({ block: "nearest" });
}
function setQuote(st, m) { st.txt_top = m.top; st.txt_bottom = m.bottom; }
function applyManifest() {
  const m = M.shown[M.sel];
  if (!m) return;
  flushCommit(); setQuote(page(), m); syncUI(); commit(); requestRender();
  toast(T("Манифест применён", "Manifesto applied"), "ok", 1000);
}
function spreadManifests() {
  if (M.sel < 0) return;
  flushCommit();
  S.pages.forEach((st, i) => setQuote(st, M.shown[(M.sel + i) % M.shown.length]));
  syncUI(); commit(); renderStrip(); requestRender();
  toast(T(`Манифесты розданы по страницам: ${S.pages.length}`, `Manifestos spread across ${S.pages.length} page(s)`));
}
function randomQuote() {
  flushCommit(); setQuote(page(), pick(CFG.MANIFESTOS.concat(userManifests().map((m) => ({ ...m }))))); syncUI(); commit(); requestRender();
}
function saveMyManifesto() {
  const st = page(), top = (st.txt_top || "").trim(), bottom = (st.txt_bottom || "").trim();
  if (!top && !bottom) { toast(T("На странице нет текста", "The page has no caption"), "err"); return; }
  const u = userManifests();
  if (u.some((m) => m.top === top && m.bottom === bottom)) { toast(T("Такой манифест уже есть среди ваших", "Already in your manifestos")); return; }
  u.push({ top, bottom }); ls.set("zine.manifestos", u);
  toast(T("★ Сохранено в «Мои»", "★ Saved to Mine"));
}
function deleteMyManifesto() {
  const m = M.shown[M.sel];
  if (!m || m.lang !== "user") return;
  ls.set("zine.manifestos", userManifests().filter((x) => !(x.top === m.top && x.bottom === m.bottom)));
  M.items = allManifests(); filterManifests();
}
$("#mCat").addEventListener("change", filterManifests);
$("#mQuery").addEventListener("input", filterManifests);
$("#mApply").addEventListener("click", applyManifest);
$("#mSpread").addEventListener("click", spreadManifests);
$("#mRandom").addEventListener("click", () => { if (M.shown.length) { selectManifest(rnd(0, M.shown.length - 1)); applyManifest(); } });
$("#mDelete").addEventListener("click", deleteMyManifesto);
$("#mWrite").addEventListener("click", () => { const f = $("#mNew"); f.hidden = !f.hidden; if (!f.hidden) $("#mNewTop").focus(); });
$("#mNewCancel").addEventListener("click", () => { $("#mNew").hidden = true; });
$("#mNewSave").addEventListener("click", () => {
  const top = $("#mNewTop").value.trim().toUpperCase(), bottom = $("#mNewBottom").value.trim().toUpperCase();
  if (!top || !bottom) { toast(T("Заполните обе строки", "Fill in both lines"), "err"); return; }
  const u = userManifests();
  if (!u.some((m) => m.top === top && m.bottom === bottom)) { u.push({ top, bottom }); ls.set("zine.manifestos", u); }
  $("#mNewTop").value = ""; $("#mNewBottom").value = ""; $("#mNew").hidden = true;
  $("#mQuery").value = ""; openManifest(); $("#mCat").value = "Мои"; filterManifests(); selectManifest(M.shown.length - 1);
  toast(T("★ Сохранено в «Мои»", "★ Saved to Mine"));
});
$("#mList").addEventListener("keydown", (e) => {
  if (e.key === "ArrowDown") { e.preventDefault(); selectManifest(Math.min(M.shown.length - 1, M.sel + 1)); }
  if (e.key === "ArrowUp") { e.preventDefault(); selectManifest(Math.max(0, M.sel - 1)); }
  if (e.key === "Enter") applyManifest();
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && mDlg.open) mDlg.close(); });

// ---------------------------------------------------------------- Remix
function remix() {
  flushCommit();
  const st = page(), q = pick(CFG.MANIFESTOS);
  setQuote(st, q);
  Object.assign(st, {
    palette: pick(Object.keys(CFG.RISO_PALETTES)), layout: pick(CFG.LAYOUTS)[1], rows: rnd(4, 8), dot_size: rnd(5, 12),
    tilt: +(Math.random() * 2.5).toFixed(1), loss: rnd(10, 60), tstyle: pick(CFG.TEXT_STYLES)[1], font: pick(Object.keys(CFG.FONTS)), seed: newSeed(),
  });
  syncUI(); resetPresetLabel(); commit(); requestRender();
  toast(T("🎲 Новый стиль", "🎲 New style"), "ok", 1000);
}

// ---------------------------------------------------------------- проект .zine
function buildManifest() {
  const used = [...new Set(S.pages.map((p) => p.img).filter((k) => k && S.images.has(k)))].sort();
  return { version: 2, pages: S.pages, cur: S.cur, images: used };
}
async function pngOf(key) {
  if (S.blobs.has(key)) return S.blobs.get(key);
  const blob = await IO.canvasToBlob(S.images.get(key).canvas);
  S.blobs.set(key, blob);
  return blob;
}

async function saveProject(asNew = false) {
  flushCommit();
  let sink;
  if (!asNew && S.handle) sink = { name: S.handle.name, handle: S.handle, write: async (b) => { const w = await S.handle.createWritable(); await w.write(b); await w.close(); } };
  else { sink = await askSave(`${S.name || "zine"}.zine`, { mime: "application/zip", ext: ".zine", desc: "Xerox Zine Studio" }); if (!sink) return; }
  try {
    await runJob(T("Сохранение проекта", "Saving project"), async (progress) => {
      const man = buildManifest(), entries = [{ name: "manifest.json", data: IO.textToU8(JSON.stringify(man, null, 2)) }];
      for (let i = 0; i < man.images.length; i++) {
        await progress(T(`Упаковываю фото ${i + 1} из ${man.images.length}…`, `Packing photo ${i + 1} of ${man.images.length}…`), i / (man.images.length + 1));
        entries.push({ name: `images/${man.images[i]}.png`, data: await IO.blobToU8(await pngOf(man.images[i])) });
      }
      await progress(T("Запись файла…", "Writing file…"), 0.95);
      await sink.write(new Blob([IO.writeZip(entries)], { type: "application/zip" }));
    });
  } catch (e) {
    if (e instanceof Cancelled) return;
    console.error(e); toast(T("Не удалось сохранить проект: ", "Could not save the project: ") + (e.message || e), "err"); return;
  }
  S.handle = sink.handle || null;
  if (sink.name) S.name = baseName(sink.name);
  markClean(); clearAutosave();
  toast(T(`✓ Проект сохранён: ${sink.name}`, `✓ Project saved: ${sink.name}`));
}

async function loadProjectBuffer(buf) {
  const files = await IO.readZip(buf);
  if (!files.has("manifest.json")) throw new Error(T("это не проект .zine (нет manifest.json)", "not a .zine project (no manifest.json)"));
  const man = JSON.parse(IO.u8ToText(files.get("manifest.json")));
  if (!Array.isArray(man.pages) || !man.pages.length || !man.pages.every((p) => p && typeof p === "object")) throw new Error(T("в проекте нет страниц", "the project has no pages"));
  const images = new Map(), blobs = new Map();
  const decodePng = async (u8) => {
    const blob = new Blob([u8], { type: "image/png" });
    const bmp = await createImageBitmap(blob);
    const cv = E.makeCanvas(bmp.width, bmp.height);
    cv.getContext("2d", { willReadFrequently: true }).drawImage(bmp, 0, 0);
    bmp.close && bmp.close();
    return { canvas: cv, blob };
  };
  for (const [name, data] of files) {
    if (name.startsWith("images/") && name.endsWith(".png")) {
      try { const r = await decodePng(data); const key = name.slice(7, -4); images.set(key, { canvas: r.canvas }); blobs.set(key, r.blob); } catch (e) { console.warn("фото в проекте не открылось", name, e); }
    }
  }
  if (files.has("source.png")) { // проекты первой версии: одно фото на все страницы
    try { const r = await decodePng(files.get("source.png")); images.set("legacy", { canvas: r.canvas }); blobs.set("legacy", r.blob); man.pages.forEach((p) => { if (!p.img) p.img = "legacy"; }); } catch { /* ignore */ }
  }
  return { man, images, blobs };
}
function installProject({ man, images, blobs }, name, handle = null) {
  S.images = images; S.blobs = blobs; S.counter = 0;
  S.pages = man.pages.map(normalizePage);
  S.cur = clamp(Number.isInteger(man.cur) ? man.cur : 0, 0, S.pages.length - 1);
  S.name = name || "zine"; S.handle = handle;
  thumbCache.clear(); resetHistory(); afterPageSwitch(); markClean();
}

async function openProjectFile(file, handle = null) {
  if (S.dirty && !(await confirmDlg({ title: T("Открыть проект?", "Open project?"), msg: T("Несохранённые изменения будут потеряны.", "Unsaved changes will be lost."), ok: T("Открыть", "Open") }))) return;
  try {
    setBusy(true, T("Открываю проект…", "Opening project…"));
    const proj = await loadProjectBuffer(await file.arrayBuffer());
    installProject(proj, baseName(file.name), handle);
    clearAutosave();
    toast(T(`✓ Открыт проект: ${file.name} (страниц: ${S.pages.length})`, `✓ Opened ${file.name} (${S.pages.length} page(s))`));
  } catch (e) {
    console.error(e); toast(T("Не удалось открыть проект: ", "Could not open the project: ") + (e.message || e), "err");
  } finally { setBusy(false); }
}
async function openProjectDialog() {
  if (typeof window.showOpenFilePicker === "function" && !TOUCH) {
    try {
      const [h] = await window.showOpenFilePicker({ types: [{ description: "Xerox Zine Studio", accept: { "application/zip": [".zine", ".zip"] } }] });
      return openProjectFile(await h.getFile(), h);
    } catch (e) { if (e && e.name === "AbortError") return; }
  }
  $("#fileProj").click();
}

async function newProject() {
  if (S.dirty && !(await confirmDlg({ title: T("Новый проект?", "New project?"), msg: T("Несохранённые изменения будут потеряны.", "Unsaved changes will be lost."), ok: T("Создать", "Create") }))) return;
  S.images = new Map(); S.blobs = new Map(); S.counter = 0; S.pages = [freshPage()]; S.cur = 0; S.name = "zine"; S.handle = null;
  thumbCache.clear(); resetHistory(); afterPageSwitch(); markClean(); clearAutosave();
}

// ---------------------------------------------------------------- автосохранение и восстановление
const autosaveSoon = debounce(doAutosave, 2500);
let autosaveWarned = false;
const storedKeys = new Set();
async function doAutosave() {
  if (!S.dirty) return;
  try {
    const man = buildManifest();
    for (const k of man.images) {
      if (storedKeys.has(k)) continue;
      await idb.set(`img:${k}`, await pngOf(k)); storedKeys.add(k);
    }
    await idb.set("autosave", { man, name: S.name, at: Date.now() });
  } catch (e) {
    if (!autosaveWarned) { autosaveWarned = true; console.warn("автосохранение недоступно", e); toast(T("Автосохранение недоступно в этом браузере — сохраняйте проект в файл", "Autosave is unavailable in this browser — save the project to a file"), "err"); }
  }
}
async function clearAutosave() {
  autosaveSoon.cancel();
  try { for (const k of await idb.keys()) await idb.del(k); } catch { /* ignore */ }
  storedKeys.clear();
}
async function offerRestore() {
  let a;
  try { a = await idb.get("autosave"); } catch { return false; }
  if (!a || !a.man || !Array.isArray(a.man.pages)) return false;
  const when = new Date(a.at).toLocaleString(LANG === "ru" ? "ru-RU" : "en-GB");
  $("#restoreMsg").textContent = T(`Найден несохранённый проект (${when}). Восстановить?`, `Found an unsaved project (${when}). Restore it?`);
  $("#restoreYes").textContent = T("Восстановить", "Restore");
  $("#restoreNo").textContent = T("Начать заново", "Start fresh");
  $("#restore").hidden = false;
  $("#restoreYes").onclick = async () => {
    $("#restore").hidden = true;
    try {
      const images = new Map(), blobs = new Map();
      for (const k of a.man.images || []) {
        const blob = await idb.get(`img:${k}`);
        if (!blob) continue;
        const bmp = await createImageBitmap(blob), cv = E.makeCanvas(bmp.width, bmp.height);
        cv.getContext("2d", { willReadFrequently: true }).drawImage(bmp, 0, 0); bmp.close && bmp.close();
        images.set(k, { canvas: cv }); blobs.set(k, blob); storedKeys.add(k);
      }
      installProject({ man: a.man, images, blobs }, a.name);
      markDirty();
      toast(T("✓ Проект восстановлен", "✓ Project restored"));
    } catch (e) { console.error(e); toast(T("Не удалось восстановить проект", "Could not restore the project"), "err"); }
  };
  $("#restoreNo").onclick = async () => { $("#restore").hidden = true; await clearAutosave(); };
  return true;
}
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") { flushCommit(); autosaveSoon.flush(); } });

// ---------------------------------------------------------------- экспорт
const scaleSel = $("#expScale");
scaleSel.value = ls.get("zine.scale", "2");
scaleSel.addEventListener("change", () => ls.set("zine.scale", scaleSel.value));
const exportScale = () => Number(scaleSel.value) || 2;
const pageName = (i, n = S.pages.length) => `${S.name || "zine"}_page_${pad(i + 1, Math.max(2, String(n).length))}`;
const render = (i, opts) => E.renderPage(srcFor(S.pages[i]), S.pages[i], opts);
const pngU8 = async (canvas) => IO.pngSetDpi(await IO.blobToU8(await IO.canvasToBlob(canvas)), 300);
const memHint = (e) => (/memory|alloc|canvas/i.test(String(e && e.message)) ? T(" Не хватило памяти — попробуйте масштаб поменьше.", " Out of memory — try a lower scale.") : "");

async function job(title, fn, okMsg) {
  try {
    const r = await runJob(title, fn);
    if (okMsg) toast(typeof okMsg === "function" ? okMsg(r) : okMsg);
  } catch (e) {
    if (e instanceof Cancelled) { toast(T("Отменено", "Cancelled"), "ok", 1200); return; }
    console.error(e); toast(T("Ошибка экспорта: ", "Export failed: ") + (e.message || e) + memHint(e), "err");
  }
}

async function exportPng() {
  flushCommit();
  const sink = await askSave(`${pageName(S.cur)}.png`, { mime: "image/png", ext: ".png", desc: "PNG" });
  if (!sink) return;
  await job(T("Экспорт PNG", "Export PNG"), async (progress) => {
    await progress(T("Рендеринг…", "Rendering…"), 0.2);
    const r = await render(S.cur, { scale: exportScale() });
    await progress(T("Кодирование…", "Encoding…"), 0.8);
    await sink.write(new Blob([await pngU8(r.canvas)], { type: "image/png" }));
  }, T(`✓ Сохранено: ${sink.name}`, `✓ Saved: ${sink.name}`));
}
async function pageBlob() {
  flushCommit();
  const r = await render(S.cur, { scale: exportScale() });
  return new Blob([await pngU8(r.canvas)], { type: "image/png" });
}
const CAN_SHARE = () => !!(navigator.canShare && navigator.share && navigator.canShare({ files: [new File([new Blob([""])], "a.png", { type: "image/png" })] }));
const CAN_COPY = () => !!(navigator.clipboard && navigator.clipboard.write && window.ClipboardItem);
async function sharePage() {
  try {
    toast(T("Подготовка…", "Preparing…"), "ok", 1500);
    const file = new File([await pageBlob()], `${pageName(S.cur)}.png`, { type: "image/png" });
    await navigator.share({ files: [file], title: "Xerox Zine Studio" });
  } catch (e) { if (!e || e.name !== "AbortError") toast(T("Не удалось поделиться", "Could not share"), "err"); }
}
async function copyPage() {
  try {
    toast(T("Копирование…", "Copying…"), "ok", 1500);
    const blob = await pageBlob();
    await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
    toast(T("✓ Страница скопирована в буфер", "✓ Page copied to clipboard"));
  } catch (e) { toast(T("Браузер не дал доступ к буферу обмена", "The browser blocked clipboard access"), "err"); }
}
async function exportAllPng() {
  flushCommit();
  const sink = await askSave(`${S.name || "zine"}_pages.zip`, { mime: "application/zip", ext: ".zip", desc: "ZIP" });
  if (!sink) return;
  const n = S.pages.length, scale = exportScale();
  await job(T("Экспорт всех страниц", "Export all pages"), async (progress) => {
    const entries = [];
    for (let i = 0; i < n; i++) {
      await progress(T(`Страница ${i + 1} из ${n}…`, `Page ${i + 1} of ${n}…`), i / (n + 1));
      const r = await render(i, { scale });
      entries.push({ name: `${pageName(i, n)}.png`, data: await pngU8(r.canvas) });
    }
    await sink.write(new Blob([IO.writeZip(entries)], { type: "application/zip" }));
  }, T(`✓ Сохранено страниц: ${n}`, `✓ Saved ${n} page(s)`));
}
async function exportStencil() {
  flushCommit();
  const sink = await askSave(`${pageName(S.cur)}_stencil.png`, { mime: "image/png", ext: ".png", desc: "PNG 1-bit" });
  if (!sink) return;
  await job(T("1-bit трафарет", "1-bit stencil"), async (progress) => {
    await progress(T("Рендеринг…", "Rendering…"), 0.3);
    const r = await render(S.cur, { scale: exportScale() });
    await sink.write(await IO.encodePng1(r.bits, r.width, r.height, 300));
  }, T("✓ Трафарет сохранён (чёрно-белый PNG, 1 бит)", "✓ Stencil saved (1-bit black & white PNG)"));
}
async function exportPdf() {
  flushCommit();
  const sink = await askSave(`${S.name || "zine"}_book.pdf`, { mime: "application/pdf", ext: ".pdf", desc: "PDF" });
  if (!sink) return;
  const n = S.pages.length, scale = exportScale();
  await job(T("Экспорт книги в PDF", "Export book as PDF"), async (progress) => {
    async function* pages() {
      for (let i = 0; i < n; i++) {
        await progress(T(`Рендеринг страницы ${i + 1} из ${n}…`, `Rendering page ${i + 1} of ${n}…`), i / (n + 1));
        const r = await render(i, { scale });
        yield r.canvas.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, r.width, r.height);
      }
    }
    const blob = await IO.buildPdf(pages(), 300);
    await progress(T("Запись файла…", "Writing file…"), 0.97);
    await sink.write(blob);
  }, T(`✓ PDF готов (страниц: ${n})`, `✓ PDF ready (${n} page(s))`));
}
async function exportPdfA4() {
  flushCommit();
  const sink = await askSave(`${S.name || "zine"}_book_A4.pdf`, { mime: "application/pdf", ext: ".pdf", desc: "PDF A4" });
  if (!sink) return;
  const n = S.pages.length, AW = 2480, AH = 3508, M = 118; // A4 при 300 DPI, поля 10 мм
  await job(T("PDF для печати (A4)", "Print PDF (A4)"), async (progress) => {
    async function* sheets() {
      for (let i = 0; i < n; i++) {
        await progress(T(`Рендеринг страницы ${i + 1} из ${n}…`, `Rendering page ${i + 1} of ${n}…`), i / (n + 1));
        const [bw, bh] = baseSize(S.pages[i]), k = Math.min((AW - 2 * M) / bw, (AH - 2 * M) / bh);
        const size = [Math.floor(bw * k), Math.floor(bh * k)];
        const r = await render(i, { outSize: size });
        const sheet = E.makeCanvas(AW, AH), c = sheet.getContext("2d", { willReadFrequently: true });
        c.fillStyle = "#fff"; c.fillRect(0, 0, AW, AH);
        c.drawImage(r.canvas, Math.floor((AW - size[0]) / 2), Math.floor((AH - size[1]) / 2));
        yield c.getImageData(0, 0, AW, AH);
      }
    }
    await sink.write(await IO.buildPdf(sheets(), 300));
  }, T(`✓ PDF A4 (${n} стр.) готов к печати`, `✓ A4 PDF (${n} page(s)) ready to print`));
}
async function exportMiniZine() {
  flushCommit();
  const n = S.pages.length;
  if (n !== 8) {
    const note = n < 8 ? T(`В проекте ${n} стр., а в мини-зине их 8. Недостающие будут копиями последней со случайными манифестами.`, `The project has ${n} page(s) but a mini-zine has 8. Missing ones become copies of the last page with random manifestos.`)
      : T(`В проекте ${n} стр., а в мини-зине их 8. В лист попадут первые 8.`, `The project has ${n} pages but a mini-zine has 8. The first 8 are used.`);
    if (!(await confirmDlg({ title: T("Мини-зин на 8 страниц", "8-page mini-zine"), msg: note, ok: T("Продолжить", "Continue") }))) return;
  }
  const sink = await askSave(`${S.name || "zine"}_mini_zine_A4.png`, { mime: "image/png", ext: ".png", desc: "PNG A4" });
  if (!sink) return;
  const items = S.pages.slice(0, 8).map((p) => clone(p));
  while (items.length < 8) { const st = clone(items[items.length - 1]), q = pick(CFG.MANIFESTOS); Object.assign(st, { txt_top: q.top, txt_bottom: q.bottom, seed: newSeed() }); items.push(st); }
  await job(T("Мини-зин A4", "Mini-zine A4"), async (progress) => {
    const SW = 3508, SH = 2480, cw = Math.floor(SW / 4), rh = Math.floor(SH / 2);
    const sheet = E.makeCanvas(SW, SH), c = sheet.getContext("2d");
    c.fillStyle = "#fff"; c.fillRect(0, 0, SW, SH);
    const rendered = [];
    for (let i = 0; i < 8; i++) {
      await progress(T(`Рендеринг страницы ${i + 1} из 8…`, `Rendering page ${i + 1} of 8…`), i / 9);
      rendered.push((await E.renderPage(srcFor(items[i]), items[i], { outSize: [cw, rh] })).canvas);
    }
    // классическая раскладка: верхний ряд перевёрнут 5-4-3-2, нижний 6-7-8-1
    [4, 3, 2, 1].forEach((idx, col) => {
      c.save(); c.translate(col * cw + cw / 2, rh / 2); c.rotate(Math.PI); c.drawImage(rendered[idx], -cw / 2, -rh / 2, cw, rh); c.restore();
    });
    [5, 6, 7, 0].forEach((idx, col) => c.drawImage(rendered[idx], col * cw, rh, cw, rh));
    c.strokeStyle = "rgb(160,160,160)"; c.lineWidth = 2; c.setLineDash([14, 10]);
    for (let k = 1; k < 4; k++) { c.beginPath(); c.moveTo(k * cw, 0); c.lineTo(k * cw, SH); c.stroke(); }
    c.beginPath(); c.moveTo(0, rh); c.lineTo(SW, rh); c.stroke();
    c.setLineDash([]); c.strokeStyle = "rgb(220,20,20)"; c.lineWidth = 5;
    c.beginPath(); c.moveTo(cw, rh); c.lineTo(cw * 3, rh); c.stroke(); // разрез
    await progress(T("Кодирование…", "Encoding…"), 0.95);
    await sink.write(new Blob([await pngU8(sheet)], { type: "image/png" }));
  }, T("✓ Мини-зин сохранён: сложите лист, разрежьте по красной линии", "✓ Mini-zine saved: fold the sheet and cut along the red line"));
}

// ---------------------------------------------------------------- меню «Файл», справка, о программе
function menuItems() {
  return [
    [T("Новый проект", "New project"), newProject],
    [T("Загрузить фото…", "Add photos…"), () => $("#fileImg").click(), "Ctrl+O"],
    [T("Открыть проект (.zine)…", "Open project (.zine)…"), openProjectDialog, "Ctrl+Shift+O"],
    [T("Сохранить проект (.zine)", "Save project (.zine)"), () => saveProject(false), "Ctrl+Shift+S"],
    [T("Сохранить проект как…", "Save project as…"), () => saveProject(true)],
    "hr", T("ЭКСПОРТ", "EXPORT"),
    [T("Страница в PNG", "Page as PNG"), exportPng, "Ctrl+S"],
    ...(CAN_SHARE() ? [[T("Поделиться страницей…", "Share page…"), sharePage]] : []),
    ...(CAN_COPY() ? [[T("Копировать страницу в буфер", "Copy page to clipboard"), copyPage]] : []),
    [T("Все страницы в PNG (ZIP)", "All pages as PNG (ZIP)"), exportAllPng],
    [T("1-bit трафарет (PNG)", "1-bit stencil (PNG)"), exportStencil],
    [T("Книга в PDF", "Book as PDF"), exportPdf],
    [T("PDF для печати (A4, поля 10 мм)", "Print PDF (A4, 10 mm margins)"), exportPdfA4],
    [T("Мини-зин на 8 страниц (A4)", "8-page mini-zine (A4)"), exportMiniZine],
    "hr", T("СТРАНИЦЫ И ТЕКСТ", "PAGES & TEXT"),
    [T("Применить стиль страницы ко всем", "Apply this page's style to all pages"), applyStyleToAll],
    [T("Библиотека манифестов…", "Manifesto library…"), openManifest, "Ctrl+M"],
    "hr",
    [T("Горячие клавиши", "Keyboard shortcuts"), showHelp, "F1"],
    [T("О программе и лицензии", "About & licenses"), showAbout],
  ];
}
function buildMenu() {
  const m = $("#menuFile");
  m.textContent = "";
  for (const it of menuItems()) {
    if (it === "hr") { m.append(document.createElement("hr")); continue; }
    if (typeof it === "string") { const h = document.createElement("div"); h.className = "mh"; h.textContent = it; m.append(h); continue; }
    const b = document.createElement("button");
    b.setAttribute("role", "menuitem");
    b.innerHTML = `<span></span>${it[2] && !TOUCH ? `<kbd>${it[2]}</kbd>` : ""}`;
    $("span", b).textContent = it[0];
    b.addEventListener("click", () => { closeMenu(); it[1](); });
    m.append(b);
  }
}
function closeMenu() { $("#menuFile").hidden = true; $("#btnFile").setAttribute("aria-expanded", "false"); }
$("#btnFile").addEventListener("click", (e) => {
  e.stopPropagation();
  const m = $("#menuFile"), open = m.hidden;
  m.hidden = !open;
  $("#btnFile").setAttribute("aria-expanded", String(open));
  if (open) $("button", m).focus();
});
document.addEventListener("click", (e) => { if (!e.target.closest(".menu-wrap")) closeMenu(); });
$("#menuFile").addEventListener("keydown", (e) => {
  const btns = $$("#menuFile button"), i = btns.indexOf(document.activeElement);
  if (e.key === "ArrowDown") { e.preventDefault(); btns[(i + 1) % btns.length].focus(); }
  if (e.key === "ArrowUp") { e.preventDefault(); btns[(i - 1 + btns.length) % btns.length].focus(); }
  if (e.key === "Escape") { closeMenu(); $("#btnFile").focus(); }
});

function showHelp() {
  const k = (a, b) => `<tr><td><kbd>${a}</kbd></td><td>${b}</td></tr>`;
  $("#helpBody").innerHTML = `<table>
    ${k("Ctrl+O", T("загрузить фото (можно сразу несколько — каждое станет страницей)", "add photos (several at once — each becomes a page)"))}
    ${k("Ctrl+Shift+O", T("открыть проект .zine", "open a .zine project"))}
    ${k("Ctrl+S", T("экспорт страницы в PNG", "export the page as PNG"))}
    ${k("Ctrl+Shift+S", T("сохранить проект (.zine)", "save the project (.zine)"))}
    ${k("Ctrl+Z / Ctrl+Y", T("отменить / вернуть", "undo / redo"))}
    ${k("Ctrl+M", T("библиотека манифестов", "manifesto library"))}
    ${k("Alt+R", T("Remix — случайный стиль и цитата", "Remix — random style and quote"))}
    ${k("Alt+N / Alt+D", T("новая страница / дублировать", "new page / duplicate"))}
    ${k("[ и ]", T("предыдущая / следующая страница", "previous / next page"))}
    ${k("0 / 1", T("вписать вид / масштаб 100%", "fit view / 100% zoom"))}
    ${k("Ctrl+V", T("вставить фото из буфера обмена", "paste a photo from the clipboard"))}
  </table>
  <h4>${T("В ПРЕДПРОСМОТРЕ", "IN THE PREVIEW")}</h4>
  <p>${T("Мышь — двигать, колесо — зум, двойной клик — вписать / 100%, Shift+клик — поставить подпись (ближайшую: верхнюю или нижнюю). На телефоне: один палец — двигать, два — зум, кнопка «✎ Подпись» — режим размещения подписи.", "Drag to pan, wheel to zoom, double-click toggles fit / 100%, Shift+click places the nearest caption. On a phone: one finger pans, two fingers zoom, the “✎ Caption” button turns on caption placement.")}</p>
  <h4>${T("ФОТО И ПОЛЗУНКИ", "PHOTO & SLIDERS")}</h4>
  <p>${T("Потяните по фото слева — выделить кадр, двойной клик — сбросить. Двойной клик по ползунку возвращает значение по умолчанию.", "Drag over the photo to select a frame, double-click to reset. Double-click a slider to restore its default.")}</p>
  <h4>${T("ПРОЕКТЫ", "PROJECTS")}</h4>
  <p>${T("Файл .zine полностью совместим с настольной версией. Несохранённая работа автоматически сохраняется в браузере и предлагается к восстановлению при следующем запуске.", "A .zine file is fully compatible with the desktop app. Unsaved work is autosaved in the browser and offered for restore on the next visit.")}</p>`;
  $("#dlgHelp").showModal();
}
async function showAbout() {
  $("#aboutBody").innerHTML = `<p><b>Xerox Zine Studio ${CFG.APP_VERSION}</b> · web</p>
    <p>${T("Генератор ксерокс-зинов: полутон, рваные края, потеря качества копий и ризографская палитра. Страницы собираются в PDF, мини-зин A4 и 1-bit трафарет.", "A xerox-zine generator: halftone, torn edges, generation loss and risograph palettes. Pages become a PDF, an A4 mini-zine and a 1-bit stencil.")}</p>
    <p>🔒 ${T("Всё считается в вашем браузере: фото не загружаются на сервер, аналитики и трекеров нет.", "Everything runs in your browser: photos are never uploaded, there is no analytics or tracking.")}</p>
    <p><a href="https://github.com/DmitryLeLeE/xeroxstudio" target="_blank" rel="noopener">github.com/DmitryLeLeE/xeroxstudio</a></p>
    <h4>${T("ЛИЦЕНЗИИ ТРЕТЬИХ СТОРОН", "THIRD-PARTY LICENSES")}</h4><pre id="licPre">…</pre>`;
  $("#dlgAbout").showModal();
  try { $("#licPre").textContent = await (await fetch("licenses.txt")).text(); } catch { $("#licPre").textContent = "licenses.txt"; }
}

// ---------------------------------------------------------------- клавиши, перетаскивание, вставка
document.addEventListener("keydown", (e) => {
  const mod = e.ctrlKey || e.metaKey, key = e.key.toLowerCase();
  const typing = /^(textarea|input)$/i.test(e.target.tagName) && e.target.type !== "range" && e.target.type !== "checkbox";
  if (e.key === "F1") { e.preventDefault(); showHelp(); return; }
  if (document.querySelector("dialog[open]:not(#dlgManifest)")) return;
  if (mod && key === "s") { e.preventDefault(); e.shiftKey ? saveProject(false) : exportPng(); return; }
  if (mod && key === "o") { e.preventDefault(); e.shiftKey ? openProjectDialog() : $("#fileImg").click(); return; }
  if (mod && key === "m") { e.preventDefault(); openManifest(); return; }
  if (typing) return;
  if (mod && key === "z") { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
  if (mod && key === "y") { e.preventDefault(); redo(); return; }
  if (e.altKey && key === "r") { e.preventDefault(); remix(); return; }
  if (e.altKey && key === "n") { e.preventDefault(); addPage(); return; }
  if (e.altKey && key === "d") { e.preventDefault(); duplicatePage(); return; }
  if (mod || e.altKey) return;
  if (e.key === "[") gotoPage(S.cur - 1);
  else if (e.key === "]") gotoPage(S.cur + 1);
  else if (e.key === "0") fitView();
  else if (e.key === "1") zoom100();
});

let dragDepth = 0;
const hasFiles = (e) => e.dataTransfer && [...e.dataTransfer.types].includes("Files");
window.addEventListener("dragenter", (e) => { if (hasFiles(e)) { dragDepth++; $("#dropveil").hidden = false; } });
window.addEventListener("dragleave", (e) => { if (hasFiles(e) && --dragDepth <= 0) { dragDepth = 0; $("#dropveil").hidden = true; } });
window.addEventListener("dragover", (e) => { if (hasFiles(e)) e.preventDefault(); });
window.addEventListener("drop", (e) => {
  if (!hasFiles(e)) return;
  e.preventDefault(); dragDepth = 0; $("#dropveil").hidden = true;
  const files = [...e.dataTransfer.files], proj = files.find((f) => /\.(zine|zip)$/i.test(f.name));
  if (proj) openProjectFile(proj); else addPhotos(files);
});
window.addEventListener("paste", (e) => {
  if (/^(textarea|input)$/i.test(e.target.tagName)) return;
  const files = [...(e.clipboardData ? e.clipboardData.files : [])].filter(isImageFile);
  if (files.length) { e.preventDefault(); addPhotos(files); }
});

$("#fileImg").addEventListener("change", (e) => { const f = [...e.target.files]; e.target.value = ""; if (f.length) addPhotos(f); });
$("#fileCam").addEventListener("change", (e) => { const f = [...e.target.files]; e.target.value = ""; if (f.length) addPhotos(f); });
const closeWelcome = () => { ls.set("zine.welcomed", true); const d = $("#dlgWelcome"); if (d.open) d.close(); };
$("#dlgWelcome").addEventListener("cancel", () => ls.set("zine.welcomed", true));
$("#wPhoto").addEventListener("click", () => { closeWelcome(); $("#fileImg").click(); });
$("#wCam").addEventListener("click", () => { closeWelcome(); $("#fileCam").click(); });
$("#wSample").addEventListener("click", closeWelcome);
if (!TOUCH) $("#wCam").hidden = true;
$("#btnTheme").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "paper" ? "dark" : "paper";
  document.documentElement.dataset.theme = next; ls.set("zine.theme", next);
  document.querySelector('meta[name="theme-color"]').setAttribute("content", next === "paper" ? "#f1ece0" : "#121212");
});
$("#fileProj").addEventListener("change", (e) => { const f = e.target.files[0]; e.target.value = ""; if (f) openProjectFile(f); });

// ---------------------------------------------------------------- кнопки
$("#btnPhoto").addEventListener("click", () => $("#fileImg").click());
$("#btnRotL").addEventListener("click", () => transformPhoto("rotL"));
$("#btnRotR").addEventListener("click", () => transformPhoto("rotR"));
$("#btnFlip").addEventListener("click", () => transformPhoto("flip"));
$("#btnUndo").addEventListener("click", undo);
$("#btnRedo").addEventListener("click", redo);
$("#btnRemix").addEventListener("click", remix);
$("#btnHelp").addEventListener("click", showHelp);
$("#btnFit").addEventListener("click", fitView);
$("#btn100").addEventListener("click", zoom100);
$("#btnSavePng").addEventListener("click", exportPng);
$("#btnTextMode").addEventListener("click", () => setTextMode(!textMode));
$("#pgNew").addEventListener("click", addPage);
$("#pgDup").addEventListener("click", duplicatePage);
$("#pgLeft").addEventListener("click", () => movePage(-1));
$("#pgRight").addEventListener("click", () => movePage(1));
$("#pgDel").addEventListener("click", deletePage);
$("#btnLang").addEventListener("click", () => { setLang(LANG === "ru" ? "en" : "ru"); location.reload(); });
$("#srcWrap").addEventListener("click", (e) => { if (!srcFor(page()) && e.target.closest("#srcWrap")) $("#fileImg").click(); });

const app = $("#app");
app.dataset.tab = innerWidth <= 860 ? "view" : "style"; // на телефоне сначала большой лист
$$("#tabbar button").forEach((b) => b.addEventListener("click", () => {
  const go = b.dataset.go;
  app.dataset.tab = app.dataset.tab === go && go !== "view" ? "view" : go;
  syncTabbar();
  requestAnimationFrame(() => { drawSrc(); if (V.fitted) fitView(); });
}));
const syncTabbar = () => $$("#tabbar button").forEach((x) => x.classList.toggle("on", x.dataset.go === app.dataset.tab));
syncTabbar();
new ResizeObserver(() => requestAnimationFrame(drawSrc)).observe($("#srcWrap"));

// ---------------------------------------------------------------- запуск
window.addEventListener("error", (e) => { console.error(e.error || e.message); });
window.addEventListener("unhandledrejection", (e) => { console.error(e.reason); if (!(e.reason instanceof Cancelled)) toast(T("Что-то пошло не так: ", "Something went wrong: ") + (e.reason && e.reason.message || e.reason), "err"); });

async function loadSample() {
  try {
    const blob = await (await fetch("../img/sample.jpg")).blob();
    const cv = await decodeFile(blob);
    const key = newKey();
    S.images.set(key, { canvas: cv });
    page().img = key;
    S.name = "zine";
  } catch (e) { console.warn("пример не загрузился", e); }
}

async function init() {
  applyStaticLang();
  $("#btnLang").textContent = LANG === "ru" ? "EN" : "RU";
  S.pages = [freshPage()];
  buildSettings(); buildMenu();
  const restoring = await offerRestore();
  if (!restoring) await loadSample();
  resetHistory(); markClean();
  afterPageSwitch();
  if (!restoring && srcFor(page()) && !ls.get("zine.welcomed", false) && !/[?&]shot\b/.test(location.search)) $("#dlgWelcome").showModal();
  if ("serviceWorker" in navigator && /^https:|^http:\/\/localhost/.test(location.href)) {
    navigator.serviceWorker.register("sw.js").then((reg) => {
      reg.addEventListener("updatefound", () => {
        const nw = reg.installing;
        if (nw) nw.addEventListener("statechange", () => { if (nw.state === "installed" && navigator.serviceWorker.controller) toast(T("Доступна новая версия — обновите страницу", "A new version is available — reload the page"), "ok", 6000); });
      });
    }).catch(() => {});
  }
  window.__zine = { S, E, IO, page, requestRender, commit, undo, redo, gotoPage, addPage, exportPng, remix }; // для автотестов
  window.__ready = true;
}
init();
