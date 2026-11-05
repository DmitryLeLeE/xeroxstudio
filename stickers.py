"""Библиотека стикеров: векторные примитивы в квадрате 100x100. Общая для десктопа и браузера
(web/app/js/config.js генерируется из этого файла). Режимы: f - заливка цветом слоя, s - контур,
p - заливка цветом бумаги (для «вырезов»), k - контур цветом бумаги."""
import math


def _poly(p, m="f"):
    return {"t": "poly", "p": [[round(x, 1), round(y, 1)] for x, y in p], "m": m}


def _circle(cx, cy, r, m="f"):
    return {"t": "circle", "c": [cx, cy], "r": r, "m": m}


def _line(p, w=6):
    return {"t": "line", "p": [[round(x, 1), round(y, 1)] for x, y in p], "w": w}


def _text(s, cx, cy, h):
    return {"t": "text", "s": s, "c": [cx, cy], "h": h}


def _star(n, r_out, r_in, cx=50, cy=50, rot=-90):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 180.0 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _heart():
    pts = []
    for i in range(60):
        t = math.pi * 2 * i / 60
        pts.append((50 + 3.1 * 16 * math.sin(t) ** 3, 46 - 3.1 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) + 4))
    return pts


def _spiral():
    return [(50 + (3 + i * 0.52) * math.cos(i * 0.42), 50 + (3 + i * 0.52) * math.sin(i * 0.42)) for i in range(90)]


def _scribble_circle():
    pts = []
    for i in range(70):
        a = i * 0.19
        r = 40 + 5 * math.sin(i * 0.5) - i * 0.03
        pts.append((50 + r * math.cos(a), 50 + r * math.sin(a) * 0.85))
    return pts


def _smile():
    return [(30 + 40 * i / 14.0, 60 + 14 * math.sin(math.pi * i / 14.0)) for i in range(15)]


def _eye_outline():
    top = [(8 + 84 * i / 12.0, 50 - 26 * math.sin(math.pi * i / 12.0)) for i in range(13)]
    bot = [(92 - 84 * i / 12.0, 50 + 26 * math.sin(math.pi * i / 12.0)) for i in range(13)]
    return top + bot


def _flower():
    prims = [_circle(50 + 26 * math.cos(math.radians(a)), 50 + 26 * math.sin(math.radians(a)), 17, "f") for a in range(0, 360, 60)]
    prims.append(_circle(50, 50, 13, "p"))
    return prims


STICKERS = {
    "star": ("Звезда", "Star", [_poly(_star(5, 46, 19))]),
    "burst": ("Взрыв «NEW»", "Burst “NEW”", [_poly(_star(14, 48, 36, rot=-90)), _text("NEW", 50, 52, 26)]),
    "arrow": ("Стрелка", "Arrow", [_poly([(6, 38), (60, 38), (60, 16), (94, 50), (60, 84), (60, 62), (6, 62)])]),
    "smiley": ("Смайл", "Smiley", [_circle(50, 50, 42, "s"), _circle(36, 40, 5), _circle(64, 40, 5), _line(_smile(), 6)]),
    "eye": ("Глаз", "Eye", [_poly(_eye_outline(), "s"), _circle(50, 50, 15), _circle(56, 44, 4, "p")]),
    "bolt": ("Молния", "Lightning", [_poly([(58, 4), (22, 54), (46, 54), (36, 96), (80, 40), (54, 40)])]),
    "heart": ("Сердце", "Heart", [_poly(_heart())]),
    "scissors": ("Ножницы", "Scissors", [_circle(26, 26, 14, "s"), _circle(26, 74, 14, "s"), _line([(36, 34), (92, 76)], 7), _line([(36, 66), (92, 24)], 7)]),
    "cross": ("Крест", "Cross", [_line([(14, 14), (86, 86)], 14), _line([(86, 14), (14, 86)], 14)]),
    "spiral": ("Спираль", "Spiral", [_line(_spiral(), 5)]),
    "scribble": ("Обводка", "Scribble ring", [_line(_scribble_circle(), 5)]),
    "barcode": ("Штрихкод", "Barcode", [_poly([(x, 20), (x + w, 20), (x + w, 80), (x, 80)]) for x, w in ((8, 5), (17, 2), (22, 7), (33, 3), (40, 5), (49, 2), (55, 8), (67, 3), (74, 5), (83, 3), (89, 3))]),
    "flower": ("Цветок", "Flower", _flower()),
    "bubble": ("Облачко", "Speech bubble", [_poly([(8, 12), (92, 12), (92, 66), (58, 66), (30, 90), (36, 66), (8, 66)])]),
    "target": ("Мишень", "Target", [_circle(50, 50, 44, "s"), _circle(50, 50, 28, "s"), _circle(50, 50, 11), _line([(50, 2), (50, 98)], 3), _line([(2, 50), (98, 50)], 3)]),
    "asterisk": ("Звёздочка *", "Asterisk", [_line([(50, 8), (50, 92)], 12), _line([(14, 29), (86, 71)], 12), _line([(14, 71), (86, 29)], 12)]),
}
