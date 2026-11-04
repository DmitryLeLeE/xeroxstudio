// Форматы файлов без внешних библиотек: ZIP (.zine совместим с десктопом), PDF без потерь, 1-bit PNG.

const enc = new TextEncoder();
const dec = new TextDecoder("utf-8");

// ---------------------------------------------------------------- CRC32 и Adler32
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

export function crc32(u8, crc = 0) {
  let c = ~crc >>> 0;
  for (let i = 0; i < u8.length; i++) c = CRC_TABLE[(c ^ u8[i]) & 0xff] ^ (c >>> 8);
  return ~c >>> 0;
}

function adler32(u8) {
  let a = 1, b = 0;
  for (let i = 0; i < u8.length; i++) { a = (a + u8[i]) % 65521; b = (b + a) % 65521; }
  return ((b << 16) | a) >>> 0;
}

export function concat(parts) {
  const total = parts.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(total);
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}

// ---------------------------------------------------------------- deflate
async function streamThrough(u8, transform) {
  const stream = new Blob([u8]).stream().pipeThrough(transform);
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

/** zlib-поток (формат PDF FlateDecode и PNG IDAT). Без CompressionStream пишет несжатые блоки. */
export async function zlibCompress(u8) {
  if (typeof CompressionStream !== "undefined") {
    try { return await streamThrough(u8, new CompressionStream("deflate")); } catch { /* ниже запасной путь */ }
  }
  const parts = [Uint8Array.of(0x78, 0x01)];
  for (let i = 0; i < u8.length || i === 0; i += 65535) {
    const chunk = u8.subarray(i, Math.min(u8.length, i + 65535));
    const last = i + 65535 >= u8.length;
    const head = new Uint8Array(5);
    head[0] = last ? 1 : 0;
    head[1] = chunk.length & 255; head[2] = chunk.length >> 8;
    head[3] = ~chunk.length & 255; head[4] = (~chunk.length >> 8) & 255;
    parts.push(head, chunk);
    if (u8.length === 0) break;
  }
  const ad = adler32(u8);
  parts.push(Uint8Array.of(ad >>> 24, (ad >>> 16) & 255, (ad >>> 8) & 255, ad & 255));
  return concat(parts);
}

async function rawInflate(u8) {
  if (typeof DecompressionStream === "undefined") throw new Error("Браузер не умеет распаковывать zip: обновите его");
  return streamThrough(u8, new DecompressionStream("deflate-raw"));
}

// ---------------------------------------------------------------- ZIP
/** entries: [{name, data: Uint8Array}] -> Uint8Array. Без сжатия (PNG и так сжаты). */
export function writeZip(entries) {
  const locals = [], centrals = [];
  let offset = 0;
  const now = new Date();
  const dosTime = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1);
  const dosDate = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
  for (const { name, data } of entries) {
    const nameBytes = enc.encode(name), crc = crc32(data);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true);
    lh.setUint16(8, 0, true); lh.setUint16(10, dosTime, true); lh.setUint16(12, dosDate, true);
    lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true);
    lh.setUint16(26, nameBytes.length, true); lh.setUint16(28, 0, true);
    locals.push(new Uint8Array(lh.buffer), nameBytes, data);

    const ch = new DataView(new ArrayBuffer(46));
    ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true);
    ch.setUint16(10, 0, true); ch.setUint16(12, dosTime, true); ch.setUint16(14, dosDate, true);
    ch.setUint32(16, crc, true); ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true);
    ch.setUint16(28, nameBytes.length, true); ch.setUint32(42, offset, true);
    centrals.push(new Uint8Array(ch.buffer), nameBytes);
    offset += 30 + nameBytes.length + data.length;
  }
  const centralBytes = concat(centrals);
  const eocd = new DataView(new ArrayBuffer(22));
  eocd.setUint32(0, 0x06054b50, true);
  eocd.setUint16(8, entries.length, true); eocd.setUint16(10, entries.length, true);
  eocd.setUint32(12, centralBytes.length, true); eocd.setUint32(16, offset, true);
  return concat([...locals, centralBytes, new Uint8Array(eocd.buffer)]);
}

