"""
Config: константы, палитры Risograph, форматы, манифесты самиздата и состояние по умолчанию.
"""

import os
import sys

APP_NAME = "Xerox Zine Studio"
APP_VERSION = "1.1.0"


def resource_path(name):
    """Путь к ресурсу и в обычном запуске, и внутри PyInstaller-сборки."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


CANVAS_FORMATS = {
    "2:3 Постер (1000×1500)": (1000, 1500),
    "1:1 Квадрат / Обложка (1200×1200)": (1200, 1200),
    "9:16 Stories / Обои (1080×1920)": (1080, 1920),
    "3:4 Принт (1200×1600)": (1200, 1600),
}

RISO_PALETTES = {
    "Classic B&W (Xerox)": ((255, 255, 255), (10, 10, 10)),
    "Vintage Newsprint (Cream / Charcoal)": ((244, 238, 224), (22, 22, 24)),
    "Acid Cyberpunk (Neon Lime / Black)": ((214, 255, 0), (10, 10, 10)),
    "Hot Pink Riot (Fluo Pink / Black)": ((255, 42, 133), (12, 12, 12)),
    "Blueprint / Cyanotype (Navy / Cyan)": ((10, 22, 40), (0, 230, 255)),
    "Crimson Zine (Off-White / Blood Red)": ((246, 243, 235), (180, 12, 28)),
    "Toxic Violet (Lavender / Deep Violet)": ((230, 220, 245), (35, 10, 60)),
    "Safety Orange (Blaze Orange / Charcoal)": ((255, 87, 34), (18, 18, 18)),
    "Nightvision (Muted Green / Phosphor)": ((12, 28, 14), (64, 255, 96)),
}

ZINE_QUOTES = [
    # VISION
    ("[VISION] I SUFFER FROM THE CLARITY\nOF MY VISION", "PROTECT ME FROM\nWHAT I CANNOT SEE"),
    ("[VISION] WHAT THE EYE SEES\nTHE MIND BELIEVES", "FILTERED THROUGH LIES\nRECORDED IN DUST"),
    ("[VISION] EYES WIDE OPEN\nIN TOTAL DARKNESS", "PAIN IS INEVITABLE\nCLARITY IS FATAL"),
    ("[VISION] THE OPTICAL NERVE\nREMEMBERS EVERYTHING", "OVEREXPOSED\nUNDERSTOOD BY NONE"),
    ("[VISION] DON'T LOOK AT ME\nLOOK THROUGH ME", "ALL SENSORS ACTIVE\nNO SIGNAL RECEIVED"),
    ("[VISION] RETINAL BURN-IN", "PERMANENT RESIDUE"),
    ("[VISION] AN INVERTED SPECTRUM", "WHERE SHADOWS EMIT LIGHT"),
    # SURVEILLANCE
    ("[SURVEILLANCE] CAPTURED IN HIGH RESOLUTION", "ANONYMITY IS A LUXURY\nWE CANNOT AFFORD"),
    ("[SURVEILLANCE] SURVEILLANCE AS\nAN ACT OF LOVE", "PRIVATE THOUGHTS\nBECOME PUBLIC SPECTACLE"),
    ("[SURVEILLANCE] WHO WATCHES\nTHE OBSERVER?", "SILENT WITNESS\nGUILTY PARTNER"),
    ("[SURVEILLANCE] UNAUTHORIZED GAZE", "PERCEPTION IS\nA HOSTILE ACT"),
    ("[SURVEILLANCE] FACIAL RECOGNITION FAILED", "IDENTITY REJECTED"),
    ("[SURVEILLANCE] UNDER CONSTANT SCRUTINY", "STILL UNRECOGNIZABLE"),
    ("[SURVEILLANCE] FEED ARCHIVED AT 04:00", "INCIDENT NOT LOGGED"),
    # MEMORY
    ("[MEMORY] MEMORIES CORRUPTED\nBY FREQUENT REPLAY", "DECAY OF REALITY\nREPLICATED IN TONER"),
    ("[MEMORY] REPEATED UNTIL\nMEANING DISSOLVES", "A COPY OF A COPY\nOF A REAL LIFE"),
    ("[MEMORY] THE LAST IMAGE\nBEFORE REBOOT", "WAS NEVER SAVED"),
    ("[MEMORY] DIGITAL GHOSTS\nIN ANALOG COPIES", "A WITNESS TO\nOUR MUTUAL COLLAPSE"),
    ("[MEMORY] BUFFER OVERFLOW", "DROWNING IN DETAILS"),
    ("[MEMORY] SYNTHETIC NOSTALGIA", "FOR THINGS NEVER EXPERIENCED"),
    # BRUTALIST & POST-PUNK
    ("[BRUTAL] SYSTEM FAILURE\nIN ABSOLUTE SILENCE", "DECODE WHAT REMAINS\nOF THE IMAGE"),
    ("[BRUTAL] THE FUTURE IS COLD\nAND HEAVILY RASTERIZED", "NOTHING IS PERMANENT\nEXCEPT THE SCAN"),
    ("[BRUTAL] TONER RUNNING OUT", "SO IS YOUR TIME"),
    ("[BRUTAL] A CRACK IN THE GLASS", "A SHIFT IN REALITY"),
    ("[BRUTAL] MECHANICAL INDIFFERENCE", "ORGANIC FAILURE"),
    ("[POST-PUNK] THE PANOPTICON CRUMBLES", "UNDER ITS OWN WEIGHT"),
    ("[POST-PUNK] MONOCHROME REALITY", "BLEEDING INTO GREY"),
    ("[POST-PUNK] STATIC ELECTROCUTION", "ON COPIER GLASS"),
    ("[POST-PUNK] A GHOST IN THE COPIER", "SPEAKING IN LINES"),
    ("[POST-PUNK] TERMINAL CLARITY", "NO RETREAT POSSIBLE"),
    # COPIER
    ("[COPIER] THE COPY IS WORSE\nTHAN THE ORIGINAL", "AND THAT IS THE POINT"),
    ("[COPIER] PRESS START\nON THE GLASS", "LET THE LIGHT\nDO THE ARGUING"),
    ("[COPIER] TONER RUNNING OUT", "SO IS YOUR TIME"),
    ("[COPIER] EVERY GENERATION LOSES\nA LITTLE MORE TRUTH", "AND GAINS A LITTLE MORE NOISE"),
    ("[COPIER] ONE ORIGINAL", "ONE THOUSAND ACCOMPLICES"),
    ("[COPIER] FEED THE MACHINE\nA FACE", "GET BACK A WARNING"),
    ("[COPIER] PAPER JAM\nIN THE ARCHIVE", "REMOVE ALL OBSTRUCTIONS TO MEMORY"),
    ("[COPIER] 50 COPIES FOR THE PRICE OF ONE", "NOBODY OWNS THE LAST ONE"),
    # DIY
    ("[DIY] FOLD IT.\nCUT IT.", "GIVE IT AWAY"),
    ("[DIY] MAKE IT BADLY\nMAKE IT TODAY", "PERFECT IS NOT A DEADLINE"),
    ("[DIY] NO PERMISSION\nNO BUDGET", "NO PROBLEM"),
    ("[DIY] A STAPLE IS A SPINE", "A KITCHEN TABLE IS A PRESS"),
    ("[DIY] SCISSORS BEFORE SOFTWARE", "GLUE BEFORE GENIUS"),
    ("[DIY] YOUR HANDS ARE\nTHE ONLY BRAND", "WORTH TRUSTING"),
    ("[DIY] READ IT. COPY IT.", "PASS IT ON"),
    ("[DIY] SMALL PRINT RUN\nHUGE INTENTIONS", "LEAVE ONE ON THE BUS"),
    # CITY
    ("[CITY] THE WALLS ARE\nPAPER NOW", "TEAR A STRIP\nAND READ"),
    ("[CITY] LAMPPOSTS FULL OF VOICES", "NONE OF THEM ASKED"),
    ("[CITY] 3 A.M.\nTHE PHOTOCOPIER STILL WARM", "THE STREETS ALREADY SPEAKING"),
    ("[CITY] CONCRETE REMEMBERS\nEVERY POSTER", "UNDER EVERY LAYER OF PASTE"),
    ("[CITY] WHAT YOU PASTE TODAY", "THE RAIN WILL EDIT TOMORROW"),
    ("[CITY] THIS BUS STOP\nIS A GALLERY", "ADMISSION IS ATTENTION"),
    ("[CITY] NOISE IS A\nPUBLIC LANGUAGE", "SPEAK IT LOUDLY"),
    ("[CITY] FLYER FOR A\nPARTY THAT NEVER HAPPENED", "EVERYONE CAME"),
]

CUSTOM_PALETTE = "Пользовательская (Custom)"

# Отображаемое имя -> внутренний код (код хранится в .zine-файлах)
LAYOUTS = {
    "Шахматка (зигзаг)": "staggered",
    "Колонка (место под текст)": "column",
    "Контактный лист (кадры)": "contact_sheet",
    "Герой + копии": "center_hero",
}
LAYOUT_ALIASES = {"reference_columns": "column"}  # старые проекты

DITHERS = {
    "Полутон (точки)": "halftone",
    "Зерно Флойда–Стейнберга": "floyd",
    "Трафарет (порог)": "stencil",
}
FIT_MODES = {
    "Вписать целиком": "contain",
    "Заполнить кадр": "cover",
}
TEXT_STYLES = {
    "Белая плашка": "white_box",
    "Чёрная лента (Dymo)": "dymo_tape",
    "Контур (чёрный с белой обводкой)": "outline",
}
TEXT_ALIGNS = {"По левому краю": "left", "По центру": "center", "По правому краю": "right"}

# Шрифты с кириллицей. Если файла нет в системе, движок берёт запасной.
FONT_FILES = {
    "Arial Black": "ariblk.ttf",
    "Arial Bold": "arialbd.ttf",
    "Impact": "impact.ttf",
    "Courier New Bold": "courbd.ttf",
    "Consolas Bold": "consolab.ttf",
    "Times New Roman Bold": "timesbd.ttf",
}
FONT_FALLBACKS = [
    "arialbd.ttf",
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]

DEFAULT_STATE = {
    "format": "2:3 Постер (1000×1500)",
    "layout": "staggered",
    "rows": 4,
    "tilt": 0.0,
    "fit_mode": "contain",
    "bright": 1.3,
    "edge_x": 15,
    "edge_y": 10,
    "loss": 30,
    "censor": False,
    "sticker": False,
    "dither": "halftone",
    "dot_size": 7,
    "angle": 45,
    "contrast": 2.4,
    "noise": 25,
    "streaks": 15,
    "misreg": 3,
    "palette": "Classic B&W (Xerox)",
    "invert": False,
    "custom_colors": ((255, 255, 255), (0, 0, 0)),
    "txt_top": "",
    "txt_bottom": "",
    "font": "Arial Black",
    "font_size": 34,
    "tstyle": "white_box",
    "text_align": "left",
    "txt_x": 7,
    "txt_y1": 10,
    "txt_y2": 70,
    "text_rot": 0.0,
    "copier_edge": 0,
    "paper": 0,
    "overprint": 0,
    "ink2": (255, 60, 140),
    "tape": 0,
    "crop": [0.0, 0.0, 1.0, 1.0],
    "seed": 42,
    "img": None,
}
