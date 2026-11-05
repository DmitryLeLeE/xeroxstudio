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
