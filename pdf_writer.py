"""
PDF writer: многостраничный PDF без потерь.

Pillow сохраняет RGB-страницы в PDF как JPEG, и растр из мелких точек получает артефакты сжатия.
Здесь страницы кладутся как индексированные изображения со сжатием Flate: для картинок из
2–4 цветов это и точнее, и компактнее. Страницы принимаются по одной (генератор), поэтому
пик памяти равен одной странице.
"""

import os
import zlib

import numpy as np


def _encode(im):
    """-> (width, height, colorspace, bytes). Индексированный режим, если цветов не больше 256."""
    im = im.convert("RGB")
    w, h = im.size
    colors = im.getcolors(maxcolors=256)
    arr = np.asarray(im)
    if colors:
        palette = [c for _n, c in sorted(colors, reverse=True)]
        idx = np.zeros((h, w), dtype=np.uint8)
        for i, c in enumerate(palette):
            if i:
                idx[(arr == c).all(axis=2)] = i
        hexpal = "".join("%02X%02X%02X" % tuple(c) for c in palette)
        return w, h, f"[/Indexed /DeviceRGB {len(palette) - 1} <{hexpal}>]", idx.tobytes()
    return w, h, "/DeviceRGB", arr.tobytes()


def write_pdf(path, pages, dpi=300.0):
    """pages - итерируемое PIL-изображений. Возвращает число страниц."""
    tmp = f"{path}.tmp"
    offsets = {}
    page_ids = []
    try:
        with open(tmp, "wb") as f:
            def put(num, body):
                offsets[num] = f.tell()
                f.write(f"{num} 0 obj\n".encode() + body + b"\nendobj\n")

            def stream(entries, data):
                return f"<< {entries} /Length {len(data)} >>\nstream\n".encode() + data + b"\nendstream"

            f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
            next_id = 3
            for im in pages:
                w, h, colorspace, raw = _encode(im)
                wpt, hpt = w * 72.0 / dpi, h * 72.0 / dpi
                img_id, content_id, page_id = next_id, next_id + 1, next_id + 2
                next_id += 3
                put(img_id, stream(
                    f"/Type /XObject /Subtype /Image /Width {w} /Height {h} /ColorSpace {colorspace} "
                    f"/BitsPerComponent 8 /Filter /FlateDecode", zlib.compress(raw, 6)))
                put(content_id, stream("", f"q {wpt:.3f} 0 0 {hpt:.3f} 0 0 cm /Im0 Do Q".encode()))
                put(page_id, (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {wpt:.3f} {hpt:.3f}] "
                    f"/Resources << /XObject << /Im0 {img_id} 0 R >> >> /Contents {content_id} 0 R >>"
                ).encode())
                page_ids.append(page_id)
            if not page_ids:
                raise ValueError("в PDF нет страниц")
            kids = " ".join(f"{i} 0 R" for i in page_ids)
            put(2, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode())
            put(1, b"<< /Type /Catalog /Pages 2 0 R >>")
            xref_pos = f.tell()
            total = next_id
            f.write(f"xref\n0 {total}\n".encode() + b"0000000000 65535 f \n")
            for n in range(1, total):
                f.write(f"{offsets[n]:010d} 00000 n \n".encode())
            f.write(f"trailer\n<< /Size {total} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return len(page_ids)
