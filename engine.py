"""
Engine: алгоритмы растрирования, процедурные маски, раскладки страниц, детекция лиц.

render_zine_page() не трогает глобальное состояние (свой генератор случайных чисел
на каждый вызов), поэтому предпросмотр и экспорт дают одинаковый результат.
"""

import math
import os
import random
import sys
import threading

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

import config

LANCZOS = Image.Resampling.LANCZOS
BICUBIC = Image.Resampling.BICUBIC



def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _apply_stain(arr, rng, cx, cy, r, grease, power=1.0):
    """Пятно от кофе (кольцо с тёмным неровным ободком, брызги) или жира (мягкое прозрачное, как на копии).
    Накладывается умножением, поэтому бумага и краска просвечивают."""
    h, w, _ = arr.shape
    half = int(r * (1.35 if grease else 2.0)) + 3
    x0, y0 = int(cx) - half, int(cy) - half
    xa, xb, ya, yb = max(0, x0), min(w, x0 + 2 * half), max(0, y0), min(h, y0 + 2 * half)
    if xb <= xa or yb <= ya:
        return
    ks = (2, 3, 4, 5, 7, 9)
    amp = [rng.uniform(0.02, 0.07) * (1.7 if grease else 1.0) / (k ** 0.5) for k in ks]
    ph = [rng.uniform(0, 6.2832) for _ in ks]
    ring_ph = rng.uniform(0, 6.2832)
    mp = [rng.uniform(0, 6.2832) for _ in range(4)]
    mf = [rng.uniform(3, 7), rng.uniform(3, 7)]
    gx, gy = np.meshgrid(np.arange(xa, xb, dtype=np.float32), np.arange(ya, yb, dtype=np.float32))
    dx, dy = gx - cx, gy - cy
    dist = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)
    rr = np.ones_like(th)
    for k, a, p in zip(ks, amp, ph):
        rr += a * np.cos(k * th + p)
    t = dist / (r * rr)
    mottle = 0.5 + 0.5 * np.sin(dx / r * mf[0] + mp[0]) * np.sin(dy / r * mf[1] + mp[1])
    if grease:
        alpha = 0.36 * (1.0 - _smooth(0.45, 1.0, t)) * (0.8 + 0.4 * mottle)
        alpha += 0.07 * np.exp(-(((t - 0.88) / 0.12) ** 2))
        col = np.array((124, 100, 46), dtype=np.float32)
    else:
        inside = np.clip((1.03 - t) / 0.06, 0.0, 1.0)
        ring = np.exp(-(((t - 0.95) / 0.045) ** 2)) * (0.4 + 0.6 * (0.5 + 0.5 * np.cos(th - ring_ph)))
        alpha = inside * (0.11 + 0.05 * mottle) + ring * 0.62
        alpha += 0.05 * np.exp(-(((t - 1.1) / 0.1) ** 2))
        # брызги вокруг: мелкие кольца
        for _ in range(int(rng.integers(2, 5))):
            ang, dd = rng.uniform(0, 6.2832), r * rng.uniform(1.15, 1.7)
            rd = r * rng.uniform(0.05, 0.13)
            td = np.hypot(gx - (cx + dd * np.cos(ang)), gy - (cy + dd * np.sin(ang))) / rd
            alpha += np.clip((1.05 - td) / 0.1, 0, 1) * 0.2 + np.exp(-(((td - 0.92) / 0.12) ** 2)) * 0.45
        col = np.array((98, 58, 24), dtype=np.float32)
    alpha = np.clip(alpha * power, 0.0, 0.88)[..., None]
    reg = arr[ya:yb, xa:xb]
    arr[ya:yb, xa:xb] = reg * (1.0 - alpha + alpha * col / 255.0)


RANSOM_FONTS = ["Arial Black", "Times New Roman Bold", "Courier New Bold", "Impact", "Rubik Mono One", "Rubik Distressed", "Marck Script"]


def _h01(cx, cy):
    """Скалярная версия того же хеша, что и в JS (hash01)."""
    h = (cx * 374761393 + cy * 668265263) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFF) / 65536.0

# Шрифты без кириллицы -> замена, когда в надписи русский текст (браузер делает это сам).
LATIN_ONLY_FONTS = {"Special Elite": "Courier New Bold", "Permanent Marker": "Rubik Spray Paint"}


