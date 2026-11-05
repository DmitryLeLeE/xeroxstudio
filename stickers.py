"""Библиотека стикеров: векторные примитивы в квадрате 100x100. Общая для десктопа и браузера
(web/app/js/config.js генерируется из этого файла). Режимы: f - заливка цветом слоя, s - контур,
p - заливка цветом бумаги (для «вырезов»), k - контур цветом бумаги."""
import math


def _r(x):
    """Двойное округление: одинаковый результат на любой платформе (sin/cos различаются в последних битах)."""
    return round(round(x, 6), 1)


def _poly(p, m="f"):
    return {"t": "poly", "p": [[_r(x), _r(y)] for x, y in p], "m": m}


def _circle(cx, cy, r, m="f"):
    return {"t": "circle", "c": [_r(cx), _r(cy)], "r": _r(r), "m": m}


def _line(p, w=6):
    return {"t": "line", "p": [[_r(x), _r(y)] for x, y in p], "w": w}


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
    # андеграунд
    "skull": ("Череп", "Skull", [_circle(50, 42, 34), _poly([(30, 60), (70, 60), (66, 90), (34, 90)]), _circle(37, 44, 9, "p"), _circle(63, 44, 9, "p"),
                                 _poly([(50, 54), (44, 66), (56, 66)], "p")] + [_poly([(x, 78), (x + 3, 78), (x + 3, 90), (x, 90)], "p") for x in (41, 48, 55)]),
    "anarchy": ("Анархия", "Anarchy", [_circle(50, 50, 42, "s"), _line([(28, 86), (50, 14), (72, 86)], 8), _line([(14, 56), (86, 40)], 7), _line([(36, 66), (66, 66)], 6)]),
    "copy": ("Штамп COPY", "COPY stamp", [_poly([(6, 26), (94, 26), (94, 74), (6, 74)]), _text("COPY", 50, 52, 30)]),
    "diy": ("DIY", "DIY", [_poly([(6, 22), (94, 22), (94, 78), (6, 78)]), _poly([(11, 27), (89, 27), (89, 73), (11, 73)], "k"), _text("DIY", 50, 52, 34)]),
    "pin": ("Булавка", "Safety pin", [_circle(20, 50, 12, "s"), _line([(20, 38), (80, 38)], 5), _line([(20, 62), (80, 62)], 5), _line([(80, 38), (90, 44), (90, 56), (80, 62)], 5)]),
    "nosign": ("Запрет", "No sign", [_circle(50, 50, 42, "s"), _line([(21, 21), (79, 79)], 9)]),
    "crown": ("Корона", "Crown", [_poly([(10, 80), (10, 34), (30, 56), (50, 20), (70, 56), (90, 34), (90, 80)]), _circle(10, 30, 5), _circle(50, 14, 5), _circle(90, 30, 5)]),
    "dead": ("Мёртвая рожица", "Dead face", [_circle(50, 50, 42, "s"), _line([(28, 34), (44, 50)], 6), _line([(44, 34), (28, 50)], 6), _line([(56, 34), (72, 50)], 6), _line([(72, 34), (56, 50)], 6), _line([(30, 72), (38, 66), (46, 74), (54, 66), (62, 74), (70, 68)], 6)]),
    "cassette": ("Кассета", "Cassette", [_poly([(6, 22), (94, 22), (94, 78), (6, 78)], "s"), _circle(32, 46, 9, "s"), _circle(68, 46, 9, "s"), _poly([(26, 64), (74, 64), (68, 78), (32, 78)], "s")]),
    "peace": ("Пацифик", "Peace", [_circle(50, 50, 42, "s"), _line([(50, 8), (50, 92)], 6), _line([(50, 50), (20, 80)], 6), _line([(50, 50), (80, 80)], 6)]),
    "warning": ("Осторожно", "Warning", [_poly([(50, 8), (94, 86), (6, 86)], "s"), _line([(50, 36), (50, 60)], 9), _circle(50, 73, 5)]),
    "vinyl": ("Пластинка", "Vinyl", [_circle(50, 50, 44, "s"), _circle(50, 50, 30, "s"), _circle(50, 50, 13), _circle(50, 50, 3, "p")]),
}
