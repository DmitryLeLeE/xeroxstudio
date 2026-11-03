"""
Генератор иконки приложения: icon.ico (16–256 px) и icon.png (256 px).

Иконка нарисована самим движком программы: полутоновый глаз на рваном листе бумаги
с ризографским «призраком» розовой краски и лентой Dymo на лаймовой плашке.
Запуск:  python make_icon.py
"""

import os

import numpy as np
from PIL import Image, ImageDraw

from engine import ZineGraphicEngine

LIME = (214, 255, 0)
PAPER = (250, 247, 238)
INK = (10, 10, 10)
PINK = (255, 42, 133)
SIZES = [16, 24, 32, 48, 64, 128, 256]


def eye_artwork(w, h):
    """Серое изображение 0..255: глаз, веко и лента Dymo. Из него растр делает движок."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy, r = w * 0.5, h * 0.40, w * 0.46
    u, v = (xx - cx) / r, (yy - cy) / r

    gray = np.full((h, w), 255.0, dtype=np.float32)
    half = 0.50 * np.clip(1.0 - u * u, 0, 1) ** 0.8
    inside = (np.abs(v) < half) & (np.abs(u) < 1.0)
    gray[inside] = 236.0  # белок

    d = np.hypot(u, v)
    iris = inside & (d < 0.46)
    gray[iris] = 95.0 - 55.0 * np.clip((d[iris] - 0.30) / 0.16, 0, 1)  # радужка темнеет к краю
    gray[inside & (d < 0.20)] = 0.0  # зрачок
    gray[np.hypot(u + 0.13, v + 0.15) < 0.075] = 255.0  # блик

    lid = np.abs(np.abs(v) - half) < 0.045  # контур века
    gray[lid & (np.abs(u) < 0.98)] = 0.0

    # лента Dymo с «текстом»
    x0, x1, y0, y1 = int(w * 0.12), int(w * 0.88), int(h * 0.73), int(h * 0.87)
    gray[y0:y1, x0:x1] = 0.0
    mid = (y0 + y1) // 2
    th = max(2, (y1 - y0) // 6)
    for a, b in ((0.18, 0.46), (0.52, 0.66), (0.72, 0.82)):
        gray[mid - th: mid + th, int(w * a): int(w * b)] = 255.0
    return gray


def render_icon(engine, size):
    ss = 8 if size <= 48 else 4
    n = size * ss
    radius = int(n * 0.22)

    canvas = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).rounded_rectangle([0, 0, n - 1, n - 1], radius=radius, fill=LIME + (255,))

    sw, sh = int(n * 0.66), int(n * 0.80)
    dots_across = 15 if size >= 128 else 10 if size >= 48 else 7
    dot = sw / dots_across
    bits = engine.apply_halftone_dots(Image.fromarray(eye_artwork(sw, sh).astype(np.uint8)), dot_size=dot, angle=45)
    ink = ~bits

    sheet = np.empty((sh, sw, 3), dtype=np.uint8)
    sheet[:] = PAPER
    dx, dy = max(1, int(n * 0.018)), max(1, int(n * 0.010))
    ghost = np.zeros_like(ink)
    ghost[dy:, dx:] = ink[: sh - dy, : sw - dx]
    sheet[ghost & ~ink] = PINK
    sheet[ink] = INK

    sheet_img = Image.fromarray(sheet).convert("RGBA")
    sheet_img.putalpha(engine.create_organic_torn_mask(sw, sh, 7, 6, seed=11))

    shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    shadow.putalpha(sheet_img.split()[3].point(lambda a: int(a * 0.55)))
    shadow_bg = Image.new("RGBA", shadow.size, (0, 0, 0, 255))
    shadow_bg.putalpha(shadow.split()[3])

    angle = -6
    sheet_rot = sheet_img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    shadow_rot = shadow_bg.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    px, py = (n - sheet_rot.width) // 2, int((n - sheet_rot.height) // 2 + n * 0.005)
    off = max(1, int(n * 0.020))

    layer = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    layer.paste(shadow_rot, (px + off, py + off), shadow_rot)
    layer.paste(sheet_rot, (px, py), sheet_rot)

    # обрезаем всё по скруглённой плашке
    tile_mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(tile_mask).rounded_rectangle([0, 0, n - 1, n - 1], radius=radius, fill=255)
    layer.putalpha(Image.fromarray(np.minimum(np.array(layer.split()[3]), np.array(tile_mask))))
    canvas.alpha_composite(layer)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    engine = ZineGraphicEngine()
    frames = {s: render_icon(engine, s) for s in SIZES}
    frames[256].save(os.path.join(here, "icon.png"))
    frames[256].save(
        os.path.join(here, "icon.ico"),
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=[frames[s] for s in SIZES if s != 256],
    )
    print("icon.ico и icon.png созданы:", ", ".join(f"{s}px" for s in SIZES))


if __name__ == "__main__":
    main()
