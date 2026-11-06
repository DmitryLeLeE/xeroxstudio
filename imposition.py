"""Раскладка буклета на скрепку и лист калибровки принтера (десктоп; в вебе то же сделано в app.js)."""
import numpy as np
from PIL import Image, ImageDraw


def booklet_sides(n):
    """Стороны листов для двусторонней печати со сшивкой по центру: [(левая, правая), ...].
    Номера с нуля; индексы >= n означают пустую страницу добивки до кратности 4."""
    total = -(-n // 4) * 4
    sides = []
    for k in range(total // 4):
        sides.append((total - 1 - 2 * k, 2 * k))
        sides.append((2 * k + 1, total - 2 - 2 * k))
    return sides


def calibration_sheet(engine):
    """A4 300 DPI: растровые поля (размер точки x тон), заливка, тонкие линии, кресты приводки."""
    W, H = 2480, 3508
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((150, 130), "Xerox Zine Studio: printer calibration", fill=(0, 0, 0), font=engine.get_font("Arial Black", 54))
    small = engine.get_font("Arial Bold", 32)
    d.text((150, 210), "Print at 100%, no scaling. Pick the cell where dots stay readable and do not clog.", fill=(0, 0, 0), font=small)
    dots, tones, cw, ch, x0, y0, gap = [4, 6, 8, 11, 15], [0.1, 0.25, 0.4, 0.55, 0.7, 0.85], 300, 300, 250, 420, 20
    lab = engine.get_font("Arial Bold", 30)
    for row, dot in enumerate(dots):
        d.text((150, y0 + row * (ch + gap) + ch // 2 - 15), f"dot {dot}", fill=(0, 0, 0), font=lab)
        for col, t in enumerate(tones):
            gray = Image.fromarray(np.full((ch, cw), round(255 * (1 - t)), dtype=np.uint8))
            bits = engine.apply_halftone_dots(gray, dot_size=dot * 2, angle=45)
            sheet.paste(Image.fromarray((bits * 255).astype(np.uint8)).convert("RGB"), (x0 + col * (cw + gap), y0 + row * (ch + gap)))
            if row == 0:
                d.text((x0 + col * (cw + gap) + 100, y0 - 44), f"{round(t * 100)}%", fill=(0, 0, 0), font=lab)
    by = y0 + len(dots) * (ch + gap) + 40
    d.text((150, by), "Solid 100% and hairlines: look for banding and how much ink fails to reach the edge.", fill=(0, 0, 0), font=small)
    d.rectangle([150, by + 70, W - 150, by + 190], fill=(0, 0, 0))
    for i in range(12):
        d.rectangle([150 + i * 190, by + 240, 150 + i * 190 + i, by + 360], fill=(0, 0, 0))
    for cx, cy in ((90, 90), (W - 90, 90), (90, H - 90), (W - 90, H - 90)):
        d.rectangle([cx - 40, cy - 1, cx + 40, cy + 1], fill=(0, 0, 0))
        d.rectangle([cx - 1, cy - 40, cx + 1, cy + 40], fill=(0, 0, 0))
    return sheet


# ---- Плакат крупнее A4: разбивка на листы A4 с нахлёстом для склейки
PAPER_MM = {"A3": (297, 420), "A2": (420, 594), "A1": (594, 841)}


def poster_size_px(paper, page_w, page_h, dpi=300):
    """Размер плаката в пикселях: страница вписывается в лист выбранного формата (портрет или альбом по пропорции страницы)."""
    pw, ph = PAPER_MM[paper]
    if page_w > page_h:
        pw, ph = ph, pw
    mm = dpi / 25.4
    k = min(pw / page_w, ph / page_h)
    return int(page_w * k * mm), int(page_h * k * mm)


def tile_plan(W, H, dpi=300, margin_mm=5, overlap_mm=10):
    """Раскладка плаката W×H px по листам A4: ориентация с меньшим числом листов, нахлёст overlap_mm для склейки.
    -> {sheet: (w, h), margin, usable: (ux, uy), tiles: [(row, col, x0, y0, x1, y1)], rows, cols}"""
    mm = dpi / 25.4
    best = None
    for sw_mm, sh_mm in ((210, 297), (297, 210)):
        ux, uy = int((sw_mm - 2 * margin_mm) * mm), int((sh_mm - 2 * margin_mm) * mm)
        ov = int(overlap_mm * mm)
        cols = 1 if W <= ux else -(-(W - ov) // (ux - ov))
        rows = 1 if H <= uy else -(-(H - ov) // (uy - ov))
        if best is None or cols * rows < best[0]:
            best = (cols * rows, sw_mm, sh_mm, ux, uy, ov, cols, rows)
    _, sw_mm, sh_mm, ux, uy, ov, cols, rows = best
    tiles = []
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * (ux - ov), r * (uy - ov)
            tiles.append((r, c, x0, y0, min(x0 + ux, W), min(y0 + uy, H)))
    return {"sheet": (int(sw_mm * mm), int(sh_mm * mm)), "margin": int(margin_mm * mm), "usable": (ux, uy),
            "overlap": ov, "tiles": tiles, "rows": rows, "cols": cols}


def tile_sheet(poster, plan, tile, label=""):
    """Один лист A4 плаката: кусок картинки на белом поле, уголки реза и подпись «ряд/колонка»."""
    r, c, x0, y0, x1, y1 = tile
    sw, sh = plan["sheet"]
    m = plan["margin"]
    sheet = Image.new("RGB", (sw, sh), (255, 255, 255))
    sheet.paste(poster.crop((x0, y0, x1, y1)), (m, m))
    d = ImageDraw.Draw(sheet)
    L = max(6, m // 2)
    for (cx, cy) in ((m, m), (m + x1 - x0, m), (m, m + y1 - y0), (m + x1 - x0, m + y1 - y0)):
        dx = -1 if cx > m else 1
        dy = -1 if cy > m else 1
        d.line([(cx, cy), (cx + dx * L, cy)], fill=(0, 0, 0), width=2)
        d.line([(cx, cy), (cx, cy + dy * L)], fill=(0, 0, 0), width=2)
    # подпись в нижнем поле: нахлёст проходит по границе соседей, помечаем его пунктиром
    txt = f"{label} · ряд {r + 1}/{plan['rows']} · колонка {c + 1}/{plan['cols']}"
    d.text((m, sh - m // 2 - 6), txt, fill=(90, 90, 90))
    return sheet