/** -> Map имя -> Uint8Array. Понимает хранение и deflate (так пишет десктопная версия). */
export async function readZip(buffer) {
  const u8 = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  let eocd = -1;
  for (let i = u8.length - 22; i >= Math.max(0, u8.length - 65557); i--) {
    if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error("это не zip/.zine файл");
  const count = dv.getUint16(eocd + 10, true);
  let p = dv.getUint32(eocd + 16, true);
  const files = new Map();
  for (let n = 0; n < count; n++) {
    if (dv.getUint32(p, true) !== 0x02014b50) throw new Error("повреждён каталог zip");
    const method = dv.getUint16(p + 10, true), csize = dv.getUint32(p + 20, true);
    const nlen = dv.getUint16(p + 28, true), elen = dv.getUint16(p + 30, true), clen = dv.getUint16(p + 32, true);
    const lho = dv.getUint32(p + 42, true);
    const name = dec.decode(u8.subarray(p + 46, p + 46 + nlen));
    const dataStart = lho + 30 + dv.getUint16(lho + 26, true) + dv.getUint16(lho + 28, true);
    const raw = u8.subarray(dataStart, dataStart + csize);
    if (method === 0) files.set(name, raw.slice());
    else if (method === 8) files.set(name, await rawInflate(raw));
    else throw new Error(`неизвестный способ сжатия в zip (${method})`);
    p += 46 + nlen + elen + clen;
  }
  return files;
}

// ---------------------------------------------------------------- PDF без потерь
/** Индексированное изображение, если цветов не больше 256, иначе RGB. */
function encodePixels(imageData) {
  const { data, width: w, height: h } = imageData;
  const map = new Map(), palette = [];
  const idx = new Uint8Array(w * h);
  let indexed = true;
  for (let i = 0, p = 0; i < idx.length; i++, p += 4) {
    const key = (data[p] << 16) | (data[p + 1] << 8) | data[p + 2];
    let k = map.get(key);
    if (k === undefined) {
      if (palette.length >= 256) { indexed = false; break; }
      k = palette.length;
      map.set(key, k);
      palette.push(key);
    }
    idx[i] = k;
  }
  if (indexed) {
    const hex = palette.map((c) => c.toString(16).padStart(6, "0").toUpperCase()).join("");
    return { colorspace: `[/Indexed /DeviceRGB ${palette.length - 1} <${hex}>]`, raw: idx };
  }
  const rgb = new Uint8Array(w * h * 3);
  for (let i = 0, p = 0, q = 0; i < w * h; i++, p += 4, q += 3) { rgb[q] = data[p]; rgb[q + 1] = data[p + 1]; rgb[q + 2] = data[p + 2]; }
  return { colorspace: "/DeviceRGB", raw: rgb };
}

/**
 * pages - асинхронный/обычный итератор ImageData (по одной странице, чтобы не копить память).
 * Возвращает Blob application/pdf.
 */
export async function buildPdf(pages, dpi = 300) {
  const parts = [], offsets = {}, pageIds = [];
  let pos = 0;
  const push = (u8) => { parts.push(u8); pos += u8.length; };
  const put = (num, body) => { offsets[num] = pos; push(enc.encode(`${num} 0 obj\n`)); push(typeof body === "string" ? enc.encode(body) : body); push(enc.encode("\nendobj\n")); };
  const stream = (entries, data) => concat([enc.encode(`<< ${entries} /Length ${data.length} >>\nstream\n`), data, enc.encode("\nendstream")]);

  push(Uint8Array.of(0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34, 0x0a, 0x25, 0xe2, 0xe3, 0xcf, 0xd3, 0x0a));
  let next = 3;
  for await (const imageData of pages) {
    const { width: w, height: h } = imageData;
    const { colorspace, raw } = encodePixels(imageData);
    const wpt = ((w * 72) / dpi).toFixed(3), hpt = ((h * 72) / dpi).toFixed(3);
    const [imgId, contId, pageId] = [next, next + 1, next + 2];
    next += 3;
    put(imgId, stream(`/Type /XObject /Subtype /Image /Width ${w} /Height ${h} /ColorSpace ${colorspace} /BitsPerComponent 8 /Filter /FlateDecode`, await zlibCompress(raw)));
    put(contId, stream("", enc.encode(`q ${wpt} 0 0 ${hpt} 0 0 cm /Im0 Do Q`)));
    put(pageId, `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${wpt} ${hpt}] /Resources << /XObject << /Im0 ${imgId} 0 R >> >> /Contents ${contId} 0 R >>`);
    pageIds.push(pageId);
  }
  if (!pageIds.length) throw new Error("в PDF нет страниц");
  put(2, `<< /Type /Pages /Kids [${pageIds.map((i) => `${i} 0 R`).join(" ")}] /Count ${pageIds.length} >>`);
  put(1, "<< /Type /Catalog /Pages 2 0 R >>");
  const xref = pos;
  let table = `xref\n0 ${next}\n0000000000 65535 f \n`;
  for (let n = 1; n < next; n++) table += `${String(offsets[n]).padStart(10, "0")} 00000 n \n`;
  push(enc.encode(`${table}trailer\n<< /Size ${next} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`));
  return new Blob(parts, { type: "application/pdf" });
}

// ---------------------------------------------------------------- 1-bit PNG (трафарет)
function pngChunk(type, data) {
  const t = enc.encode(type);
  const out = new Uint8Array(12 + data.length), dv = new DataView(out.buffer);
  dv.setUint32(0, data.length);
  out.set(t, 4);
  out.set(data, 8);
  dv.setUint32(8 + data.length, crc32(concat([t, data])));
  return out;
}

/** bits: Uint8Array w*h, 1 = белый (бумага), 0 = чёрный (краска). */
export async function encodePng1(bits, w, h, dpi = 300) {
  const rowBytes = (w + 7) >> 3;
  const raw = new Uint8Array((rowBytes + 1) * h);
  for (let y = 0; y < h; y++) {
    const o = y * (rowBytes + 1) + 1;
    for (let x = 0; x < w; x++) if (bits[y * w + x]) raw[o + (x >> 3)] |= 0x80 >> (x & 7);
  }
  const ihdr = new DataView(new ArrayBuffer(13));
  ihdr.setUint32(0, w); ihdr.setUint32(4, h); ihdr.setUint8(8, 1); ihdr.setUint8(9, 0);
  const ppm = Math.round(dpi / 0.0254), phys = new DataView(new ArrayBuffer(9));
  phys.setUint32(0, ppm); phys.setUint32(4, ppm); phys.setUint8(8, 1);
  return new Blob([
    Uint8Array.of(137, 80, 78, 71, 13, 10, 26, 10),
    pngChunk("IHDR", new Uint8Array(ihdr.buffer)), pngChunk("pHYs", new Uint8Array(phys.buffer)),
    pngChunk("IDAT", await zlibCompress(raw)), pngChunk("IEND", new Uint8Array(0)),
  ], { type: "image/png" });
}

/** Вписывает плотность пикселей (pHYs) в готовый PNG: canvas.toBlob её не пишет. */
export function pngSetDpi(u8, dpi = 300) {
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
  if (u8.length < 33 || dv.getUint32(0) !== 0x89504e47) return u8;
  const ppm = Math.round(dpi / 0.0254), phys = new DataView(new ArrayBuffer(9));
  phys.setUint32(0, ppm); phys.setUint32(4, ppm); phys.setUint8(8, 1);
  const at = 8 + 12 + 13; // сигнатура + IHDR
  return concat([u8.subarray(0, at), pngChunk("pHYs", new Uint8Array(phys.buffer)), u8.subarray(at)]);
}

// ---------------------------------------------------------------- вспомогательное
export const canvasToBlob = (canvas, type = "image/png") => new Promise((res, rej) => canvas.toBlob((b) => (b ? res(b) : rej(new Error("не удалось закодировать картинку"))), type));
export const blobToU8 = async (blob) => new Uint8Array(await blob.arrayBuffer());
export const textToU8 = (s) => enc.encode(s);
export const u8ToText = (u8) => dec.decode(u8);