class ZineGraphicEngine:

    @staticmethod
    def add_registration_marks(plate):
        """Перекрестия приводки по углам (чёрные = краска) на 1-bit пластине."""
        a = np.array(plate.convert("1"), dtype=bool)  # True = белый
        h, w = a.shape
        m = int(round(min(w, h) * 0.035)); arm = int(round(m * 0.9))
        for cx, cy in ((m, m), (w - 1 - m, m), (m, h - 1 - m), (w - 1 - m, h - 1 - m)):
            for d in range(-arm, arm + 1):
                for x, y in ((cx + d, cy), (cx, cy + d)) + (((cx + d, cy + 1), (cx + 1, cy + d)) if abs(d) < 2 else ()):
                    if 0 <= x < w and 0 <= y < h:
                        a[y, x] = False
        return Image.fromarray(a)

    def render_separations(self, img, state, scale=1.0):
        """Пластины красок для ризографа: [(имя, 1-bit Image)], цвета (бумага, ink1, ink2|None)."""
        _, bits = self.render_zine_page(img, state, scale=scale)
        plates = [("ink1", self.add_registration_marks(bits))]
        if self.last_plate2 is not None:
            plates.append(("ink2", self.add_registration_marks(self.last_plate2)))
        for name, (plate, _rgb) in getattr(self, "last_extra", {}).items():
            plates.append((name, self.add_registration_marks(plate)))
        return plates, self.last_inks

    def __init__(self):
        self.last_plate2 = None
        self.last_inks = None
        self._lock = threading.Lock()  # CascadeClassifier не потокобезопасен
        self.face_cascade = self._load_cascade()
        self._fonts = {}
        self._sample_cache = None  # (key, cv_source, PIL)
        self._placeholder_img = None

    # ------------------------------------------------------------------ ресурсы
    @staticmethod
    def _load_cascade():
        name = "haarcascade_frontalface_default.xml"
        if not hasattr(cv2, "CascadeClassifier"):  # в OpenCV 5.x старый детектор убран
            return None
        here = os.path.dirname(os.path.abspath(__file__))
        paths = [os.path.join(config.resource_path(""), name), os.path.join(here, "assets", name)]
        if hasattr(sys, "_MEIPASS"):
            paths.append(os.path.join(sys._MEIPASS, "cv2", "data", name))
        try:
            paths.append(os.path.join(cv2.data.haarcascades, name))
        except Exception:
            pass
        for p in paths:
            if os.path.exists(p):
                try:
                    cascade = cv2.CascadeClassifier(p)
                except Exception:
                    continue
                if not cascade.empty():
                    return cascade
        return None

    def get_font(self, name, size):
        size = max(6, int(size))
        key = (name, size)
        font = self._fonts.get(key)
        if font is not None:
            return font
        for candidate in [config.FONT_FILES.get(name, "arialbd.ttf")] + config.FONT_FALLBACKS:
            try:
                font = ImageFont.truetype(candidate, size)
                break
            except Exception:
                font = None
        if font is None:
            try:
                font = ImageFont.load_default(size=size)
            except TypeError:
                font = ImageFont.load_default()
        if len(self._fonts) > 64:
            self._fonts.clear()
        self._fonts[key] = font
        return font

    # ------------------------------------------------------------------ примитивы

    @staticmethod
    def _hash01(cx, cy):
        """Целочисленный хеш ячейки -> [0, 1). Тот же алгоритм в web/app/js/engine.js (должен совпадать)."""
        h = cx.astype(np.uint32) * np.uint32(374761393) + cy.astype(np.uint32) * np.uint32(668265263)
        h = (h ^ (h >> np.uint32(13))) * np.uint32(1274126177)
        h = h ^ (h >> np.uint32(16))
        return (h & np.uint32(0xFFFF)).astype(np.float32) / 65536.0

    _BAYER8 = np.array([
        [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
        [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
        [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]], dtype=np.float32)

    @classmethod
    def apply_pattern_dither(cls, gray_pil, kind, dot_size=7, angle=45):
        """Линейные и шумовые растры: lines, cross, stipple, mezzo, bayer. bool: True = бумага, False = краска."""
        g = np.asarray(gray_pil, dtype=np.uint8).astype(np.float32) / 255.0
        h, w = g.shape
        ds = float(max(2.0, dot_size))
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        dark = 1.0 - g
        if kind in ("lines", "cross"):
            rad = math.radians(angle)
            c, sn = math.cos(rad), math.sin(rad)
            yr = xs * sn + ys * c
            d1 = np.abs(yr - np.round(yr / ds) * ds)
            ink = d1 < dark * ds * 0.5
            if kind == "cross":
                xr = xs * c - ys * sn
                d2 = np.abs(xr - np.round(xr / ds) * ds)
                ink |= d2 < np.maximum(0.0, dark - 0.5) * ds
            return ~ink
        if kind == "bayer":
            cell = max(1, int(round(ds / 3.0)))
            bx = (xs.astype(np.int32) // cell) % 8
            by = (ys.astype(np.int32) // cell) % 8
            thr = (cls._BAYER8[by, bx] + 0.5) / 64.0
            return ~(dark > thr)
        cell = max(1, int(round(ds / 2.0))) if kind == "stipple" else max(1, int(round(ds / 5.0)))
        cx = (xs.astype(np.int32) // cell)
        cy = (ys.astype(np.int32) // cell)
        return ~(dark > cls._hash01(cx, cy))

    @staticmethod
    def apply_halftone_dots(gray_pil, dot_size=7, angle=45):
        """Амплитудный растр. Возвращает bool-массив: True = бумага, False = краска.
        Считается полосами по 256 строк, чтобы на больших экспортах не раздувалась память."""
        arr = np.asarray(gray_pil, dtype=np.uint8)
        h, w = arr.shape
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        ds = float(max(2.0, dot_size))
        max_r = ds * 0.7071

        xs = np.arange(w, dtype=np.float32)[None, :]
        out = np.empty((h, w), dtype=bool)
        for y0 in range(0, h, 256):
            y1 = min(h, y0 + 256)
            ys = np.arange(y0, y1, dtype=np.float32)[:, None]
            xr = xs * cos_a - ys * sin_a
            yr = xs * sin_a + ys * cos_a
            dx = xr - np.round(xr / ds) * ds
            dy = yr - np.round(yr / ds) * ds
            threshold = (1.0 - arr[y0:y1].astype(np.float32) / 255.0) * max_r
            out[y0:y1] = np.sqrt(dx * dx + dy * dy) >= threshold
        return out

    @staticmethod
    def create_organic_torn_mask(w, h, rough_x, rough_y, seed=0):
        if rough_x <= 0 and rough_y <= 0:
            return Image.new("L", (w, h), 255)

        x = np.linspace(0, 1, w, dtype=np.float32)
        y = np.linspace(0, 1, h, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)
        dist_x = np.minimum(xx, 1.0 - xx)
        dist_y = np.minimum(yy, 1.0 - yy)

        fx = max(0.005, (rough_x / 100.0) * 0.40)
        fy = max(0.005, (rough_y / 100.0) * 0.45)
        base_ramp = np.minimum(np.clip(dist_x / fx, 0.0, 1.0), np.clip(dist_y / fy, 0.0, 1.0))

        rng = np.random.RandomState(int(seed) % (2 ** 31))
        sw1, sh1 = max(3, w // 24), max(3, h // 24)
        noise = rng.uniform(-0.35, 0.35, (sh1, sw1)).astype(np.float32)
        noise = cv2.resize(noise, (w, h), interpolation=cv2.INTER_CUBIC)

        noisy = np.clip(base_ramp + noise * (1.0 - base_ramp * 0.7), 0.0, 1.0)
        noisy = noisy * noisy * (3.0 - 2.0 * noisy)
        return Image.fromarray((noisy * 255.0).astype(np.uint8))

    def apply_censor_bar(self, img_pil):
        if not self.face_cascade:
            return img_pil
        gray = cv2.cvtColor(np.array(img_pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
        k = min(1.0, 900.0 / max(gray.shape))
        small = cv2.resize(gray, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k < 1.0 else gray
        with self._lock:
            faces = self.face_cascade.detectMultiScale(small, 1.1, 4, minSize=(24, 24))
        if len(faces) == 0:
            return img_pil

        out = img_pil.convert("RGB")
        draw = ImageDraw.Draw(out)
        for fx, fy, fw, fh in faces / k:
            pad = fw * 0.06
            draw.rectangle(
                [fx - pad, fy + fh * 0.28, fx + fw + pad, fy + fh * 0.48], fill=(0, 0, 0)
            )
        return out

    @staticmethod
    def create_sticker_cutout(img_pil):
        """Тёмный объект на светлом фоне -> вырезка с белым полем и чёрным контуром."""
        arr = np.array(img_pil.convert("RGB"))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        k = max(1, int(max(gray.shape) / 500))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        halo = cv2.dilate(mask, kernel, iterations=4)
        ring = cv2.dilate(halo, kernel, iterations=1)

        h, w = mask.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[ring > 0] = (0, 0, 0, 255)
        rgba[halo > 0] = (255, 255, 255, 255)
        rgba[mask > 0, :3] = arr[mask > 0]
        rgba[mask > 0, 3] = 255
        return Image.fromarray(rgba)

    @staticmethod
    def add_scanner_artifacts(canvas, intensity, seed, s=1.0):
        if intensity <= 0:
            return canvas
        w, h = canvas.size
        overlay = np.full((h, w), 255.0, dtype=np.float32)
        rng = np.random.RandomState(int(seed) % (2 ** 31))
        k = intensity / 100.0

        for _ in range(int(3 + k * 5)):
            x = rng.randint(0, w)
            sw = max(1, int(rng.randint(1, 4) * s))
            overlay[:, max(0, x - sw): min(w, x + sw)] -= rng.uniform(20, 90) * k

        for _ in range(int(k * 120 * max(1.0, s * s * 0.5))):
            dx, dy = rng.randint(0, w), rng.randint(0, h)
            length = int(rng.randint(4, 30) * s)
            overlay[dy: min(h, dy + length), dx] -= rng.uniform(40, 120)

        mask = Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8))
        return ImageChops.multiply(canvas.convert("L"), mask).convert("RGB")

    @staticmethod
    def add_copier_edge(canvas, strength, seed, s=1.0):
        """Тёмная кромка у левого и нижнего края, как от неплотно закрытой крышки ксерокса."""
        if strength <= 0:
            return canvas
        w, h = canvas.size
        rng = np.random.RandomState(int(seed) % (2 ** 31))
        band = max(2.0, w * 0.045 * strength / 100.0)

        def wobble(n):  # неровная ширина кромки вдоль края
            knots = max(4, n // int(24 * max(s, 0.5)))
            return np.interp(np.arange(n), np.linspace(0, n - 1, knots), rng.uniform(0.55, 1.45, knots)).astype(np.float32)

        left = np.clip(1.0 - np.arange(w, dtype=np.float32)[None, :] / (band * wobble(h)[:, None]), 0, 1)
        bottom = np.clip(1.0 - (h - 1 - np.arange(h, dtype=np.float32))[:, None] / (band * 0.7 * wobble(w)[None, :]), 0, 1)
        dark = np.maximum(left, bottom)
        gray = np.asarray(canvas.convert("L"), dtype=np.float32) * (1.0 - dark)
        return Image.fromarray(gray.astype(np.uint8)).convert("RGB")


    @staticmethod
    def add_tape(canvas, boxes, amount, seed, s=1.0):
        """Полоски малярного скотча на кадрах: рисуются в серой зоне и потом превращаются в растр."""
        if amount <= 0:
            return canvas
        rng = random.Random(int(seed))
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        p = amount / 100.0

        def strip(cx, cy, ang):
            length, wid = rng.uniform(64, 96) * s, rng.uniform(20, 28) * s
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            nz = max(1.0, 2.5 * s)
            pts = []
            for u, v in ((-1, -1), (-1, -0.33), (-1, 0.33), (-1, 1), (1, 1), (1, 0.33), (1, -0.33), (1, -1)):
                jx = rng.uniform(-nz, nz) if abs(u) == 1 and abs(v) != 1 else 0.0  # рваные торцы
                x, y = u * length / 2 + jx, v * wid / 2
                pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
            d.polygon(pts, fill=(178, 178, 178, 235))

        for bx, by, bw, bh in boxes:
            if bw < 4 or bh < 4:
                continue
            if rng.random() < p:
                strip(bx + bw / 2 + rng.uniform(-0.1, 0.1) * bw, by + 4 * s, rng.uniform(-9, 9))
            for cx, cy, base in ((bx + 6 * s, by + 6 * s, -40), (bx + bw - 6 * s, by + bh - 6 * s, -40), (bx + bw - 6 * s, by + 6 * s, 40), (bx + 6 * s, by + bh - 6 * s, 40)):
                if rng.random() < p * 0.35:
                    strip(cx, cy, base + rng.uniform(-8, 8))
        out = canvas.convert("RGBA")
        out.alpha_composite(layer)
        return out.convert("RGB")

    def add_wear(self, img, st, seed, s=1.0):
        """Износ листа: пятна, пыль и волоски, сгиб, дырки от дырокола, штамп. img - RGB Image."""
        stains, dust, fold = float(st.get("stains", 0)), float(st.get("dust", 0)), float(st.get("fold", 0))
        holes, stamp = int(st.get("holes", 0)), str(st.get("stamp", "") or "").replace("\n", " ").strip()
        if not (stains > 0 or dust > 0 or fold > 0 or holes or stamp):
            return img
        w, h = img.size
        rng = np.random.default_rng(int(seed))
        base = img.convert("RGBA")
        m = min(w, h)

        if stains > 0:
            arr = np.asarray(base.convert("RGB"), dtype=np.float32)
            for i in range(1 + int(stains / 25)):
                cx, cy = rng.uniform(0.1, 0.9) * w, rng.uniform(0.1, 0.9) * h
                r = rng.uniform(0.04, 0.1) * m * (0.6 + stains / 100)
                _apply_stain(arr, rng, cx, cy, r, grease=(i % 2 == 1), power=0.55 + stains / 220.0)
            base = Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

        if dust > 0:
            layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            for _ in range(int(dust * w * h / 60000.0)):
                x, y, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.6, 2.2) * s
                d.ellipse([x - r, y - r, x + r, y + r], fill=(20, 20, 20, 200))
            for _ in range(int(dust / 20)):
                x, y = rng.uniform(0, w), rng.uniform(0, h)
                pts = [(x, y)]
                for _ in range(5):
                    x += rng.normal(0, 14 * s); y += rng.normal(0, 14 * s)
                    pts.append((x, y))
                d.line(pts, fill=(30, 30, 30, 170), width=max(1, int(s)))
            base = Image.alpha_composite(base, layer)

        if fold > 0:
            a = np.zeros((h, w), dtype=np.float32)
            for pos, k, horizontal in ((h / 2.0, 1.0, True), (w / 2.0, 0.6, False)):
                if not horizontal and fold < 50:
                    continue
                n = h if horizontal else w
                dist = np.abs(np.arange(n, dtype=np.float32) - pos) / max(2.0, n * 0.025)
                band = np.exp(-dist * dist) * (fold / 100.0) * 70 * k
                a = np.maximum(a, band[:, None] if horizontal else band[None, :])
            layer = np.zeros((h, w, 4), dtype=np.uint8)
            layer[..., 3] = a.astype(np.uint8)
            base = Image.alpha_composite(base, Image.fromarray(layer, "RGBA"))
            hi = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(hi).line([(0, h // 2 + max(2, int(2 * s))), (w, h // 2 + max(2, int(2 * s)))],
                                    fill=(255, 255, 255, int(40 + fold * 1.2)), width=max(1, int(s)))
            base = Image.alpha_composite(base, hi)

        if holes:
            layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            r = 0.014 * w
            for fy in (0.2, 0.5, 0.8):
                cx, cy = 0.05 * w, fy * h
                d.ellipse([cx - r - 2 * s, cy - r - 2 * s, cx + r + 2 * s, cy + r + 2 * s], fill=(0, 0, 0, 40))
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(26, 26, 26, 255))
            base = Image.alpha_composite(base, layer)

        if stamp:
            size = max(14, int(0.06 * w))
            font = self.get_font(st.get("font", "Arial Black"), size)
            tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
            tb = tmp.textbbox((0, 0), stamp.upper(), font=font)
            pad = int(0.02 * w)
            sw, sh = tb[2] - tb[0] + 2 * pad, tb[3] - tb[1] + 2 * pad
            st_img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
            d = ImageDraw.Draw(st_img)
            col = (190, 30, 30, 255)
            d.rectangle([0, 0, sw - 1, sh - 1], outline=col, width=max(3, int(4 * s)))
            d.text((pad - tb[0], pad - tb[1]), stamp.upper(), fill=col, font=font)
            alpha = np.asarray(st_img.split()[3], dtype=np.float32) * (rng.random((sh, sw)) > 0.2) * 0.85
            st_img.putalpha(Image.fromarray(alpha.astype(np.uint8)))
            st_img = st_img.rotate(float(st.get("stamp_rot", -12)), expand=True, resample=Image.BICUBIC)
            px = int(min(max(0, 0.66 * w - st_img.width / 2), max(0, w - st_img.width)))
            py = int(min(max(0, 0.8 * h - st_img.height / 2), max(0, h - st_img.height)))
            layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            layer.paste(st_img, (px, py), st_img)
            base = Image.alpha_composite(base, layer)

        return base.convert("RGB")

    def _sticker_image(self, name, px, color, paper):
        """RGBA-картинка стикера px x px (рисуется в 2x и уменьшается для сглаживания)."""
        import stickers
        spec = stickers.STICKERS.get(name)
        D = max(8, int(px)) * 2
        img = Image.new("RGBA", (D, D), (0, 0, 0, 0))
        if spec is None:
            return img.resize((D // 2, D // 2))
        d = ImageDraw.Draw(img)
        k = D / 100.0
        col, pap = tuple(color) + (255,), tuple(paper) + (255,)
        for pr in spec[2]:
            t, m = pr["t"], pr.get("m", "f")
            fill = col if m in ("f", "s") else pap
            if t == "poly":
                pts = [(x * k, y * k) for x, y in pr["p"]]
                if m in ("f", "p"):
                    d.polygon(pts, fill=fill)
                else:
                    d.line(pts + [pts[0]], fill=fill, width=max(2, int(6 * k)), joint="curve")
            elif t == "circle":
                cx, cy = pr["c"][0] * k, pr["c"][1] * k
                r = pr["r"] * k
                if m in ("f", "p"):
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
                else:
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=fill, width=max(2, int(6 * k)))
            elif t == "line":
                pts = [(x * k, y * k) for x, y in pr["p"]]
                w = max(2, int(pr.get("w", 6) * k))
                d.line(pts, fill=col, width=w, joint="curve")
                for x, y in (pts[0], pts[-1]):
                    d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=col)
            elif t == "text":
                f = self.get_font("Arial Black", int(pr["h"] * k))
                try:
                    d.text((pr["c"][0] * k, pr["c"][1] * k), pr["s"], fill=pap, font=f, anchor="mm")
                except Exception:
                    d.text((pr["c"][0] * k - 20, pr["c"][1] * k - 10), pr["s"], fill=pap, font=f)
        return img.resize((D // 2, D // 2), Image.LANCZOS)

    def _text_layer_image(self, text, fpx, style, font_name, color, paper_rgb, track=0.0, lead=None):
        """Надпись-слой: плашка, лента или обводка. track - добавка между буквами (доля кегля), lead - множитель интервала строк."""
        font = self.get_font(font_name, fpx)
        probe = ImageDraw.Draw(Image.new("L", (1, 1)))
        if track or lead:
            return self._text_layer_spaced(text, fpx, style, font, color, paper_rgb, float(track or 0.0), float(lead or 1.0))
        tb = probe.multiline_textbbox((0, 0), text, font=font, spacing=int(fpx * 0.15))
        pad = int(fpx * 0.3)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        loc = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(loc)
        if style == "box":
            d.rectangle([0, 0, loc.width, loc.height], fill=tuple(paper_rgb) + (255,))
            fill, stroke = tuple(color) + (255,), None
        elif style == "tape":
            d.rectangle([0, 0, loc.width, loc.height], fill=tuple(color) + (255,))
            fill, stroke = tuple(paper_rgb) + (255,), None
        else:
            fill, stroke = tuple(color) + (255,), tuple(paper_rgb) + (255,)
        d.multiline_text((pad - tb[0], pad - tb[1]), text, font=font, fill=fill, spacing=int(fpx * 0.15),
                         stroke_width=max(2, int(fpx * 0.08)) if stroke else 0, stroke_fill=stroke)
        return loc

    @staticmethod
    def _text_layer_spaced(text, fpx, style, font, color, paper_rgb, track, lead):
        """Надпись с ручным трекингом и межстрочным интервалом (как paint() в engine.js)."""
        lines = text.split("\n")
        pad, lh, tr = fpx * 0.3, fpx * 1.15 * lead, fpx * track

        def width(l):
            return sum(font.getlength(ch) for ch in l) + tr * max(0, len(l) - 1) if tr else font.getlength(l)
        tw = max([width(l) for l in lines] + [1])
        bw, bh = int(tw + 2 * pad), int(lh * len(lines) + 2 * pad)
        loc = Image.new("RGBA", (max(bw, 4), max(bh, 4)), (0, 0, 0, 0))
        d = ImageDraw.Draw(loc)
        if style == "box":
            d.rectangle([0, 0, loc.width, loc.height], fill=tuple(paper_rgb) + (255,))
            fill, stroke = tuple(color) + (255,), None
        elif style == "tape":
            d.rectangle([0, 0, loc.width, loc.height], fill=tuple(color) + (255,))
            fill, stroke = tuple(paper_rgb) + (255,), None
        else:
            fill, stroke = tuple(color) + (255,), tuple(paper_rgb) + (255,)
        sw = max(2, int(fpx * 0.08)) if stroke else 0
        for i, l in enumerate(lines):
            y, x = pad + i * lh, pad
            if not tr:
                d.text((x, y), l, font=font, fill=fill, stroke_width=sw, stroke_fill=stroke)
                continue
            for ch in l:
                d.text((x, y), ch, font=font, fill=fill, stroke_width=sw, stroke_fill=stroke)
                x += font.getlength(ch) + tr
        return loc

    def _ransom_image(self, text, fpx, color, paper_rgb, accent):
        """«Записка из газетных букв»: у каждой буквы свой клочок, шрифт, размер и наклон (раскладка как в JS)."""
        paper, color, accent = tuple(paper_rgb), tuple(color), tuple(accent)
        lines, rows, n = text.split("\n"), [], 0
        for l in lines:
            row = []
            for ch in l:
                i = n
                n += 1
                if ch == " ":
                    row.append({"sp": True, "w": fpx * 0.45})
                    continue
                fname = RANSOM_FONTS[int(_h01(i, 11) * len(RANSOM_FONTS))]
                sz = max(6, int(round(fpx * (0.78 + 0.5 * _h01(i, 12)))))
                font = self.get_font(fname, sz)
                try:
                    cw = font.getlength(ch)
                except Exception:
                    cw = sz * 0.6
                pad = sz * 0.16
                row.append({"ch": ch, "font": font, "sz": sz, "rot": (_h01(i, 13) - 0.5) * 0.28, "mode": _h01(i, 14),
                            "dy": (_h01(i, 15) - 0.5) * 0.22 * fpx, "w": cw + 2 * pad, "h": sz * 1.05 + 2 * pad})
            rows.append(row)
        lh = fpx * 1.55
        adv = lambda it: it["w"] - (0 if it.get("sp") else fpx * 0.02)
        maxw = max([sum(adv(it) for it in r) for r in rows] + [1])
        W, H = int(maxw + fpx * 0.8), int(lh * len(rows) + fpx * 0.8)
        out = Image.new("RGBA", (max(W, 4), max(H, 4)), (0, 0, 0, 0))
        for ri, row in enumerate(rows):
            x = (out.width - sum(adv(it) for it in row)) / 2
            for it in row:
                if it.get("sp"):
                    x += it["w"]
                    continue
                inv = 0.45 <= it["mode"] < 0.75
                acc = 0.75 <= it["mode"] < 0.9
                bg = color if inv else accent if acc else paper
                fg = paper if (inv or acc) else color
                tw, th = int(it["w"]) + 2, int(it["h"]) + 2
                tile = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
                d = ImageDraw.Draw(tile)
                d.rectangle([1, 1, tw - 2, th - 2], fill=bg + (255,), outline=None if (inv or acc) else (80, 80, 80, 255))
                d.text((tw / 2, th / 2 + it["sz"] * 0.05), it["ch"], fill=fg + (255,), font=it["font"], anchor="mm")
                tile = tile.rotate(-math.degrees(it["rot"]), expand=True, resample=Image.BICUBIC)
                cx, cy = x + it["w"] / 2, fpx * 0.4 + ri * lh + lh / 2 + it["dy"]
                out.alpha_composite(tile, (max(0, int(cx - tile.width / 2)), max(0, int(cy - tile.height / 2))))
                x += adv(it)
        return out

    @staticmethod
    def _wear_sticker(loc, seed):
        """Износ стикера: пропуски тонера, пятна, царапины. Те же формулы, что wearSticker в engine.js."""
        W, H = loc.size
        px = float(W)
        mask = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(mask)
        u = max(1.2, px / 150.0)
        n = min(1600, int(px * px / 40))
        k = seed * 100
        for i in range(n):
            x, y = _h01(i, k + 21) * W, _h01(i, k + 22) * H
            r = (0.4 + _h01(i, k + 23) ** 2 * 1.6) * u
            d.ellipse([x - r, y - r, x + r, y + r], fill=int(255 * (0.55 + 0.45 * _h01(i, k + 24))))
        for j in range(9):  # пятна, где краска стёрлась кучнее
            cx, cy = _h01(j, k + 31) * W, _h01(j, k + 32) * H
            for i in range(18):
                a = _h01(i + 100 * j, k + 33) * 6.2832
                rr = _h01(i + 100 * j, k + 34) * px * 0.1
                r = (0.8 + _h01(i + 100 * j, k + 35) * 2.2) * u
                x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
                d.ellipse([x - r, y - r, x + r, y + r], fill=204)
        for j in range(10):  # выцветшие места: мягкие полупрозрачные пятна
            x, y = _h01(j, k + 51) * W, _h01(j, k + 52) * H
            r = px * (0.03 + _h01(j, k + 53) * 0.06)
            d.ellipse([x - r, y - r, x + r, y + r], fill=70)
        for j in range(5):  # царапины
            x, y = _h01(j, k + 41) * W, _h01(j, k + 42) * H
            a, ln = _h01(j, k + 43) * 6.2832, px * (0.2 + _h01(j, k + 44) * 0.4)
            d.line([x, y, x + math.cos(a) * ln, y + math.sin(a) * ln], fill=230, width=max(1, int(round(px / 220))))
        arr = np.asarray(loc, dtype=np.float32).copy()
        arr[..., 3] *= 1.0 - np.asarray(mask, dtype=np.float32) / 255.0
        return Image.fromarray(arr.astype(np.uint8), "RGBA")

    @staticmethod
    def add_mechanism(img, st, seed, s=1.0):
        """Механика копира: заедание бумаги, эхо барабана, полосы тонера. Те же формулы, что addMechanism в engine.js."""
        ghost, bands, smear = float(st.get("ghost", 0) or 0), float(st.get("bands", 0) or 0), float(st.get("smear", 0) or 0)
        gutter, recopy = float(st.get("gutter", 0) or 0), float(st.get("recopy", 0) or 0)
        if not (ghost > 0 or bands > 0 or smear > 0 or gutter > 0 or recopy > 0):
            return img
        arr = np.asarray(img.convert("RGB"), dtype=np.float32).copy()
        h, w = arr.shape[:2]
        if smear > 0:
            y0 = int((0.15 + 0.65 * _h01(int(seed), 97)) * h)
            hb = max(3, int((0.02 + 0.07 * smear / 100.0) * h))
            arr[y0:y0 + min(hb, h - y0)] = arr[y0].copy()
        if ghost > 0:
            dy, dx = int(h * 0.31), int(4 * s)
            sh = np.full_like(arr, 255.0)
            rolled = np.roll(arr, dy, axis=0)
            sh[:, dx:] = rolled[:, :w - dx] if dx else rolled
            a = 0.38 * ghost / 100.0
            arr = arr * (1.0 - a) + a * arr * sh / 255.0
        if bands > 0:
            P = h / (5 + 3 * _h01(int(seed), 98))
            phase = _h01(int(seed), 99) * 2 * math.pi
            y = np.arange(h, dtype=np.float32)
            a = (bands / 100.0) * 0.2 * (0.5 + 0.5 * np.sin(2 * math.pi * y / P + phase))
            arr = arr * (1.0 - a)[:, None, None]
        if gutter > 0:  # тёмный корешок по центру, как при копировании разворота книги
            x = np.arange(w, dtype=np.float32)
            sig = w * (0.02 + 0.05 * gutter / 100.0)
            a = 0.9 * gutter / 100.0 * np.exp(-(((x - w * 0.5) / sig) ** 2))
            arr = arr * (1.0 - a)[None, :, None]
        if recopy > 0:  # лист пересняли несколько раз: каждый проход мутнее, контрастнее и теряет тонер
            passes = 1 + int(recopy // 35)
            kc = 1.10 + 0.14 * recopy / 100.0
            for _ in range(passes):
                p = np.pad(arr, ((0, 0), (1, 1), (0, 0)), mode="edge")
                arr = (p[:, :-2] + 2 * p[:, 1:-1] + p[:, 2:]) / 4.0
                p = np.pad(arr, ((1, 1), (0, 0), (0, 0)), mode="edge")
                arr = (p[:-2] + 2 * p[1:-1] + p[2:]) / 4.0
                arr = np.clip((arr - 128.0) * kc + 128.0, 0, 255)
                arr = 255.0 - (255.0 - arr) * 0.97
        return Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8), "RGB")

    @staticmethod
    def _warp_image(loc, kind, k, bh=None):
        """Искажение надписи по столбцам. loc - RGBA, поля сверху и снизу добавляются здесь. Как warpCanvas в engine.js."""
        bh = bh or loc.height
        m = int(math.ceil(bh * (0.15 + k * 0.9)))
        W, H = loc.width, loc.height + 2 * m
        src = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        src.paste(loc, (0, m))
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for x in range(W):
            t = ((x + 0.5) / W) * 2 - 1
            col = src.crop((x, 0, x + 1, H))
            if kind == "bulge":
                sy = 1 + k * 0.8 * (1 - t * t)
                nh = max(1, int(round(H * sy)))
                out.paste(col.resize((1, nh), Image.BILINEAR), (x, int(round((H - nh) / 2))))
                continue
            dy = 0.0
            if kind == "arch":
                dy = -k * bh * 1.1 * (1 - t * t) + k * bh * 0.55
            elif kind == "dip":
                dy = k * bh * 1.1 * (1 - t * t) - k * bh * 0.55
            elif kind == "wave":
                dy = k * bh * 0.55 * math.sin(t * math.pi * 2)
            elif kind == "slant":
                dy = k * bh * 0.7 * t
            out.paste(col, (x, int(round(dy))))
        return out

    @staticmethod
    def _auto_levels(rgb, bright=1.0):
        """2% самых тёмных тонов -> чёрный, 2% самых светлых -> белый; затем гамма яркости. Как autoLevels в engine.js."""
        f = rgb.astype(np.float32)
        g = (f[..., 0] * 299 + f[..., 1] * 587 + f[..., 2] * 114) / 1000
        hist = np.bincount(np.floor(g).astype(np.int64).ravel(), minlength=256)
        cum, n = np.cumsum(hist), g.size
        lo, hi = int(np.argmax(cum >= 0.02 * n)), int(np.argmax(cum >= 0.98 * n))
        out = rgb.astype(np.float32)
        if hi - lo >= 16:
            out = np.clip((out - lo) * (255.0 / (hi - lo)), 0, 255)
        if bright != 1.0:
            out = np.round(255.0 * np.power(out.round() / 255.0, 1.0 / bright))
        return out.astype(np.uint8)

    def photo_mask(self, key, dot=5, contrast=1.6, cutout=False, max_side=720, bright=1.0, cov=0.0):
        """Фото-объект -> маска краски (L, 255 = краска): контраст, растр и (по желанию) вырезка фона. Кэшируется."""
        imgs = getattr(self, "layer_images", None) or {}
        src = imgs.get(key)
        if src is None:
            return None
        cache = self.__dict__.setdefault("_mask_cache", {})
        sig = (key, int(dot), round(float(contrast), 2), bool(cutout), round(float(bright), 2), round(float(cov), 2), id(src))
        if sig in cache:
            return cache[sig]
        arr = np.asarray(src)
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB) if arr.ndim == 3 else cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
        h0, w0 = rgb.shape[:2]
        k = min(1.0, max_side / max(h0, w0))
        if k < 1.0:
            rgb = cv2.resize(rgb, (max(8, round(w0 * k)), max(8, round(h0 * k))), interpolation=cv2.INTER_AREA)
        keep = None
        if cutout:
            keep = np.asarray(self.create_sticker_cutout(Image.fromarray(rgb)))[..., 3] > 0
        rgb = self._auto_levels(rgb, bright)
        pivot = float(np.floor((rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114).mean() + 0.5))
        if cov > 0:
            pivot = float(round((1 - cov) * 235 + cov * pivot))
        f = np.clip((rgb.astype(np.float32) - pivot) * float(contrast) + pivot, 0, 255)
        gray = (0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]).astype(np.uint8)
        bits = self.apply_halftone_dots(Image.fromarray(gray), dot_size=float(dot), angle=45)
        ink = ~bits
        if keep is not None:
            ink &= keep
        mask = Image.fromarray((ink * 255).astype(np.uint8), "L")
        if len(cache) > 24:
            cache.clear()
        cache[sig] = mask
        return mask

    def _bitmap_layer(self, ly, wpx, color, paper, li):
        mask = self.photo_mask(ly.get("img"), ly.get("dot", 5) or 5, ly.get("contrast", 1.6) or 1.6, ly.get("cutout", False), bright=float(ly.get("bright", 1.0) or 1.0), cov=float(ly.get("cov", 0.0) or 0.0))
        if mask is None:
            return None
        wpx = max(8, int(wpx))
        hpx = max(4, round(wpx * mask.height / mask.width))
        m = mask.resize((wpx, hpx), Image.BILINEAR)
        backed = ly.get("backing", True) is not False
        out = Image.new("RGBA", (wpx, hpx), tuple(paper) + (255,) if backed else (0, 0, 0, 0))
        out.paste(Image.new("RGBA", (wpx, hpx), tuple(color) + (255,)), (0, 0), m)
        if backed and ly.get("torn", True) is not False:
            torn = self.create_organic_torn_mask(wpx, hpx, 7, 7, seed=700 + li)
            a = np.asarray(out.getchannel("A"), dtype=np.float32) * np.asarray(torn, dtype=np.float32) / 255.0
            out.putalpha(Image.fromarray(a.astype(np.uint8)))
        return self._wear_sticker(out, li + 1)

    def draw_layers(self, img, st, paper_rgb, ink_rgb, s=1.0):
        """Свободные слои: стикеры и надписи поверх готового листа. Координаты - доли листа."""
        layers = st.get("layers") or []
        if not layers:
            return img
        w, h = img.size
        base = img.convert("RGBA")
        cols = {"ink": tuple(ink_rgb), "paper": tuple(paper_rgb), "ink2": tuple(st.get("ink2", (255, 60, 140))),
                "ink3": tuple(st.get("ink3", (0, 120, 190))), "ink4": tuple(st.get("ink4", (255, 200, 0)))}
        for li, ly in enumerate(layers):
            try:
                if ly.get("hidden"):
                    continue
                color = cols.get(ly.get("color", "ink"), cols["ink"])
                size = max(0.02, float(ly.get("size", 0.2)))
                if ly.get("type") == "sticker":
                    loc = self._sticker_image(ly.get("sticker", "star"), size * w, color, paper_rgb)
                    loc = self._wear_sticker(loc, li + 1)
                elif ly.get("type") == "bitmap":
                    loc = self._bitmap_layer(ly, size * w, color, paper_rgb, li)
                    if loc is None:
                        continue
                elif ly.get("type") == "shape":
                    loc = self._shape_image(ly, size * w, color)
                else:
                    text = str(ly.get("text", "")).strip()
                    if not text:
                        continue
                    fpx = max(8, int(size * w * 0.5))
                    style = ly.get("style", "box")
                    if style == "ransom":
                        loc = self._ransom_image(text, fpx, color, paper_rgb, cols["ink2"])
                    else:
                        fname = ly.get("font", "Arial Black")
                        if fname in LATIN_ONLY_FONTS and any("\u0400" <= ch <= "\u04ff" for ch in text):
                            fname = LATIN_ONLY_FONTS[fname]  # в шрифте нет кириллицы: иначе буквы пропадут
                        loc = self._text_layer_image(text, fpx, style, fname, color, paper_rgb,
                                                     track=max(-0.2, min(1.0, float(ly.get("track", 0) or 0))),
                                                     lead=max(0.6, min(2.5, float(ly.get("lead")))) if ly.get("lead") and abs(float(ly.get("lead")) - 1) > 1e-6 else None)
                        warp = ly.get("warp") or "none"
                        if warp != "none":
                            wk = min(1.0, max(0.0, float(ly.get("warp_k", 0.5) if ly.get("warp_k") is not None else 0.5)))
                            loc = self._warp_image(loc, warp, wk)
                    sx = min(3.0, max(0.4, float(ly.get("sx", 1.0) or 1.0)))
                    if sx != 1.0:
                        loc = loc.resize((max(1, int(round(loc.width * sx))), loc.height), Image.BICUBIC)
                if ly.get("flipx"):
                    loc = loc.transpose(Image.FLIP_LEFT_RIGHT)
                rot = float(ly.get("rot", 0))
                if rot:
                    loc = loc.rotate(-rot, expand=True, resample=Image.BICUBIC)
                opacity = min(1.0, max(0.0, float(ly.get("opacity", 1.0) if ly.get("opacity") is not None else 1.0)))
                if opacity < 1.0:
                    loc = loc.copy()
                    loc.putalpha(loc.getchannel("A").point(lambda v: int(v * opacity)))
                px = int(float(ly.get("x", 0.5)) * w - loc.width / 2)
                py = int(float(ly.get("y", 0.5)) * h - loc.height / 2)
                layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                shd = min(1.0, max(0.0, float(ly.get("shadow", 0) or 0)))
                if shd > 0:  # жёсткая тень без размытия: тот же сдвиг, что shadowOffset в engine.js
                    d = int(round(shd * 0.035 * w))
                    scol = cols.get(ly.get("shadow_c", "ink"), cols["ink"])
                    sh = Image.new("RGBA", loc.size, tuple(scol) + (255,))
                    sh.putalpha(loc.getchannel("A"))
                    layer.paste(sh, (px + d, py + d))  # без маски: иначе альфа возводится в квадрат на полупрозрачных краях
                top = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                top.paste(loc, (px, py))
                layer = Image.alpha_composite(layer, top)
                blend = ly.get("blend", "normal")
                base = self._blend_over(base, layer, blend) if blend in ("multiply", "screen", "difference") else Image.alpha_composite(base, layer)
            except Exception:
                continue
        return base.convert("RGB")

    @staticmethod
    def _blend_over(base, layer, mode):
        """Режимы наложения слоя на лист: multiply, screen, difference (как globalCompositeOperation в canvas)."""
        b = np.asarray(base.convert("RGB"), dtype=np.float32)
        top = np.asarray(layer, dtype=np.float32)
        l, a = top[..., :3], top[..., 3:4] / 255.0
        if mode == "multiply":
            m = b * l / 255.0
        elif mode == "screen":
            m = 255.0 - (255.0 - b) * (255.0 - l) / 255.0
        else:
            m = np.abs(b - l)
        out = b * (1.0 - a) + m * a
        return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    @staticmethod
    def _shape_image(ly, wpx, color):
        """Фигура-слой: rect / ellipse / triangle; заливка solid, outline, stripes, fade (растровое затухание), dots, gradient."""
        W = max(8, int(wpx))
        H = max(4, int(round(W * float(ly.get("aspect", 0.6) or 0.6))))
        S = 2
        W2, H2 = W * S, H * S
        kind, fill = ly.get("shape", "rect"), ly.get("fill", "solid")
        shape = Image.new("L", (W2, H2), 0)
        d = ImageDraw.Draw(shape)
        if kind == "ellipse":
            d.ellipse([0, 0, W2 - 1, H2 - 1], fill=255)
        elif kind == "triangle":
            d.polygon([(W2 / 2, 0), (W2 - 1, H2 - 1), (0, H2 - 1)], fill=255)
        else:
            d.rectangle([0, 0, W2 - 1, H2 - 1], fill=255)
        mask = shape
        if fill == "outline":
            lw = max(2, int(W2 * 0.02))  # обводка шириной 2*lw по краю, обрезанная фигурой: внутрь уходит lw (как clip+stroke в canvas)
            ring = Image.new("L", (W2, H2), 0)
            dr = ImageDraw.Draw(ring)
            if kind == "ellipse":
                dr.ellipse([0, 0, W2 - 1, H2 - 1], outline=255, width=2 * lw)
            elif kind == "triangle":
                pts = [(W2 / 2, 0), (W2 - 1, H2 - 1), (0, H2 - 1), (W2 / 2, 0)]
                dr.line(pts, fill=255, width=2 * lw, joint="curve")
            else:
                dr.rectangle([0, 0, W2 - 1, H2 - 1], outline=255, width=2 * lw)
            mask = ImageChops.multiply(shape, ring)
        elif fill == "stripes":
            pat = Image.new("L", (W2, H2), 0)
            dp = ImageDraw.Draw(pat)
            sp = W2 * 0.06
            t = -float(H2)
            while t < W2 + H2:
                dp.line([(t, H2), (t + H2, 0)], fill=255, width=max(1, int(sp / 2)))
                t += sp
            mask = ImageChops.multiply(shape, pat)
        elif fill == "gradient":  # плавное затухание сверху вниз: альфа 1 -> 0
            ramp = np.tile(np.linspace(255, 0, H2, dtype=np.float32)[:, None], (1, W2))
            mask = ImageChops.multiply(shape, Image.fromarray(ramp.astype(np.uint8), "L"))
        elif fill in ("fade", "dots"):
            pat = Image.new("L", (W2, H2), 0)
            dp = ImageDraw.Draw(pat)
            step = max(5.0, W * 0.022) * S
            j, y = 0, 0.0
            while y <= H2:
                r = step * (0.72 * (1.0 - y / H2) if fill == "fade" else 0.36)
                if r >= 0.8:
                    x = (j % 2) * step / 2
                    while x <= W2:
                        dp.ellipse([x - r, y - r, x + r, y + r], fill=255)
                        x += step
                y += step
                j += 1
            mask = ImageChops.multiply(shape, pat)
        mask = mask.resize((W, H), Image.LANCZOS)
        out = Image.new("RGBA", (W, H), tuple(color) + (255,))
        out.putalpha(mask)
        return out

    @staticmethod
    def add_paper(out, amount, seed, s=1.0):
        """Фактура бумаги: волокна, пятна и лёгкое потемнение к краям. out - uint8 (h, w, 3)."""
        if amount <= 0:
            return out
        h, w = out.shape[:2]
        rng = np.random.default_rng(int(seed))
        k = amount / 100.0
        fine = rng.standard_normal((h, w), dtype=np.float32)
        def field(cell):  # шум с размером пятна cell пикселей
            gh, gw = max(2, int(h / (cell * max(s, 0.5)))), max(2, int(w / (cell * max(s, 0.5))))
            g = rng.standard_normal((gh, gw)).astype(np.float32)
            return np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC), dtype=np.float32)

        blot = 0.35 * field(90) + 0.65 * field(5)  # крупные разводы и мелкие волокна
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        edge = np.maximum(np.abs(xx / w - 0.5), np.abs(yy / h - 0.5)) * 2.0
        shade = 1.0 - k * (0.05 * fine + 0.055 * blot + 0.10 * np.clip(edge - 0.6, 0, 1) ** 2 / 0.16)
        return np.clip(out.astype(np.float32) * shade[..., None], 0, 255).astype(np.uint8)

    def _placeholder(self):
        """Тестовая «пустая» картинка, пока фото не загружено."""
        if self._placeholder_img is None:
            w, h = 600, 800
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            bg = 235.0 - 90.0 * (yy / h)
            r = np.hypot((xx - w * 0.5) / (w * 0.36), (yy - h * 0.40) / (h * 0.27))
            lit = np.hypot((xx - w * 0.40) / (w * 0.36), (yy - h * 0.32) / (h * 0.27))
            sphere = 25.0 + 205.0 * np.clip(1.0 - lit * 0.75, 0, 1) ** 1.3
            img = np.where(r < 1.0, sphere, bg)
            img[::6, :] *= 0.82  # строки развёртки
            pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGB")
            d = ImageDraw.Draw(pil)
            font = self.get_font("Impact", 54)
            label = "NO SIGNAL"
            bb = d.textbbox((0, 0), label, font=font)
            tx = (w - (bb[2] - bb[0])) // 2 - bb[0]
            d.rectangle([tx - 16 + bb[0], 690, tx + bb[2] + 16, 690 + bb[3] - bb[1] + 20], fill=(0, 0, 0))
            d.text((tx, 700 - bb[1]), label, fill=(255, 255, 255), font=font)
            self._placeholder_img = pil
        return self._placeholder_img

    def _get_sample(self, cv_source, st):
        if cv_source is None:
            return self._placeholder()
        crop = tuple(float(v) for v in st["crop"])
        key = (crop, bool(st["censor"]), bool(st["sticker"]))
        cache = self._sample_cache
        if cache and cache[1] is cv_source and cache[0] == key:
            return cache[2]

        ih, iw = cv_source.shape[:2]
        x1, y1, x2, y2 = (min(max(v, 0.0), 1.0) for v in crop)
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        ix1, ix2, iy1, iy2 = int(x1 * iw), int(x2 * iw), int(y1 * ih), int(y2 * ih)
        if ix2 - ix1 < 8 or iy2 - iy1 < 8:
            ix1, iy1, ix2, iy2 = 0, 0, iw, ih
        pil = Image.fromarray(cv2.cvtColor(cv_source[iy1:iy2, ix1:ix2], cv2.COLOR_BGR2RGB))
        if st["censor"]:
            pil = self.apply_censor_bar(pil)
        if st["sticker"]:
            pil = self.create_sticker_cutout(pil)
        self._sample_cache = (key, cv_source, pil)
        return pil

    # ------------------------------------------------------------------ раскладки
    @staticmethod
    def _layout_boxes(layout, cw, ch, rows, ext, s):
        """Список (x, y, w, h) для каждого кадра страницы."""
        rows = max(1, int(rows))
        boxes = []
        if layout == "staggered":
            col_w, row_h = int(cw * 0.58), ch // rows
            for r in range(rows):
                x = int(cw * 0.05) if r % 2 == 0 else int(cw * 0.37)
                boxes.append((x, r * row_h, col_w, row_h + ext))
        elif layout == "column":
            col_w, row_h = int(cw * 0.46), ch // rows
            for r in range(rows):
                boxes.append((int(cw * 0.05), r * row_h, col_w, row_h + ext))
        elif layout == "contact_sheet":
            cols = 3
            margin, gap = int(cw * 0.04), max(2, int(cw * 0.012))
            tw = (cw - 2 * margin - (cols - 1) * gap) // cols
            th = (ch - 2 * margin - (rows - 1) * gap) // rows
            for r in range(rows):
                for c in range(cols):
                    boxes.append((margin + c * (tw + gap), margin + r * (th + gap), tw, th))
        elif layout == "center_hero":
            boxes.append((int(cw * 0.10), int(ch * 0.12), int(cw * 0.80), int(ch * 0.54)))
            n = min(5, max(3, rows))
            gap = max(2, int(cw * 0.012))
            tw = (int(cw * 0.80) - (n - 1) * gap) // n
            for i in range(n):
                boxes.append((int(cw * 0.10) + i * (tw + gap), int(ch * 0.78), tw, int(ch * 0.14)))
        elif layout == "column_right":
            col_w, row_h = int(cw * 0.46), ch // rows
            for r in range(rows):
                boxes.append((int(cw * 0.49), r * row_h, col_w, row_h + ext))
        elif layout == "diagonal":
            n = min(rows, 8)
            bw = int(cw * 0.5)
            bh = min(ch, int(ch / n * 1.45))
            for r in range(n):
                x = int(cw * 0.04 + cw * 0.42 * (r / (n - 1) if n > 1 else 0.5))
                y = int(r * (ch - bh) / (n - 1)) if n > 1 else 0
                boxes.append((x, y, bw, bh))
        elif layout == "pile":
            n = min(max(2, rows), 6)
            bw, bh = int(cw * 0.62), int(ch * 0.40)
            for i in range(n):
                fx = (i * 618 % 1000) / 1000
                fy = i / (n - 1)
                boxes.append((int((cw - bw) * fx), int((ch - bh) * fy), bw, bh))
        elif layout == "two_columns":
            margin, gap = int(cw * 0.05), max(2, int(cw * 0.02))
            tw, row_h = (cw - 2 * margin - gap) // 2, ch // rows
            for r in range(rows):
                for c in range(2):
                    boxes.append((margin + c * (tw + gap), r * row_h + (row_h // 2 if c else 0), tw, row_h - gap))
        elif layout == "mosaic":
            n = min(max(2, rows), 6)
            gap = max(2, int(cw * 0.012))
            full_w = int(cw * 0.88)
            boxes.append((int(cw * 0.06), int(ch * 0.05), full_w, int(ch * 0.46)))
            tw = (full_w - 2 * gap) // 3
            lines = (n + 2) // 3
            th = (int(ch * 0.40) - (lines - 1) * gap) // lines
            for i in range(n):
                boxes.append((int(cw * 0.06) + (i % 3) * (tw + gap), int(ch * 0.55) + (i // 3) * (th + gap), tw, th))
        elif layout == "duo":
            boxes.append((int(cw * 0.08), int(ch * 0.05), int(cw * 0.84), int(ch * 0.43)))
            boxes.append((int(cw * 0.08), int(ch * 0.52), int(cw * 0.84), int(ch * 0.43)))
        elif layout == "triptych":
            margin, gap = int(cw * 0.04), max(2, int(cw * 0.015))
            tw = (cw - 2 * margin - 2 * gap) // 3
            for c in range(3):
                boxes.append((margin + c * (tw + gap), int(ch * 0.06) + (int(ch * 0.04) if c == 1 else 0), tw, int(ch * 0.82)))
        elif layout == "ribbon":
            n = min(max(3, rows), 6)
            margin, gap = int(cw * 0.04), max(2, int(cw * 0.012))
            tw = (cw - 2 * margin - (n - 1) * gap) // n
            for i in range(n):
                boxes.append((margin + i * (tw + gap), int(ch * 0.38), tw, int(ch * 0.24)))
        elif layout == "full_page":
            boxes.append((0, 0, cw, ch))
        elif layout == "free":
            return boxes  # кадров нет: лист собирается слоями
        else:
            return ZineGraphicEngine._layout_boxes("staggered", cw, ch, rows, ext, s)
        return boxes

    @staticmethod
    def _flatten(img):
        if img.mode != "RGBA":
            return img.convert("RGB")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg

    def _fit_base(self, sample, tw, th, fit_mode, brightness):
        """Кадр нужного размера без маски краёв (общий для всех одинаковых кадров)."""
        if fit_mode == "cover":
            base = ImageOps.fit(self._flatten(sample), (tw, th), method=LANCZOS)
        else:
            scale = min(tw / sample.width, th / sample.height)
            nw, nh = max(1, int(sample.width * scale)), max(1, int(sample.height * scale))
            resized = sample.resize((nw, nh), resample=LANCZOS if scale < 1 else BICUBIC)
            bg = Image.new("RGB", (tw, th), (255, 255, 255))
            bg.paste(resized, ((tw - nw) // 2, (th - nh) // 2), mask=resized.split()[3] if resized.mode == "RGBA" else None)
            base = bg
        if brightness != 1.0:
            base = ImageEnhance.Brightness(base).enhance(brightness)
        return base

    @staticmethod
    def _degrade(img, generation, loss, s):
        """Потеря качества «копии с копии»: каждое следующее поколение мутнее и контрастнее."""
        k = (loss / 100.0) * generation
        if k <= 0:
            return img
        img = img.filter(ImageFilter.GaussianBlur(0.35 * k * s))
        return ImageEnhance.Contrast(img).enhance(1.0 + 0.10 * k)

    # ------------------------------------------------------------------ главный рендер
    def render_zine_page(self, cv_source, state, custom_quote=None, scale=1.0, out_size=None):
        """
        Недеструктивная сборка страницы по словарю состояния.
        scale     - множитель разрешения (для экспорта и миниатюр);
        out_size  - точный размер вывода (w, h); геометрия остаётся пропорциональной.
        Возвращает (RGB-изображение, 1-битный трафарет чёрной краски).
        """
        st = {**config.DEFAULT_STATE, **state}
        st["layout"] = config.LAYOUT_ALIASES.get(st["layout"], st["layout"])

        base_w, base_h = config.CANVAS_FORMATS.get(st["format"], (1000, 1500))
        if out_size:
            cw, ch = int(out_size[0]), int(out_size[1])
            s = cw / float(base_w)
        else:
            s = float(scale)
            cw, ch = max(16, int(base_w * s)), max(16, int(base_h * s))
        canvas = Image.new("RGB", (cw, ch), (255, 255, 255))

        seed = int(st["seed"])
        rng = random.Random(seed)
        rough_x, rough_y = st["edge_x"], st["edge_y"]
        tilt_max = float(st["tilt"])
        ext = int(rough_y * 0.4 * s)

        # --- кадры
        sample = self._get_sample(cv_source, st)
        boxes = self._layout_boxes(st["layout"], cw, ch, st["rows"], ext, s)
        base_cache = {}
        font_label = self.get_font("Courier New Bold", max(8, int(15 * s)))
        draw_canvas = ImageDraw.Draw(canvas)

        for idx, (bx, by, bw, bh) in enumerate(boxes):
            if bw < 4 or bh < 4:
                continue
            if (bw, bh) not in base_cache:
                base_cache[(bw, bh)] = self._fit_base(sample, bw, bh, st["fit_mode"], float(st["bright"]))
            generation = idx  # кадр 0 = оригинал, дальше копии с копий
            tile = self._degrade(base_cache[(bw, bh)], generation, st["loss"], s)

            tile = tile.convert("RGBA")
            tile.putalpha(self.create_organic_torn_mask(bw, bh, rough_x, rough_y, seed=seed + idx * 11))

            if tilt_max > 0:
                rot = tile.rotate(rng.uniform(-tilt_max, tilt_max), resample=BICUBIC, expand=True)
                px = bx + bw // 2 - rot.width // 2
                py = by + bh // 2 - rot.height // 2
                canvas.paste(rot, (px, py), mask=rot.split()[3])
            else:
                canvas.paste(tile, (bx, by), mask=tile.split()[3])

            if st["layout"] == "contact_sheet":  # номер кадра поверх рваного края, как на плёнке
                label = f"{idx + 1:02d}A"
                lb = draw_canvas.textbbox((0, 0), label, font=font_label)
                lx, ly = bx + int(3 * s), by + int(3 * s)
                draw_canvas.rectangle([lx, ly, lx + lb[2] + int(8 * s), ly + lb[3] + int(6 * s)], fill=(255, 255, 255))
                draw_canvas.text((lx + int(4 * s), ly + int(2 * s)), label, fill=(0, 0, 0), font=font_label)

        canvas = self.add_tape(canvas, boxes, float(st["tape"]), seed + 31, s)
        canvas = self.add_scanner_artifacts(canvas, st["streaks"], seed + 7, s)
        canvas = self.add_copier_edge(canvas, st["copier_edge"], seed + 13, s)

        # --- текст
        top_txt, bot_txt = custom_quote if custom_quote else (st["txt_top"], st["txt_bottom"])
        style, align = st["tstyle"], st["text_align"]
        rot_a = float(st["text_rot"])
        measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

        def draw_block(text, y_pct):
            if not text:
                return
            pad_x, pad_y, spacing = int(12 * s), int(8 * s), int(8 * s)
            stroke = max(1, int(3 * s)) if style == "outline" else 0
            size = st["font_size"] * s
            while True:
                font = self.get_font(st["font"], size)
                bb = measure.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align=align, stroke_width=stroke)
                tw, th = math.ceil(bb[2] - bb[0]) + 2 * pad_x, math.ceil(bb[3] - bb[1]) + 2 * pad_y
                if tw <= cw * 0.94 or size <= 10 * s:
                    break
                size *= 0.9  # длинная строка: уменьшаем, чтобы не вылезла за край листа
            layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            origin = (pad_x - bb[0], pad_y - bb[1])
            if style == "dymo_tape":
                d.rectangle([0, 0, tw, th], fill=(0, 0, 0, 255))
                d.multiline_text(origin, text, fill=(255, 255, 255, 255), font=font, spacing=spacing, align=align)
            elif style == "outline":
                d.multiline_text(origin, text, fill=(0, 0, 0, 255), font=font, spacing=spacing, align=align,
                                 stroke_width=stroke, stroke_fill=(255, 255, 255, 255))
            else:
                d.rectangle([0, 0, tw, th], fill=(255, 255, 255, 255))
                d.multiline_text(origin, text, fill=(0, 0, 0, 255), font=font, spacing=spacing, align=align)
            if rot_a != 0.0:
                layer = layer.rotate(rot_a, expand=True, resample=BICUBIC)
            x = min(max(0, int(cw * st["txt_x"] / 100.0)), max(0, cw - layer.width))
            y = min(max(0, int(ch * y_pct / 100.0)), max(0, ch - layer.height))
            canvas.paste(layer, (x, y), mask=layer.split()[3])

        draw_block(top_txt, st["txt_y1"])
        draw_block(bot_txt, st["txt_y2"])

        # --- тоновая компрессия и растрирование
        gray = ImageEnhance.Contrast(canvas.convert("L")).enhance(st["contrast"])
        noise_v = st["noise"]
        if noise_v > 0:
            nrng = np.random.default_rng(seed + 1)
            arr = np.asarray(gray, dtype=np.float32)
            arr = arr + nrng.standard_normal(arr.shape, dtype=np.float32) * float(noise_v)
            gray = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

        if st["dither"] == "halftone":
            bits = self.apply_halftone_dots(gray, dot_size=st["dot_size"] * s, angle=st["angle"])
        elif st["dither"] in ("lines", "cross", "stipple", "mezzo", "bayer"):
            bits = self.apply_pattern_dither(gray, st["dither"], dot_size=st["dot_size"] * s, angle=st["angle"])
        elif st["dither"] == "stencil":
            bits = np.asarray(gray.convert("1", dither=Image.Dither.NONE))
        else:
            bits = np.asarray(gray.convert("1", dither=Image.Dither.FLOYDSTEINBERG))

        # --- палитра Riso
        if st["palette"] == config.CUSTOM_PALETTE:
            paper_rgb, ink_rgb = (tuple(c) for c in st["custom_colors"])
        else:
            paper_rgb, ink_rgb = config.RISO_PALETTES.get(st["palette"], config.RISO_PALETTES["Classic B&W (Xerox)"])
        if st["invert"]:
            paper_rgb, ink_rgb = ink_rgb, paper_rgb

        ink = ~bits
        out = np.empty((ch, cw, 3), dtype=np.uint8)
        out[:] = paper_rgb

        misreg = int(round(st["misreg"] * s))
        if misreg > 0:
            # «призрак»: второй проход краски со сдвигом, как при плохой приводке на ризографе
            dx, dy = misreg, max(1, misreg // 2)
            ghost = np.zeros_like(ink)
            ghost[dy:, dx:] = ink[: ch - dy, : cw - dx]
            ghost_rgb = tuple(int(p + (i - p) * 0.45) for p, i in zip(paper_rgb, ink_rgb))
            out[ghost & ~ink] = ghost_rgb
        out[ink] = ink_rgb

        # --- второй цвет (оверпринт): другой экран растра, свой сдвиг, смешение умножением
        over = float(st["overprint"])
        self.last_plate2 = None
        self.last_inks = (paper_rgb, ink_rgb, tuple(st["ink2"]) if over > 0 else None)
        if over > 0:
            k2 = min(1.0, over / 100.0) * 0.9
            lighter = Image.fromarray((255.0 - (255.0 - np.asarray(gray, dtype=np.float32)) * k2).astype(np.uint8))
            bits2 = self.apply_halftone_dots(lighter, dot_size=st["dot_size"] * s * 1.3, angle=(float(st["angle"]) + 30) % 90)
            self.last_plate2 = Image.fromarray(bits2)
            plate = ~bits2
            sx, sy = int(round((3 + st["misreg"]) * s)), int(round((2 + st["misreg"] / 2) * s))
            shifted = np.zeros_like(plate)
            shifted[sy:, :cw - sx] = plate[: ch - sy, sx:]
            ink2 = np.array(st["ink2"], dtype=np.float32)
            region = shifted
            out[region] = (out[region].astype(np.float32) * ink2 / 255.0).astype(np.uint8)

        # --- третья и четвёртая краска: свои тона, углы и сдвиги
        self.last_extra = {}
        g32 = np.asarray(gray, dtype=np.float32)
        m = float(st["misreg"])
        extra = (
            ("ink3", float(st.get("overprint3", 0)), 1.15, 60, (round((2 + m) * s), round((1 + m / 3) * s)),
             lambda g: 1.0 - np.abs(g / 255.0 - 0.5) * 2.0),
            ("ink4", float(st.get("overprint4", 0)), 1.5, 15, (-round((1 + m * 0.5) * s), -round((3 + m) * s)),
             lambda g: np.maximum(0.0, g / 255.0 - 0.35) / 0.65),
        )
        for name, amount, dot_k, ang_k, (dx, dy), tone in extra:
            if amount <= 0:
                continue
            k = min(1.0, amount / 100.0) * 0.9
            t = tone(g32)
            lighter = Image.fromarray((255.0 - 255.0 * np.clip(t, 0, 1) * k).astype(np.uint8))
            bits_x = self.apply_halftone_dots(lighter, dot_size=st["dot_size"] * s * dot_k, angle=(float(st["angle"]) + ang_k) % 90)
            self.last_extra[name] = (Image.fromarray(bits_x), tuple(st[name]))
            plate = ~bits_x
            shifted = np.zeros_like(plate)
            ys0, ys1 = max(0, dy), min(ch, ch + dy)
            xs0, xs1 = max(0, dx), min(cw, cw + dx)
            shifted[ys0:ys1, xs0:xs1] = plate[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
            out[shifted] = (out[shifted].astype(np.float32) * np.array(st[name], dtype=np.float32) / 255.0).astype(np.uint8)

        out = self.add_paper(out, float(st["paper"]), seed + 21, s)
        final = self.add_wear(Image.fromarray(out), st, seed + 51, s)
        final = self.add_mechanism(final, st, seed + 61, s)
        final = self.draw_layers(final, st, paper_rgb, ink_rgb, s)
        return final, Image.fromarray(bits)
