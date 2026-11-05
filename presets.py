"""
Presets: стили оформления страницы (встроенные и пользовательские).

Пресет меняет только «внешний вид» (раскладка, растр, палитра, шрифт). Фото, кадр,
тексты и формат листа остаются прежними.
"""

import json
import os

import appdata
import config

STYLE_KEYS = (
    "layout", "rows", "tilt", "fit_mode", "bright", "edge_x", "edge_y", "loss",
    "dither", "dot_size", "angle", "contrast", "noise", "streaks", "misreg", "copier_edge", "paper", "overprint", "ink2", "overprint3", "ink3", "overprint4", "ink4", "tape", "fold", "holes", "stains", "dust",
    "palette", "invert", "custom_colors",
    "font", "font_size", "tstyle", "text_align", "txt_x", "txt_y1", "txt_y2", "text_rot",
)

BUILTIN = {
    "Классический ксерокс": {
        "layout": "staggered", "rows": 4, "palette": "Classic B&W (Xerox)", "dither": "halftone",
        "dot_size": 7, "contrast": 2.4, "noise": 25, "streaks": 25, "misreg": 2, "loss": 30, "tilt": 0.0, "copier_edge": 35,
    },
    "Газетная печать": {
        "layout": "column", "rows": 5, "palette": "Vintage Newsprint (Cream / Charcoal)", "dither": "halftone",
        "dot_size": 5, "angle": 15, "contrast": 1.8, "noise": 38, "streaks": 12, "misreg": 1, "loss": 18, "copier_edge": 15,
        "edge_x": 8, "edge_y": 6, "font": "Times New Roman Bold", "tstyle": "white_box",
    },
    "Кислотный райот": {
        "layout": "staggered", "rows": 5, "palette": "Acid Cyberpunk (Neon Lime / Black)", "dither": "halftone",
        "dot_size": 9, "contrast": 2.8, "noise": 20, "streaks": 30, "misreg": 5, "loss": 45, "tilt": 2.2,
        "font": "Impact", "font_size": 44, "tstyle": "dymo_tape",
    },
    "Панк-флаер": {
        "layout": "center_hero", "rows": 4, "palette": "Hot Pink Riot (Fluo Pink / Black)", "dither": "halftone",
        "dot_size": 11, "contrast": 3.0, "noise": 30, "streaks": 35, "misreg": 6, "loss": 55, "tilt": 3.0,
        "font": "Impact", "font_size": 52, "tstyle": "white_box", "edge_x": 22, "edge_y": 16,
    },
    "Синька (cyanotype)": {
        "layout": "contact_sheet", "rows": 5, "palette": "Blueprint / Cyanotype (Navy / Cyan)", "dither": "floyd",
        "dot_size": 6, "contrast": 2.0, "noise": 14, "streaks": 10, "misreg": 1, "loss": 22,
        "font": "Courier New Bold", "font_size": 30, "tstyle": "dymo_tape",
    },
    "Контактный лист 35 мм": {
        "layout": "contact_sheet", "rows": 6, "palette": "Classic B&W (Xerox)", "dither": "halftone",
        "dot_size": 5, "contrast": 2.2, "noise": 22, "streaks": 18, "misreg": 1, "loss": 15,
        "font": "Consolas Bold", "font_size": 28, "tstyle": "white_box",
    },
    "Ризо-оверпринт": {
        "layout": "staggered", "rows": 4, "palette": config.CUSTOM_PALETTE, "custom_colors": ((244, 238, 224), (25, 55, 170)), "dither": "halftone",
        "dot_size": 8, "angle": 30, "contrast": 2.2, "noise": 18, "streaks": 12, "misreg": 5, "loss": 25, "tilt": 1.2,
        "paper": 55, "overprint": 70, "ink2": (255, 60, 140), "font": "Impact", "font_size": 46, "tstyle": "white_box",
    },
    "Склейка со скотчем": {
        "layout": "center_hero", "rows": 5, "palette": "Vintage Newsprint (Cream / Charcoal)", "dither": "halftone",
        "dot_size": 6, "angle": 15, "contrast": 2.0, "noise": 34, "streaks": 20, "misreg": 2, "loss": 28, "tilt": 3.5,
        "edge_x": 20, "edge_y": 14, "paper": 70, "tape": 85, "font": "Courier New Bold", "font_size": 32, "tstyle": "dymo_tape",
    },
    "Диагональ-панк": {
        "layout": "diagonal", "rows": 5, "palette": "Safety Orange (Blaze Orange / Charcoal)", "dither": "halftone", "fit_mode": "cover",
        "dot_size": 9, "contrast": 2.8, "noise": 28, "streaks": 30, "misreg": 5, "loss": 50, "tilt": 4.0, "edge_x": 18, "edge_y": 12,
        "font": "Impact", "font_size": 48, "tstyle": "white_box",
    },
    "Стопка снимков": {
        "layout": "pile", "rows": 5, "palette": "Vintage Newsprint (Cream / Charcoal)", "dither": "halftone", "fit_mode": "cover",
        "dot_size": 5, "angle": 15, "contrast": 1.9, "noise": 32, "streaks": 14, "misreg": 2, "loss": 20, "tilt": 6.0, "edge_x": 6, "edge_y": 5,
        "paper": 65, "tape": 60, "font": "Courier New Bold", "font_size": 30, "tstyle": "white_box",
    },
    "Газетная мозаика": {
        "layout": "mosaic", "rows": 6, "palette": "Vintage Newsprint (Cream / Charcoal)", "dither": "halftone", "fit_mode": "cover",
        "dot_size": 5, "angle": 15, "contrast": 1.8, "noise": 36, "streaks": 10, "misreg": 1, "loss": 18, "copier_edge": 20,
        "edge_x": 6, "edge_y": 5, "paper": 50, "font": "Times New Roman Bold", "font_size": 40, "tstyle": "white_box",
    },
    "Триптих-синька": {
        "layout": "triptych", "palette": "Blueprint / Cyanotype (Navy / Cyan)", "dither": "floyd", "fit_mode": "cover",
        "dot_size": 6, "contrast": 2.1, "noise": 14, "streaks": 10, "misreg": 1, "loss": 22, "tilt": 0.0, "edge_x": 10, "edge_y": 8,
        "font": "Courier New Bold", "font_size": 30, "tstyle": "dymo_tape",
    },
    "Постер во весь лист": {
        "layout": "full_page", "palette": "Classic B&W (Xerox)", "dither": "halftone", "fit_mode": "cover",
        "dot_size": 9, "contrast": 2.6, "noise": 24, "streaks": 28, "misreg": 3, "loss": 0, "tilt": 0.0, "copier_edge": 45,
        "edge_x": 14, "edge_y": 10, "font": "Impact", "font_size": 64, "tstyle": "outline",
    },
    "Лента кинопроб": {
        "layout": "ribbon", "rows": 5, "palette": "Acid Cyberpunk (Neon Lime / Black)", "dither": "halftone", "fit_mode": "cover",
        "dot_size": 7, "contrast": 2.7, "noise": 22, "streaks": 26, "misreg": 4, "loss": 35, "tilt": 0.0,
        "font": "Consolas Bold", "font_size": 34, "tstyle": "dymo_tape",
    },
    "Ризо-диптих": {
        "layout": "duo", "palette": config.CUSTOM_PALETTE, "custom_colors": ((244, 238, 224), (25, 55, 170)), "dither": "halftone", "fit_mode": "cover",
        "dot_size": 8, "angle": 30, "contrast": 2.2, "noise": 18, "streaks": 10, "misreg": 5, "loss": 15, "tilt": 0.0,
        "paper": 55, "overprint": 75, "ink2": (255, 60, 140), "font": "Impact", "font_size": 46, "tstyle": "white_box",
    },
    "Ночное видение": {
        "layout": "center_hero", "rows": 5, "palette": "Nightvision (Muted Green / Phosphor)", "dither": "halftone",
        "dot_size": 6, "contrast": 2.6, "noise": 45, "streaks": 50, "misreg": 3, "loss": 40, "copier_edge": 30,
        "font": "Consolas Bold", "font_size": 32, "tstyle": "dymo_tape",
    },
    "Линейная гравюра": {
        "layout": "center_hero", "rows": 4, "palette": "Vintage Newsprint (Cream / Charcoal)", "dither": "cross",
        "dot_size": 6, "angle": 30, "contrast": 2.2, "noise": 12, "streaks": 10, "misreg": 1, "loss": 15, "paper": 45, "copier_edge": 10,
        "font": "Arial Black", "font_size": 36, "tstyle": "white_box",
    },
    "Мезотинт": {
        "layout": "full_page", "palette": "Classic B&W (Xerox)", "dither": "mezzo", "fit_mode": "cover",
        "dot_size": 8, "contrast": 2.0, "noise": 10, "streaks": 0, "misreg": 0, "loss": 10, "paper": 30, "copier_edge": 20,
        "font": "Impact", "font_size": 44, "tstyle": "outline",
    },
    "Грязный офис": {
        "layout": "staggered", "rows": 4, "palette": "Classic B&W (Xerox)", "dither": "halftone",
        "dot_size": 7, "contrast": 2.4, "noise": 40, "streaks": 40, "misreg": 2, "loss": 45, "copier_edge": 50, "paper": 60,
        "fold": 70, "holes": 1, "stains": 55, "dust": 60, "tilt": 1.2,
        "font": "Consolas Bold", "font_size": 30, "tstyle": "white_box",
    },
    "Байер 8-бит": {
        "layout": "contact_sheet", "rows": 5, "palette": "Nightvision (Muted Green / Phosphor)", "dither": "bayer",
        "dot_size": 9, "contrast": 2.0, "noise": 5, "streaks": 20, "misreg": 0, "loss": 20, "copier_edge": 15,
        "font": "Consolas Bold", "font_size": 30, "tstyle": "dymo_tape",
    },
}


def extract_style(state):
    """Только стилевые поля из состояния страницы."""
    return {k: state[k] for k in STYLE_KEYS if k in state}


def full_style(partial):
    """Пресет с недостающими полями из значений по умолчанию, чтобы он не зависел от текущих настроек."""
    base = {k: config.DEFAULT_STATE[k] for k in STYLE_KEYS}
    base.update(partial)
    return base


def _user_path():
    return os.path.join(appdata.data_dir(), "presets.json")


def load_user():
    try:
        with open(_user_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, dict)} if isinstance(data, dict) else {}


def _write_user(data):
    tmp = _user_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _user_path())


def save_user(name, state):
    data = load_user()
    data[name] = extract_style(state)
    _write_user(data)


def delete_user(name):
    data = load_user()
    if name in data:
        del data[name]
        _write_user(data)


def all_presets():
    """Имя -> полный набор стилевых полей. Пользовательские идут после встроенных."""
    out = {name: full_style(p) for name, p in BUILTIN.items()}
    for name, p in load_user().items():
        out[name] = full_style(p)
    return out
