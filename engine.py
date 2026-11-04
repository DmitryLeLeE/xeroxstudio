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

        out = self.add_paper(out, float(st["paper"]), seed + 21, s)
        return Image.fromarray(out), Image.fromarray(bits)
