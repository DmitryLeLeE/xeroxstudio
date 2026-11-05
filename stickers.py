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


def _arc(cx, cy, r, a0, a1, n=18):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _rect(x0, y0, x1, y1, m="f"):
    return _poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], m)


def _pixels(rows, x0=14, y0=14, u=9):
    """Пиксель-арт из строк: '#' - клетка."""
    out = []
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == "#":
                out.append(_rect(x0 + i * u, y0 + j * u, x0 + (i + 1) * u, y0 + (j + 1) * u))
    return out


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

    # --- Америка и IT
    "usa_badge": ("Звёздный значок", "Star badge", [_circle(50, 50, 44, "s"), _poly(_star(5, 30, 12, cy=53))]),
    "stripes": ("Полосы", "Stripes", [_rect(6, 14 + 14 * i, 94, 24 + 14 * i) for i in range(0, 6, 2)] + [_rect(6, 70, 94, 80)]),
    "cursor": ("Курсор-стрелка", "Mouse cursor", [_poly([(24, 8), (24, 78), (42, 62), (54, 90), (66, 84), (54, 58), (78, 58)])]),
    "terminal": ("Терминал", "Terminal", [_rect(6, 16, 94, 84, "s"), _rect(6, 16, 94, 30), _line([(22, 48), (34, 58), (22, 68)], 6), _line([(42, 70), (62, 70)], 6)]),
    "floppy": ("Дискета", "Floppy disk", [_poly([(10, 10), (80, 10), (90, 20), (90, 90), (10, 90)], "s"), _rect(26, 10, 70, 34), _rect(22, 54, 78, 90, "s")]),
    "wifi": ("Wi-Fi", "Wi-Fi", [_line(_arc(50, 80, 62, -135, -45), 7), _line(_arc(50, 80, 42, -135, -45), 7), _line(_arc(50, 80, 22, -135, -45), 7), _circle(50, 80, 6)]),
    "cloud": ("Облако", "Cloud", [_circle(32, 58, 20), _circle(52, 44, 24), _circle(72, 58, 18), _rect(30, 58, 74, 78)]),
    "bug": ("Баг", "Bug", [_circle(50, 56, 24), _circle(50, 28, 11), _line([(30, 44), (10, 34)], 5), _line([(70, 44), (90, 34)], 5), _line([(28, 58), (8, 58)], 5), _line([(72, 58), (92, 58)], 5), _line([(32, 72), (14, 84)], 5), _line([(68, 72), (86, 84)], 5), _line([(50, 36), (50, 80)], 4)]),
    "lock": ("Замок", "Padlock", [_line(_arc(50, 40, 20, 180, 360) + [(70, 52)], 8), _rect(22, 46, 78, 90), _circle(50, 66, 6, "p")]),
    "pixel_heart": ("Пиксельное сердце", "Pixel heart", _pixels([".##.##.", "#######", "#######", "#######", ".#####.", "..###..", "...#..."], 18, 20, 9)),
    "hashtag": ("Хэштег", "Hashtag", [_line([(38, 12), (30, 88)], 9), _line([(66, 12), (58, 88)], 9), _line([(14, 36), (88, 36)], 9), _line([(12, 64), (86, 64)], 9)]),
    "at": ("Собака @", "At sign", [_circle(50, 50, 44), _text("@", 50, 52, 66)]),
    "sheriff": ("Шерифская звезда", "Sheriff badge", [_poly(_star(6, 46, 30)), _circle(50, 50, 14, "p")] + [_circle(50 + 46 * math.cos(math.radians(-90 + 60 * i)), 50 + 46 * math.sin(math.radians(-90 + 60 * i)), 6) for i in range(6)]),
    "open_sign": ("Вывеска OPEN", "OPEN sign", [_rect(6, 24, 94, 76), _rect(11, 29, 89, 71, "k"), _text("OPEN", 50, 51, 21)]),
    "route66": ("Шоссе 66", "Route 66", [_poly([(50, 6), (90, 18), (86, 62), (50, 94), (14, 62), (10, 18)]), _text("66", 50, 46, 38)]),
    "dollar": ("Доллар", "Dollar", [_circle(50, 50, 44), _text("$", 50, 52, 62)]),
    "rocket": ("Ракета", "Rocket", [_poly([(50, 4), (66, 30), (66, 70), (34, 70), (34, 30)]), _circle(50, 38, 8, "p"), _poly([(34, 52), (16, 76), (34, 70)]), _poly([(66, 52), (84, 76), (66, 70)]), _poly([(40, 74), (60, 74), (50, 96)])]),
    "e404": ("Ошибка 404", "Error 404", [_rect(6, 24, 94, 76), _text("404", 50, 51, 34)]),
    "error_window": ("Окно с ошибкой", "Error window", [_rect(8, 14, 92, 86, "s"), _rect(8, 14, 92, 32), _line([(36, 48), (64, 74)], 8), _line([(64, 48), (36, 74)], 8)]),
    "crosshair": ("Прицел", "Crosshair", [_circle(50, 50, 44, "s"), _line([(6, 50), (94, 50)], 4), _line([(50, 6), (50, 94)], 4), _circle(50, 50, 20, "s")]),
    "joystick": ("Джойстик", "Joystick", [_circle(50, 24, 14), _line([(50, 36), (50, 62)], 9), _poly([(14, 86), (86, 86), (78, 62), (22, 62)])]),
    "coffee": ("Кофе", "Coffee", [_poly([(16, 34), (68, 34), (62, 84), (22, 84)]), _line(_arc(70, 56, 16, -90, 90), 7), _line([(30, 8), (36, 24)], 5), _line([(48, 6), (54, 24)], 5)]),
}
