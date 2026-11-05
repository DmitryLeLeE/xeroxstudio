// Xerox Zine Studio — веб-версия. Всё работает в браузере, фото никуда не отправляются.
import { CFG } from "./config.js";
import * as E from "./engine.js";
import * as RC from "./render-client.js";
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
  "9:16 Stories / Обои (1080×1920)": "9:16 Stories / Wallpaper (1080×1920)", "3:4 Принт (1200×1600)": "3:4 Print (1200×1600)", "4:5 Instagram (1080×1350)": "4:5 Instagram (1080×1350)",
  staggered: "Staggered (zigzag)", column: "Column (room for text)", contact_sheet: "Contact sheet (frames)", center_hero: "Hero + copies",
  column_right: "Column on the right", diagonal: "Diagonal cascade", pile: "Pile (overlapping collage)", two_columns: "Two columns",
  mosaic: "Mosaic (one big + small)", duo: "Diptych (two large)", triptych: "Triptych (three strips)", ribbon: "Ribbon (a row of frames)", full_page: "Full page",
  halftone: "Halftone (dots)", floyd: "Floyd–Steinberg grain", stencil: "Stencil (threshold)",
  lines: "Lines (hatching)", cross: "Cross-hatch", stipple: "Stipple (random dots)", mezzo: "Mezzotint (noise)", bayer: "Bayer (ordered)",
  contain: "Fit whole photo", cover: "Fill the frame",
  white_box: "White box", dymo_tape: "Black tape (Dymo)", outline: "Outline (black, white stroke)",
  left: "Left", center: "Center", right: "Right",
  "Пользовательская (Custom)": "Custom",
  "Классический ксерокс": "Classic Xerox", "Газетная печать": "Newsprint", "Кислотный райот": "Acid Riot", "Панк-флаер": "Punk Flyer",
  "Синька (cyanotype)": "Cyanotype", "Контактный лист 35 мм": "35 mm Contact Sheet", "Ночное видение": "Night Vision", "Ризо-оверпринт": "Riso Overprint", "Склейка со скотчем": "Tape Collage",
  "Диагональ-панк": "Diagonal Punk", "Стопка снимков": "Photo Pile", "Газетная мозаика": "Newsprint Mosaic", "Триптих-синька": "Cyanotype Triptych",
  "Постер во весь лист": "Full-page Poster", "Лента кинопроб": "Film-test Ribbon", "Ризо-диптих": "Riso Diptych",
  "Линейная гравюра": "Line Engraving", "Мезотинт": "Mezzotint", "Грязный офис": "Dirty Office", "Байер 8-бит": "Bayer 8-bit",
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
    { t: "buttons", items: [[T("🧬 Мутировать вид", "🧬 Mutate look"), () => mutate()]] },
    { t: "locks" },
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
    { k: "overprint3", t: "range", label: T("Третья краска (полутона)", "Third ink (midtones)"), min: 0, max: 100, step: 1 },
    { k: "ink3", t: "color2", label: T("Цвет третьей краски", "Third ink colour") },
    { k: "overprint4", t: "range", label: T("Четвёртая краска (света)", "Fourth ink (highlights)"), min: 0, max: 100, step: 1 },
    { k: "ink4", t: "color2", label: T("Цвет четвёртой краски", "Fourth ink colour") },
  ] },
  { tab: "style", title: T("4. ПАЛИТРА (RISOGRAPH)", "4. PALETTE (RISOGRAPH)"), items: [
    { k: "palette", t: "select", label: T("Бумага / краска", "Paper / ink"),
      opts: () => [...Object.keys(CFG.RISO_PALETTES).map((k) => [k, k]), [CFG.CUSTOM_PALETTE, lbl(CFG.CUSTOM_PALETTE, CFG.CUSTOM_PALETTE)]] },
    { t: "swatches" },
    { t: "button", label: T("🎨 Палитра из фото", "🎨 Palette from photo"), act: () => paletteFromPhoto() },
    { k: "invert", t: "check", label: T("Инвертировать цвета", "Invert colors") },
  ] },
  { tab: "style", title: T("5. ИЗНОС ЛИСТА И ШТАМП", "5. SHEET WEAR & STAMP"), items: [
    { k: "fold", t: "range", label: T("Сгиб листа", "Fold crease"), min: 0, max: 100, step: 1 },
    { k: "holes", t: "check", label: T("Дырки от дырокола", "Punch holes") },
    { k: "stains", t: "range", label: T("Пятна (кофе, жир)", "Stains (coffee, grease)"), min: 0, max: 100, step: 1 },
    { k: "dust", t: "range", label: T("Пыль и волоски", "Dust & hairs"), min: 0, max: 100, step: 1 },
    { k: "stamp", t: "text", label: T("Штамп (пусто = нет)", "Stamp (empty = none)") },
    { k: "stamp_rot", t: "range", label: T("Поворот штампа (°)", "Stamp rotation (°)"), min: -45, max: 45, step: 1 },
  ] },
  { tab: "style", title: T("6. СЛОИ: СТИКЕРЫ И НАДПИСИ", "6. LAYERS: STICKERS & TEXTS"), items: [{ t: "layers" }] },
  { tab: "text", title: T("7. МАНИФЕСТЫ И ТИПОГРАФИКА", "7. MANIFESTOS & TYPOGRAPHY"), items: [
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
  } else if (it.t === "layers") {
    wrap.innerHTML = '<div class="layers-box" id="layersBox"></div>';
  } else if (it.t === "locks") {
    wrap.className = "ctl locks";
    wrap.innerHTML = `<div class="ctl-h"><span>${T("🔒 Не менять при Remix", "🔒 Keep when remixing")}</span></div><div class="chips"></div>`;
    const chips = $(".chips", wrap);
    for (const [key, ru, en] of LOCK_DEFS) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "chip"; b.textContent = T(ru, en);
      b.setAttribute("aria-pressed", String(!!LOCKS[key]));
      b.addEventListener("click", () => { LOCKS[key] = !LOCKS[key]; ls.set("zine.locks", LOCKS); b.setAttribute("aria-pressed", String(!!LOCKS[key])); });
      chips.append(b);
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
  refreshLayersUI();
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
  syncUI(); commit(); requestRender(); scanSweep();
  toast(T(`Стиль применён: ${lbl(name, name)}`, `Style applied: ${lbl(name, name)}`), "ok", 1400);
}
// ---------------------------------------------------------------- ссылка на «вид» (стиль + текст, без фото)
const LOOK_KEYS = () => [...CFG.STYLE_KEYS, "txt_top", "txt_bottom", "seed"];
const b64u = (s) => btoa(String.fromCharCode(...new TextEncoder().encode(s))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const unb64u = (t) => new TextDecoder().decode(Uint8Array.from(atob(t.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0)));
function lookUrl() {
  const st = page(), o = {};
  for (const k of LOOK_KEYS()) if (k in st) o[k] = st[k];
  return `${location.origin}${location.pathname}#look=${b64u(JSON.stringify(o))}`;
}
async function copyLookLink() {
  flushCommit();
  const url = lookUrl();
  try { await navigator.clipboard.writeText(url); toast(T("✓ Ссылка на этот вид скопирована. Фото в ней нет: его выберет тот, кто откроет.", "✓ Link to this look copied. It carries no photo: whoever opens it picks their own."), "ok", 4200); }
  catch (e) { promptDlg({ title: T("Ссылка на вид", "Link to this look"), msg: T("Скопируйте вручную:", "Copy it manually:"), ok: "OK", value: url }); }
}
function applyLookFromHash() {
  const m = /^#look=([A-Za-z0-9_-]{1,6000})$/.exec(location.hash);
  if (!m) return false;
  try {
    const src = JSON.parse(unb64u(m[1])), st = page(), allowed = new Set(LOOK_KEYS());
    for (const [k, v] of Object.entries(src)) {
      if (!allowed.has(k) || !(k in DEF)) continue;
      const d = DEF[k];
      if (typeof v !== typeof d || Array.isArray(v) !== Array.isArray(d)) continue;
      if (typeof v === "number") { if (!Number.isFinite(v) || Math.abs(v) > 1e6) continue; st[k] = k === "rows" ? Math.max(1, Math.min(12, Math.floor(v))) : v; }
      else if (typeof v === "string") st[k] = v.slice(0, 200);
      else if (Array.isArray(v)) { if (JSON.stringify(v).length < 400) st[k] = clone(v); }
      else st[k] = v;
    }
    history.replaceState(null, "", location.pathname + location.search);
    return true;
  } catch (e) { console.warn("ссылка на вид не разобрана", e); return false; }
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

function scanSweep() {
  const el = $("#scanbar"); if (!el) return;
  el.classList.remove("go"); void el.offsetWidth; el.classList.add("go");
}

// ---------------------------------------------------------------- сравнение «до/после»
const CMP = { on: false, x: 0.5, last: null };
$("#foldPrint").addEventListener("click", () => window.print());
function drawCompare() {
  if (!CMP.on || !CMP.last) return;
  const src = srcFor(page()), w = preview.width, h = preview.height;
  if (!src) return;
  const sw = src.canvas.width, sh = src.canvas.height, k = Math.max(w / sw, h / sh);
  const cx = Math.round(w * CMP.x);
  pctx.save();
  pctx.beginPath(); pctx.rect(0, 0, cx, h); pctx.clip();
  pctx.fillStyle = "#fff"; pctx.fillRect(0, 0, w, h);
  pctx.drawImage(src.canvas, (w - sw * k) / 2, (h - sh * k) / 2, sw * k, sh * k);
  pctx.restore();
  const lw = Math.max(2, Math.round(w / 300)), r = Math.max(14, Math.round(w / 40));
  pctx.fillStyle = "#fff"; pctx.fillRect(cx - lw, 0, lw * 2, h);
  pctx.fillStyle = "#141414"; pctx.fillRect(cx - lw / 2, 0, lw, h);
  pctx.beginPath(); pctx.arc(cx, h / 2, r, 0, Math.PI * 2); pctx.fillStyle = "#141414"; pctx.fill();
  pctx.strokeStyle = "#fff"; pctx.lineWidth = lw; pctx.stroke();
  pctx.fillStyle = "#fff"; pctx.font = `700 ${Math.round(r * 0.9)}px sans-serif`; pctx.textAlign = "center"; pctx.textBaseline = "middle";
  pctx.fillText("⇔", cx, h / 2 + 1);
}
function redrawCompare() { if (CMP.last) { pctx.drawImage(CMP.last, 0, 0); drawCompare(); } }
function setCompare(on) {
  CMP.on = on; $("#btnCompare").setAttribute("aria-pressed", String(on));
  if (on && !srcFor(page())) { CMP.on = false; $("#btnCompare").setAttribute("aria-pressed", "false"); toast(T("Сначала добавьте фото", "Add a photo first"), "err"); return; }
  $("#viewport").classList.toggle("cmp", CMP.on);
  redrawCompare();
}
$("#btnCompare").addEventListener("click", () => setCompare(!CMP.on));
$("#viewport").addEventListener("pointerdown", (e) => {
  if (!CMP.on) return;
  const move = (ev) => { const r = preview.getBoundingClientRect(); CMP.x = Math.min(0.98, Math.max(0.02, (ev.clientX - r.left) / r.width)); redrawCompare(); };
  e.stopImmediatePropagation(); e.preventDefault();
  $("#viewport").setPointerCapture(e.pointerId); move(e);
  const up = () => { $("#viewport").removeEventListener("pointermove", move); $("#viewport").removeEventListener("pointerup", up); $("#viewport").removeEventListener("pointercancel", up); };
  $("#viewport").addEventListener("pointermove", move); $("#viewport").addEventListener("pointerup", up); $("#viewport").addEventListener("pointercancel", up);
}, true);

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
        const res = await RC.renderPage(srcFor(st), st, { scale: previewScale(draft) });
        if (idx === S.cur) {
          if (preview.width !== res.width || preview.height !== res.height) { preview.width = res.width; preview.height = res.height; }
          pctx.drawImage(res.canvas, 0, 0);
          CMP.last = res.canvas; drawCompare();
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
          const r = await RC.renderPage(srcFor(st), st, { scale: THUMB_SCALE });
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
  updateLayerSel();
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
  } else if (ptrs.size === 1 && layerDrag) {
    gesture.moved = 99;
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

// ---------------------------------------------------------------- свободные слои
var LY = { sel: -1 }; // var: updateLayerSel может вызваться из applyView до этой строки
const layersOf = () => (page().layers = Array.isArray(page().layers) ? page().layers : []);
const layerBox = (ly) => {
  // размеры в долях ширины листа (как в движке)
  if (ly.type === "sticker") return [ly.size, ly.size];
  const lines = String(ly.text || " ").split("\n"), fpx = ly.size * 0.5, n = Math.max(...lines.map((l) => l.length), 1);
  return [n * fpx * 0.6 + 0.6 * fpx, 1.15 * fpx * lines.length + 0.6 * fpx];
};
function updateLayerSel() {
  if (!LY || !page()) return;
  const el = $("#layerSel"), ly = layersOf()[LY.sel];
  if (!ly) { el.hidden = true; return; }
  const [bw, bh] = baseSize(), pw = bw * V.zoom, ph = bh * V.zoom, [w, h] = layerBox(ly);
  el.hidden = false;
  el.style.width = `${w * pw}px`; el.style.height = `${h * pw}px`;
  el.style.transform = `translate(${V.tx + ly.x * pw - (w * pw) / 2}px, ${V.ty + ly.y * ph - (h * pw) / 2}px) rotate(${ly.rot || 0}deg)`;
}
function hitLayer(clientX, clientY) {
  const r = preview.getBoundingClientRect(), L = layersOf();
  if (!L.length) return -1;
  const X = (clientX - r.left) / r.width, Y = (clientY - r.top) / r.width, ratio = r.height / r.width;
  for (let i = L.length - 1; i >= 0; i--) {
    const ly = L[i], [w, h] = layerBox(ly), a = (-(ly.rot || 0) * Math.PI) / 180;
    const dx = X - ly.x, dy = Y - ly.y * ratio, rx = dx * Math.cos(a) - dy * Math.sin(a), ry = dx * Math.sin(a) + dy * Math.cos(a);
    if (Math.abs(rx) <= w / 2 && Math.abs(ry) <= h / 2) return i;
  }
  return -1;
}
function addLayer(proto) {
  flushCommit();
  const L = layersOf();
  L.push({ type: "text", text: "", sticker: "star", x: 0.5, y: 0.5, size: 0.2, rot: 0, color: "ink", style: "box", font: "Arial Black", ...proto });
  LY.sel = L.length - 1;
  commit(); requestRender(); refreshLayersUI();
}
function layerName(ly, i) {
  const base = ly.type === "sticker" ? `${lbl("", "")}${(CFG.STICKERS[ly.sticker] || {})[LANG === "ru" ? "ru" : "en"] || ly.sticker}` : `“${String(ly.text || "").split("\n")[0].slice(0, 22) || T("пусто", "empty")}”`;
  return `${i + 1}. ${ly.type === "sticker" ? "✦" : "Aa"} ${base}`;
}
function refreshLayersUI() {
  const box = $("#layersBox"); if (!box) return;
  const L = layersOf();
  if (LY.sel >= L.length) LY.sel = L.length - 1;
  box.textContent = "";
  const row = document.createElement("div"); row.className = "row gap";
  for (const [text, fn] of [[T("＋ Надпись", "＋ Text"), () => addLayer({ type: "text", text: T("НОВАЯ НАДПИСЬ", "NEW TEXT") })], [T("＋ Стикер…", "＋ Sticker…"), openStickers]]) {
    const b = document.createElement("button"); b.className = "btn grow"; b.textContent = text; b.addEventListener("click", fn); row.append(b);
  }
  box.append(row);
  const list = document.createElement("div"); list.className = "layers-list";
  L.forEach((ly, i) => {
    const b = document.createElement("button"); b.type = "button"; b.textContent = layerName(ly, i); b.setAttribute("aria-pressed", String(i === LY.sel));
    b.addEventListener("click", () => { LY.sel = i; refreshLayersUI(); });
    list.append(b);
  });
  if (!L.length) { const p = document.createElement("p"); p.className = "muted small"; p.textContent = T("Слоёв нет. Добавь надпись или стикер, потом таскай их по листу.", "No layers yet. Add a text or a sticker, then drag it around the sheet."); box.append(p); }
  box.append(list);
  const ly = L[LY.sel];
  if (ly) {
    const ed = document.createElement("div"); ed.className = "layer-ed";
    const upd = (fn) => { fn(); touchLayers(); };
    const mkRange = (label, min, max, step, get, set) => {
      const w = document.createElement("div"); w.className = "ctl"; const id = `ly_${Math.random().toString(36).slice(2, 7)}`;
      w.innerHTML = `<div class="ctl-h"><label for="${id}">${label}</label><output></output></div>`;
      const inp = document.createElement("input"); inp.type = "range"; inp.id = id; inp.min = min; inp.max = max; inp.step = step; inp.value = get();
      const out = $("output", w); out.textContent = Number(inp.value).toFixed(decimals(step));
      inp.addEventListener("input", () => { set(Number(inp.value)); out.textContent = Number(inp.value).toFixed(decimals(step)); resetPresetLabel(); requestRender({ draft: true }); updateLayerSel(); });
      inp.addEventListener("change", () => { commit(); requestRender(); });
      w.append(inp); return w;
    };
    const mkSelect = (label, opts, get, set) => {
      const w = document.createElement("div"); w.className = "ctl"; const id = `ly_${Math.random().toString(36).slice(2, 7)}`;
      w.innerHTML = `<div class="ctl-h"><label for="${id}">${label}</label></div>`;
      const sel = document.createElement("select"); sel.className = "sel"; sel.id = id;
      for (const [v, t] of opts) sel.append(new Option(t, v));
      sel.value = get(); sel.addEventListener("change", () => upd(() => set(sel.value)));
      w.append(sel); return w;
    };
    if (ly.type === "text") {
      const w = document.createElement("div"); w.className = "ctl";
      w.innerHTML = `<div class="ctl-h"><label>${T("Текст", "Text")}</label></div>`;
      const ta = document.createElement("textarea"); ta.rows = 2; ta.spellcheck = false; ta.value = ly.text || "";
      ta.addEventListener("input", () => { ly.text = ta.value; resetPresetLabel(); requestRender({ draft: true }); updateLayerSel(); commitSoon(); });
      ta.addEventListener("blur", () => { flushCommit(); refreshLayersUI(); });
      w.append(ta); ed.append(w);
      ed.append(mkSelect(T("Подложка", "Backing"), [["box", T("Плашка", "Box")], ["tape", T("Лента", "Tape")], ["plain", T("Без подложки", "Plain")]], () => ly.style || "box", (v) => (ly.style = v)));
      ed.append(mkSelect(T("Шрифт", "Font"), Object.keys(CFG.FONTS).map((k) => [k, k]), () => ly.font || "Arial Black", (v) => (ly.font = v)));
    }
    ed.append(mkRange(T("Размер", "Size"), 0.04, 1, 0.01, () => ly.size, (v) => (ly.size = v)));
    ed.append(mkRange(T("Поворот (°)", "Rotation (°)"), -180, 180, 1, () => ly.rot || 0, (v) => (ly.rot = v)));
    ed.append(mkSelect(T("Цвет", "Colour"), [["ink", T("Краска", "Ink")], ["paper", T("Бумага", "Paper")], ["ink2", T("Вторая краска", "Second ink")], ["ink3", T("Третья краска", "Third ink")], ["ink4", T("Четвёртая краска", "Fourth ink")]], () => ly.color || "ink", (v) => (ly.color = v)));
    const br = document.createElement("div"); br.className = "row gap";
    for (const [text, fn] of [
      [T("⧉ Копия", "⧉ Copy"), () => { const c = clone(ly); c.x = Math.min(0.95, c.x + 0.05); c.y = Math.min(0.95, c.y + 0.05); L.push(c); LY.sel = L.length - 1; }],
      [T("↑ Вперёд", "↑ Front"), () => { L.push(L.splice(LY.sel, 1)[0]); LY.sel = L.length - 1; }],
      [T("↓ Назад", "↓ Back"), () => { L.unshift(L.splice(LY.sel, 1)[0]); LY.sel = 0; }],
      [T("🗑 Удалить", "🗑 Delete"), () => { L.splice(LY.sel, 1); LY.sel = L.length - 1; }],
    ]) { const b = document.createElement("button"); b.className = "btn grow"; b.textContent = text; b.addEventListener("click", () => { flushCommit(); fn(); touchLayers(); }); br.append(b); }
    ed.append(br); box.append(ed);
  }
  updateLayerSel();
}
function touchLayers() { resetPresetLabel(); commit(); requestRender(); refreshLayersUI(); }
function openStickers() {
  const grid = $("#stickerGrid");
  if (!grid.children.length) {
    for (const name of Object.keys(CFG.STICKERS)) {
      const b = document.createElement("button"); b.type = "button"; b.setAttribute("aria-label", CFG.STICKERS[name].en);
      const cv = document.createElement("canvas"); cv.width = cv.height = 96; b.append(cv);
      const c = cv.getContext("2d"); c.translate(48, 48); E.drawSticker(c, name, 84, "#111", "#fff");
      b.addEventListener("click", () => { $("#dlgStickers").close(); addLayer({ type: "sticker", sticker: name, size: 0.22 }); });
      grid.append(b);
    }
  }
  $("#dlgStickers").showModal();
}
// перетаскивание слоёв по листу
let layerDrag = null;
vp.addEventListener("pointerdown", (e) => {
  if (e.shiftKey || textMode || ptrs.size > 1 || e.button > 0) return;
  const i = hitLayer(e.clientX, e.clientY);
  if (i < 0) { if (LY.sel >= 0 && ptrs.size === 1 && !gesture?.pinch) { /* клик мимо: снять выделение при отпускании без движения */ } return; }
  flushCommit();
  const ly = layersOf()[i], r = preview.getBoundingClientRect();
  LY.sel = i; layerDrag = { i, ox: ly.x - (e.clientX - r.left) / r.width, oy: ly.y - (e.clientY - r.top) / r.height, moved: false };
  refreshLayersUI();
}, true);
vp.addEventListener("pointermove", (e) => {
  if (!layerDrag) return;
  const r = preview.getBoundingClientRect(), ly = layersOf()[layerDrag.i]; if (!ly) return;
  ly.x = clamp((e.clientX - r.left) / r.width + layerDrag.ox, 0, 1); ly.y = clamp((e.clientY - r.top) / r.height + layerDrag.oy, 0, 1);
  layerDrag.moved = true; resetPresetLabel(); requestRender({ draft: true }); updateLayerSel();
}, true);
const endLayerDrag = () => { if (layerDrag) { if (layerDrag.moved) { commit(); requestRender(); } layerDrag = null; } };
vp.addEventListener("pointerup", endLayerDrag, true);
vp.addEventListener("pointercancel", endLayerDrag, true);

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
const LOCK_DEFS = [["palette", "Палитра", "Palette"], ["layout", "Раскладка", "Layout"], ["raster", "Растр", "Raster"], ["text", "Текст", "Text"], ["font", "Шрифт", "Font"], ["wear", "Износ", "Wear"]];
const LOCKS = ls.get("zine.locks", {}) || {};
function remix() {
  flushCommit();
  const st = page(), L = LOCKS, patch = { seed: newSeed(), tilt: +(Math.random() * 2.5).toFixed(1), loss: rnd(10, 60) };
  if (!L.text) { setQuote(st, pick(CFG.MANIFESTOS)); patch.tstyle = pick(CFG.TEXT_STYLES)[1]; }
  if (!L.palette) patch.palette = pick(Object.keys(CFG.RISO_PALETTES));
  if (!L.layout) { patch.layout = pick(CFG.LAYOUTS)[1]; patch.rows = rnd(4, 8); }
  if (!L.raster) { patch.dither = pick(CFG.DITHERS)[1]; patch.dot_size = rnd(5, 12); patch.angle = rnd(0, 90); }
  if (!L.font) patch.font = pick(Object.keys(CFG.FONTS));
  if (!L.wear) Object.assign(patch, { fold: Math.random() < 0.25 ? rnd(30, 90) : 0, stains: Math.random() < 0.3 ? rnd(20, 80) : 0, dust: Math.random() < 0.4 ? rnd(15, 70) : 0, holes: Math.random() < 0.15 });
  Object.assign(st, patch);
  syncUI(); resetPresetLabel(); commit(); requestRender(); scanSweep();
  toast(T("🎲 Новый стиль", "🎲 New style"), "ok", 1000);
}
const MUTATE_KEYS = ["dot_size", "angle", "contrast", "noise", "streaks", "misreg", "loss", "paper", "copier_edge", "tilt", "fold", "stains", "dust", "overprint", "tape"];
function mutate() {
  flushCommit();
  const st = page();
  for (const k of MUTATE_KEYS) {
    const el = ctlEls[k]?.el; if (!el || el.type !== "range") continue;
    const lo = Number(el.min), hi = Number(el.max), dec = decimals(el.step);
    const v = clamp(Number(st[k] ?? 0) + (Math.random() - 0.5) * (hi - lo) * 0.18, lo, hi);
    st[k] = Number(v.toFixed(dec));
  }
  st.seed = newSeed();
  syncUI(); resetPresetLabel(); commit(); requestRender();
  toast(T("🧬 Вид слегка изменён", "🧬 Look mutated"), "ok", 1000);
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
const render = (i, opts) => RC.renderPage(srcFor(S.pages[i]), S.pages[i], opts);
const pngU8 = async (canvas) => IO.pngSetDpi(await IO.blobToU8(await IO.canvasToBlob(canvas)), 300);
const memHint = (e) => (/memory|alloc|canvas/i.test(String(e && e.message)) ? T(" Не хватило памяти — попробуйте масштаб поменьше.", " Out of memory — try a lower scale.") : "");

async function job(title, fn, okMsg) {
  try {
    const r = await runJob(title, fn);
    if (okMsg) toast(typeof okMsg === "function" ? okMsg(r) : okMsg);
    printRitual();
  } catch (e) {
    if (e instanceof Cancelled) { toast(T("Отменено", "Cancelled"), "ok", 1200); return; }
    console.error(e); toast(T("Ошибка экспорта: ", "Export failed: ") + (e.message || e) + memHint(e), "err");
  }
}

// ---------------------------------------------------------------- звук копира и «ритуал печати»
const SOUND = { on: !!ls.get("zine.sound", false), ctx: null };
function copierSound(extraDest) {
  if (!SOUND.on) return;
  try {
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
    const ctx = SOUND.ctx || (SOUND.ctx = new AC()); if (ctx.state === "suspended") ctx.resume();
    const t0 = ctx.currentTime, dur = 1.5, n = Math.floor(ctx.sampleRate * dur), buf = ctx.createBuffer(1, n, ctx.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    const src = ctx.createBufferSource(); src.buffer = buf;
    const bp = ctx.createBiquadFilter(); bp.type = "bandpass"; bp.Q.value = 1.4;
    bp.frequency.setValueAtTime(500, t0); bp.frequency.exponentialRampToValueAtTime(2600, t0 + 1.1);
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(0.28, t0 + 0.12); g.gain.setValueAtTime(0.28, t0 + 1.0); g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    // «лампа»: быстрая вспышка-щелчок в начале
    const o = ctx.createOscillator(), og = ctx.createGain(); o.type = "square"; o.frequency.value = 90;
    og.gain.setValueAtTime(0.25, t0); og.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.09);
    src.connect(bp).connect(g).connect(ctx.destination); o.connect(og).connect(ctx.destination);
    if (extraDest) { g.connect(extraDest); og.connect(extraDest); }
    src.start(t0); o.start(t0); o.stop(t0 + 0.1);
  } catch { /* звук необязателен */ }
}
function printRitual() {
  copierSound();
  const el = document.createElement("div"); el.className = "ritual"; el.setAttribute("aria-hidden", "true");
  el.innerHTML = '<div class="copier"><div class="sheet"></div></div>';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2000);
}
function toggleSound() {
  SOUND.on = !SOUND.on; ls.set("zine.sound", SOUND.on);
  toast(SOUND.on ? T("Звук копира включён", "Copier sound on") : T("Звук копира выключен", "Copier sound off"), "ok", 1400);
  if (SOUND.on) copierSound();
}

// ---------------------------------------------------------------- схема сложения мини-зина
function foldSvg(step) {
  const W = 160, H = 84, x0 = 6, y0 = 6, w = 148, h = 72, cw = w / 4, rh = h / 2;
  const nums = [[5, 4, 3, 2], [6, 7, 8, 1]];
  const sheet = `<rect class="sh" x="${x0}" y="${y0}" width="${w}" height="${h}"/>`;
  let body = sheet;
  const label = (r, c, t, flip) => `<text x="${x0 + cw * c + cw / 2}" y="${y0 + rh * r + rh / 2}"${flip ? ` transform="rotate(180 ${x0 + cw * c + cw / 2} ${y0 + rh * r + rh / 2})"` : ""}>${t}</text>`;
  if (step === 1) body += `<line class="cr" x1="${x0}" y1="${y0 + rh}" x2="${x0 + w}" y2="${y0 + rh}"/>`;
  if (step === 2) for (let c = 1; c < 4; c++) body += `<line class="cr" x1="${x0 + cw * c}" y1="${y0}" x2="${x0 + cw * c}" y2="${y0 + h}"/>`;
  if (step >= 3 && step <= 3) {
    body += `<line class="cr" x1="${x0}" y1="${y0 + rh}" x2="${x0 + w}" y2="${y0 + rh}"/>`;
    for (let c = 1; c < 4; c++) body += `<line class="cr" x1="${x0 + cw * c}" y1="${y0}" x2="${x0 + cw * c}" y2="${y0 + h}"/>`;
    body += `<line class="cut" x1="${x0 + cw}" y1="${y0 + rh}" x2="${x0 + cw * 3}" y2="${y0 + rh}"/>`;
    for (let r = 0; r < 2; r++) for (let c = 0; c < 4; c++) body += label(r, c, nums[r][c], r === 0);
  }
  if (step === 4) {
    body = `<path class="sh" d="M${x0 + cw * 2} ${y0 + 4} L${x0 + cw * 3.4} ${y0 + rh} L${x0 + cw * 2} ${y0 + h - 4} L${x0 + cw * 0.6} ${y0 + rh} Z"/>` +
      `<line class="cr" x1="${x0 + cw * 0.6}" y1="${y0 + rh}" x2="${x0 + cw * 3.4}" y2="${y0 + rh}"/>` +
      `<line class="cut" x1="${x0 + cw * 2}" y1="${y0 + 4}" x2="${x0 + cw * 2}" y2="${y0 + h - 4}"/>`;
  }
  if (step === 5) body = `<rect class="sh" x="${x0 + cw * 1.2}" y="${y0 + 4}" width="${cw * 1.6}" height="${h - 8}"/><text x="${x0 + cw * 2}" y="${y0 + rh}">1</text>`;
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-hidden="true">${body}</svg>`;
}
function showFoldGuide() {
  const steps = [
    [T("Сложи лист пополам по длинной стороне, проведи по сгибу ногтем и раскрой.", "Fold the sheet in half the long way, crease it with a fingernail, unfold.")],
    [T("Сложи пополам поперёк, ещё раз пополам — получится 4 колонки. Раскрой.", "Fold in half across, then in half again for 4 columns. Unfold.")],
    [T("Сложи по длинной стороне и разрежь по красной линии: только средние две колонки.", "Fold the long way again and cut the red line: the middle two columns only.")],
    [T("Раскрой и сведи концы листа друг к другу — разрез откроется ромбом.", "Open it and push the two ends together; the slit opens into a diamond.")],
    [T("Прижми в книжечку: обложка — страница 1. Готово. Отдай другому.", "Press flat into a booklet with page 1 on the cover. Done. Hand it to someone.")],
  ];
  $("#foldBody").innerHTML = `<p class="muted small">${T("Красная линия на листе — разрез, пунктир — сгиб. Цифры — номера страниц.", "Red is the cut, dashed is the fold. Numbers are page numbers.")}</p><ol class="fold-steps">${steps.map((t, i) => `<li>${foldSvg(i + 1)}${t[0]}</li>`).join("")}</ol>`;
  $("#dlgFold").showModal();
}

// ---------------------------------------------------------------- буклет на скрепку, лист калибровки, палитра из фото
async function exportBooklet(paper) {
  flushCommit();
  const [PW, PH] = paper === "letter" ? [3300, 2550] : [3508, 2480]; // альбомный лист, 300 DPI
  const n = S.pages.length, total = Math.ceil(n / 4) * 4, sheets = total / 4, label = paper === "letter" ? "Letter" : "A4";
  const sink = await askSave(`${S.name || "zine"}_booklet_${label}.pdf`, { mime: "application/pdf", ext: ".pdf", desc: `PDF ${label}` });
  if (!sink) return;
  await job(T(`Буклет ${label}`, `Booklet ${label}`), async (progress) => {
    const M = 70, half = PW / 2;
    // порядок страниц при двусторонней печати со сшивкой по центру: лицо (N-1-2k | 2k), оборот (2k+1 | N-2-2k)
    const sides = [];
    for (let k = 0; k < sheets; k++) { sides.push([total - 1 - 2 * k, 2 * k]); sides.push([2 * k + 1, total - 2 - 2 * k]); }
    async function* gen() {
      for (let si = 0; si < sides.length; si++) {
        await progress(T(`Сторона листа ${si + 1} из ${sides.length}…`, `Sheet side ${si + 1} of ${sides.length}…`), si / (sides.length + 1));
        const sheet = E.makeCanvas(PW, PH), c = sheet.getContext("2d", { willReadFrequently: true });
        c.fillStyle = "#fff"; c.fillRect(0, 0, PW, PH);
        for (let h = 0; h < 2; h++) {
          const idx = sides[si][h];
          if (idx >= n) continue; // пустая страница добивки
          const [bw, bh] = baseSize(S.pages[idx]), k = Math.min((half - 2 * M) / bw, (PH - 2 * M) / bh);
          const size = [Math.floor(bw * k), Math.floor(bh * k)];
          const r = await render(idx, { outSize: size });
          c.drawImage(r.canvas, Math.floor(h * half + (half - size[0]) / 2), Math.floor((PH - size[1]) / 2));
        }
        c.strokeStyle = "#999"; c.lineWidth = 2; c.setLineDash([14, 12]);
        c.beginPath(); c.moveTo(half, 0); c.lineTo(half, PH); c.stroke();
        yield c.getImageData(0, 0, PW, PH);
      }
    }
    await sink.write(await IO.buildPdf(gen(), 300));
  }, T(`✓ Буклет готов: ${sheets} л. Печатай двусторонне, переворот по короткой стороне, сложи пополам.`, `✓ Booklet ready: ${sheets} sheet(s). Print double-sided, flip on the short edge, fold in half.`));
}

async function exportCalibration() {
  flushCommit();
  const sink = await askSave("printer_calibration_A4.png", { mime: "image/png", ext: ".png", desc: "PNG A4" });
  if (!sink) return;
  await job(T("Лист калибровки", "Calibration sheet"), async () => {
    const W = 2480, H = 3508, sheet = E.makeCanvas(W, H), c = sheet.getContext("2d", { willReadFrequently: true });
    c.fillStyle = "#fff"; c.fillRect(0, 0, W, H);
    c.fillStyle = "#000"; c.font = "bold 54px sans-serif"; c.textBaseline = "top";
    c.fillText("Xerox Zine Studio: printer calibration", 150, 130);
    c.font = "32px sans-serif";
    c.fillText(T("Распечатай в 100% без масштабирования. Выбери ячейку, где точки читаются и не слипаются.", "Print at 100%, no scaling. Pick the cell where dots stay readable and do not clog."), 150, 210);
    const dots = [4, 6, 8, 11, 15], tones = [0.1, 0.25, 0.4, 0.55, 0.7, 0.85], cw = 300, ch = 300, x0 = 250, y0 = 420, gap = 20;
    c.font = "bold 30px sans-serif";
    dots.forEach((d, row) => {
      c.fillStyle = "#000"; c.fillText(`dot ${d}`, 150, y0 + row * (ch + gap) + ch / 2 - 15);
      tones.forEach((t, col) => {
        const gray = new Uint8Array(cw * ch).fill(Math.round(255 * (1 - t)));
        const bits = E.halftoneBits(gray, cw, ch, d * 2, 45), img = c.createImageData(cw, ch);
        for (let i = 0; i < bits.length; i++) { const v = bits[i] ? 255 : 0; img.data.set([v, v, v, 255], i * 4); }
        c.putImageData(img, x0 + col * (cw + gap), y0 + row * (ch + gap));
        if (row === 0) { c.fillStyle = "#000"; c.fillText(`${Math.round(t * 100)}%`, x0 + col * (cw + gap) + 100, y0 - 44); }
      });
    });
    const by = y0 + dots.length * (ch + gap) + 40;
    c.fillStyle = "#000"; c.font = "30px sans-serif";
    c.fillText(T("Заливка 100% и тонкие линии: проверь, нет ли полос и сколько краски не доходит до края.", "Solid 100% and hairlines: look for banding and how much ink fails to reach the edge."), 150, by);
    c.fillRect(150, by + 70, W - 300, 120);
    for (let i = 0; i < 12; i++) c.fillRect(150 + i * 190, by + 240, 1 + i, 120);
    for (const [cx, cy] of [[90, 90], [W - 90, 90], [90, H - 90], [W - 90, H - 90]]) { c.fillRect(cx - 40, cy - 1, 80, 3); c.fillRect(cx - 1, cy - 40, 3, 80); }
    await sink.write(new Blob([await pngU8(sheet)], { type: "image/png" }));
  }, T("✓ Лист калибровки сохранён", "✓ Calibration sheet saved"));
}

function paletteFromPhoto() {
  flushCommit();
  const src = srcFor(page());
  if (!src) { toast(T("Сначала добавьте фото", "Add a photo first"), "err"); return; }
  const k = 64 / Math.max(src.canvas.width, src.canvas.height), w = Math.max(8, Math.round(src.canvas.width * k)), h = Math.max(8, Math.round(src.canvas.height * k));
  const tmp = E.makeCanvas(w, h), c = tmp.getContext("2d", { willReadFrequently: true });
  c.drawImage(src.canvas, 0, 0, w, h);
  const d = c.getImageData(0, 0, w, h).data, px = [];
  for (let i = 0; i < d.length; i += 4) px.push([d[i], d[i + 1], d[i + 2], 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]]);
  px.sort((a, b) => a[3] - b[3]);
  const q = Math.max(1, Math.floor(px.length * 0.12)), avg = (arr) => [0, 1, 2].map((j) => Math.round(arr.reduce((s2, p) => s2 + p[j], 0) / arr.length));
  let ink = avg(px.slice(0, q)), paper = avg(px.slice(-q));
  ink = ink.map((v) => Math.round(v * 0.55)); // краска темнее, чем тени на фото
  paper = paper.map((v) => Math.round(v + (255 - v) * 0.5));
  const st = page();
  st.custom_colors = [paper, ink]; st.palette = CFG.CUSTOM_PALETTE; st.invert = false;
  syncUI(); resetPresetLabel(); commit(); requestRender();
  toast(T("🎨 Палитра взята из фото", "🎨 Palette taken from the photo"), "ok", 1400);
}

// ---------------------------------------------------------------- история действий, папка с фото, видео для сторис
function stepLabel(prevStr, curStr) {
  if (!prevStr) return T("Начало", "Start");
  const a = JSON.parse(prevStr), b = JSON.parse(curStr);
  if (a.pages.length !== b.pages.length) return b.pages.length > a.pages.length ? T("Страница добавлена", "Page added") : T("Страница удалена", "Page removed");
  const names = {};
  for (const sec of SECTIONS()) for (const it of sec.items) if (it.k) names[it.k] = it.label;
  const keys = new Set();
  b.pages.forEach((pg, i) => { const q = a.pages[i] || {}; for (const k of Object.keys(pg)) if (JSON.stringify(pg[k]) !== JSON.stringify(q[k])) keys.add(k); });
  keys.delete("seed");
  if (!keys.size) return a.cur !== b.cur ? T("Другая страница", "Page switched") : T("Новые края и пыль", "New edges & dust");
  const list = [...keys].map((k) => (k === "layers" ? T("слои", "layers") : k === "img" || k === "crop" ? T("фото", "photo") : names[k] || k));
  return list.slice(0, 3).join(", ") + (list.length > 3 ? ` +${list.length - 3}` : "");
}
function openHistory() {
  flushCommit();
  const ol = $("#histList"); ol.textContent = "";
  H.stack.forEach((str, i) => {
    const li = document.createElement("li"), b = document.createElement("button");
    b.type = "button"; b.textContent = `${i + 1}. ${stepLabel(H.stack[i - 1], str)}`;
    if (i === H.idx) b.setAttribute("aria-current", "true");
    b.addEventListener("click", () => { H.idx = i; restoreSnap(H.stack[i]); $("#dlgHistory").close(); });
    li.append(b); ol.append(li);
  });
  $("#dlgHistory").showModal();
  const cur = ol.querySelector('[aria-current="true"]'); if (cur) cur.scrollIntoView({ block: "center" });
}
$("#fileDir").addEventListener("change", (e) => {
  const f = [...e.target.files].filter(isImageFile).sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  e.target.value = "";
  if (!f.length) { toast(T("В папке нет картинок", "No images in that folder"), "err"); return; }
  addPhotos(f);
});

async function exportStoryVideo() {
  flushCommit();
  if (typeof MediaRecorder === "undefined" || !HTMLCanvasElement.prototype.captureStream) { toast(T("Браузер не умеет записывать видео с холста", "This browser cannot record canvas video"), "err"); return; }
  const mime = ["video/mp4;codecs=avc1", "video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"].find((m) => MediaRecorder.isTypeSupported(m));
  if (!mime) { toast(T("Нет поддерживаемого формата видео", "No supported video format"), "err"); return; }
  const ext = mime.startsWith("video/mp4") ? ".mp4" : ".webm";
  const sink = await askSave(`${S.name || "zine"}_story${ext}`, { mime: mime.split(";")[0], ext, desc: "Video" });
  if (!sink) return;
  await job(T("Видео для сторис", "Story video"), async (progress) => {
    await progress(T("Рендеринг страницы…", "Rendering the page…"), 0.1);
    const page0 = (await render(S.cur, { scale: 1 })).canvas;
    const W = 1080, H2 = 1920, cv = document.createElement("canvas"); cv.width = W; cv.height = H2;
    const c = cv.getContext("2d"), DUR = 5200;
    const stream = cv.captureStream(30);
    let dest = null;
    if (SOUND.on) { try { const AC = window.AudioContext || window.webkitAudioContext; const ctx = SOUND.ctx || (SOUND.ctx = new AC()); dest = ctx.createMediaStreamDestination(); dest.stream.getAudioTracks().forEach((t) => stream.addTrack(t)); } catch { dest = null; } }
    const rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 5_000_000 }), chunks = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    const done = new Promise((res) => (rec.onstop = res));
    const pw = 760, ph = Math.round((pw * page0.height) / page0.width), slotY = 560, ease = (t) => 1 - Math.pow(1 - t, 3);
    const t0 = performance.now(); rec.start(200); copierSound(dest);
    await progress(T("Запись видео…", "Recording…"), 0.3);
    await new Promise((resolve) => {
      const frame = () => {
        const t = performance.now() - t0, k = Math.min(1, t / DUR);
        c.fillStyle = "#e9e4d8"; c.fillRect(0, 0, W, H2);
        c.fillStyle = "rgba(0,0,0,.05)"; for (let y = 0; y < H2; y += 6) c.fillRect(0, y, W, 1);
        // копир
        const shake = k < 0.7 ? Math.sin(t / 22) * 2 : 0;
        c.save(); c.translate(shake, 0);
        c.fillStyle = "#c9c9c9"; c.strokeStyle = "#1a1a1a"; c.lineWidth = 10;
        c.beginPath(); c.roundRect(90, 330, 900, 280, 28); c.fill(); c.stroke();
        c.fillStyle = "#1a1a1a"; c.fillRect(160, slotY - 30, 760, 22);
        const lamp = (t % 900) / 900; c.fillStyle = `rgba(255,240,150,${k < 0.75 ? 0.35 + 0.5 * Math.abs(Math.sin(lamp * Math.PI)) : 0.1})`; c.fillRect(160, 380, 760, 40 + 60 * lamp);
        c.restore();
        // лист выезжает
        const out = ease(Math.min(1, Math.max(0, (t - 500) / 3200))), y = slotY - 14 - ph + out * (ph * 0.78);
        c.save(); c.beginPath(); c.rect(0, slotY - 8, W, H2); c.clip();
        c.shadowColor = "rgba(0,0,0,.35)"; c.shadowBlur = 24; c.shadowOffsetY = 12;
        c.drawImage(page0, (W - pw) / 2, y, pw, ph);
        c.restore();
        c.fillStyle = "#1a1a1a"; c.font = "bold 54px Rubik, sans-serif"; c.textAlign = "center";
        c.fillText(S.name || "zine", W / 2, 1780 - (1 - ease(Math.min(1, Math.max(0, (t - 3000) / 1000)))) * 40);
        c.font = "32px Rubik, sans-serif"; c.fillStyle = "#555"; c.fillText("made on Xerox Zine Studio", W / 2, 1840);
        if (t < DUR) requestAnimationFrame(frame); else resolve();
      };
      frame();
    });
    rec.stop(); await done;
    await progress(T("Сохранение…", "Saving…"), 0.9);
    await sink.write(new Blob(chunks, { type: mime.split(";")[0] }));
  }, T("✓ Видео для сторис сохранено", "✓ Story video saved"));
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
function regMarks(bits, w, h) {
  // перекрестия приводки по углам: 0 = краска; одинаковы на всех пластинах
  const m = Math.round(Math.min(w, h) * 0.035), arm = Math.round(m * 0.9);
  const put = (x, y) => { if (x >= 0 && y >= 0 && x < w && y < h) bits[y * w + x] = 0; };
  for (const [cx, cy] of [[m, m], [w - 1 - m, m], [m, h - 1 - m], [w - 1 - m, h - 1 - m]]) {
    for (let d = -arm; d <= arm; d++) { put(cx + d, cy); put(cx, cy + d); if (Math.abs(d) < 2) { put(cx + d, cy + 1); put(cx + 1, cy + d); } }
  }
  return bits;
}
async function exportSeparations() {
  flushCommit();
  const sink = await askSave(`${pageName(S.cur)}_riso.zip`, { mime: "application/zip", ext: ".zip", desc: "ZIP" });
  if (!sink) return;
  await job(T("Разделение красок", "Ink separations"), async (progress) => {
    await progress(T("Рендеринг…", "Rendering…"), 0.3);
    const r = await render(S.cur, { scale: exportScale() });
    const base = pageName(S.cur), entries = [];
    const hx = (c) => rgbHex(c).toUpperCase();
    entries.push({ name: `${base}_ink1.png`, data: await IO.encodePng1(regMarks(Uint8Array.from(r.bits), r.width, r.height), r.width, r.height, 300) });
    if (r.plate2) entries.push({ name: `${base}_ink2.png`, data: await IO.encodePng1(regMarks(Uint8Array.from(r.plate2), r.width, r.height), r.width, r.height, 300) });
    for (const [nm, ex] of Object.entries(r.extraPlates || {})) {
      entries.push({ name: `${base}_${nm}.png`, data: await IO.encodePng1(regMarks(Uint8Array.from(ex.bits), r.width, r.height), r.width, r.height, 300) });
    }
    const L = [
      "XEROX ZINE STUDIO - INK SEPARATIONS / RAZDELENIE KRASOK", "",
      `ink1: ${base}_ink1.png  -> ink ${hx(r.inks.ink)}`,
      r.plate2 ? `ink2: ${base}_ink2.png  -> ink ${hx(r.inks.ink2)}` : "ink2: none (overprint is 0)",
      ...Object.entries(r.extraPlates || {}).map(([nm, ex]) => `${nm}: ${base}_${nm}.png  -> ink ${hx(ex.rgb)}`),
      `paper: ${hx(r.inks.paper)}`, "",
      "Black = ink, white = nothing. Print ink1, let it dry, then lay the SAME sheet",
      "into the machine again aligned by the corner crosses and print ink2.",
      "Slight misregistration is not a bug. It is the point.", "",
      "Чёрное = краска. Печатай ink1, дай высохнуть, затем тот же лист снова,",
      "совместив по угловым крестам, и печатай ink2. Небольшой сдвиг - не ошибка, а суть.", ""];
    entries.push({ name: "README.txt", data: new TextEncoder().encode(L.join("\n")) });
    await sink.write(new Blob([IO.writeZip(entries)], { type: "application/zip" }));
  }, T("✓ Пластины красок сохранены (ZIP)", "✓ Ink plates saved (ZIP)"));
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
      rendered.push((await RC.renderPage(srcFor(items[i]), items[i], { outSize: [cw, rh] })).canvas);
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
    [T("Добавить папку с фото (каждое = страница)…", "Add a folder of photos (one page each)…"), () => $("#fileDir").click()],
    [T("Открыть проект (.zine)…", "Open project (.zine)…"), openProjectDialog, "Ctrl+Shift+O"],
    [T("Сохранить проект (.zine)", "Save project (.zine)"), () => saveProject(false), "Ctrl+Shift+S"],
    [T("Сохранить проект как…", "Save project as…"), () => saveProject(true)],
    "hr", T("ЭКСПОРТ", "EXPORT"),
    [T("Страница в PNG", "Page as PNG"), exportPng, "Ctrl+S"],
    [T("Копировать ссылку на этот вид", "Copy link to this look"), copyLookLink],
    ...(CAN_SHARE() ? [[T("Поделиться страницей…", "Share page…"), sharePage]] : []),
    ...(CAN_COPY() ? [[T("Копировать страницу в буфер", "Copy page to clipboard"), copyPage]] : []),
    [T("Все страницы в PNG (ZIP)", "All pages as PNG (ZIP)"), exportAllPng],
    [T("1-bit трафарет (PNG)", "1-bit stencil (PNG)"), exportStencil],
    [T("Разделение красок для ризографа (ZIP)", "Riso ink separations (ZIP)"), exportSeparations],
    [T("Книга в PDF", "Book as PDF"), exportPdf],
    [T("PDF для печати (A4, поля 10 мм)", "Print PDF (A4, 10 mm margins)"), exportPdfA4],
    [T("Мини-зин на 8 страниц (A4)", "8-page mini-zine (A4)"), exportMiniZine],
    [T("Буклет на скрепку, A4 (любое число страниц)", "Saddle-stitch booklet, A4 (any page count)"), () => exportBooklet("a4")],
    [T("Буклет на скрепку, Letter", "Saddle-stitch booklet, Letter"), () => exportBooklet("letter")],
    [T("Лист калибровки принтера (A4)", "Printer calibration sheet (A4)"), exportCalibration],
    [T("Видео для сторис (печать листа, 9:16)", "Story video (sheet printing, 9:16)"), exportStoryVideo],
    [T("Как сложить мини-зин (схема)", "How to fold the mini-zine (guide)"), showFoldGuide],
    [SOUND.on ? T("Звук копира: выключить", "Copier sound: turn off") : T("Звук копира: включить", "Copier sound: turn on"), toggleSound],
    "hr", T("СТРАНИЦЫ И ТЕКСТ", "PAGES & TEXT"),
    [T("История действий…", "History…"), openHistory, "Ctrl+H"],
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
  if (mod && key === "h") { e.preventDefault(); openHistory(); return; }
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
  RC.warmUp();
  applyStaticLang();
  $("#btnLang").textContent = LANG === "ru" ? "EN" : "RU";
  S.pages = [freshPage()];
  buildSettings(); buildMenu();
  const restoring = await offerRestore();
  if (!restoring) await loadSample();
  const fromLink = !restoring && applyLookFromHash();
  resetHistory(); markClean();
  afterPageSwitch();
  if (!restoring && srcFor(page()) && !fromLink && !ls.get("zine.welcomed", false) && !/[?&]shot\b/.test(location.search)) $("#dlgWelcome").showModal();
  if (fromLink) { syncUI(); requestRender(); toast(T("Открыт чужой вид. Добавьте своё фото!", "Opened a shared look. Add your own photo!"), "ok", 4000); }
  if ("serviceWorker" in navigator && /^https:|^http:\/\/localhost/.test(location.href)) {
    navigator.serviceWorker.register("sw.js").then((reg) => {
      reg.addEventListener("updatefound", () => {
        const nw = reg.installing;
        if (nw) nw.addEventListener("statechange", () => { if (nw.state === "installed" && navigator.serviceWorker.controller) toast(T("Доступна новая версия — обновите страницу", "A new version is available — reload the page"), "ok", 6000); });
      });
    }).catch(() => {});
  }
  window.__zine = { S, E, RC, IO, page, requestRender, commit, undo, redo, gotoPage, addPage, exportPng, remix }; // для автотестов
  window.__ready = true;
}
init();
