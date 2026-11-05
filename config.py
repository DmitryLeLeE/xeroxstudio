"""
Config: константы, палитры Risograph, форматы, манифесты самиздата и состояние по умолчанию.
"""

import os
import sys

APP_NAME = "Xerox Zine Studio"
APP_VERSION = "2.6.0"


def resource_path(name):
    """Путь к ресурсу и в обычном запуске, и внутри PyInstaller-сборки."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


CANVAS_FORMATS = {
    "2:3 Постер (1000×1500)": (1000, 1500),
    "1:1 Квадрат / Обложка (1200×1200)": (1200, 1200),
    "9:16 Stories / Обои (1080×1920)": (1080, 1920),
    "3:4 Принт (1200×1600)": (1200, 1600),
    "4:5 Instagram (1080×1350)": (1080, 1350),
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
    "Колонка справа": "column_right",
    "Диагональный каскад": "diagonal",
    "Стопка (коллаж внахлёст)": "pile",
    "Две колонки": "two_columns",
    "Мозаика (большой + малые)": "mosaic",
    "Диптих (два крупных)": "duo",
    "Триптих (три полосы)": "triptych",
    "Лента (ряд кадров)": "ribbon",
    "Во весь лист": "full_page",
    "Свободный лист (всё слоями)": "free",
}
LAYOUT_ALIASES = {"reference_columns": "column"}  # старые проекты

DITHERS = {
    "Полутон (точки)": "halftone",
    "Зерно Флойда–Стейнберга": "floyd",
    "Трафарет (порог)": "stencil",
    "Линии (штриховка)": "lines",
    "Кросс-штрих": "cross",
    "Стипль (случайные точки)": "stipple",
    "Мезотинт (шум)": "mezzo",
    "Байер (упорядоченный)": "bayer",
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
    # свободные шрифты лежат в assets/fonts (Rubik Mono, Press Start и Marck Script с кириллицей; Special Elite и Permanent Marker только латиница)
    "Rubik Mono One": resource_path("assets/fonts/RubikMonoOne-Regular.ttf"),
    "Press Start 2P": resource_path("assets/fonts/PressStart2P-Regular.ttf"),
    "Marck Script": resource_path("assets/fonts/MarckScript-Regular.ttf"),
    "Special Elite": resource_path("assets/fonts/SpecialElite-Regular.ttf"),
    "Permanent Marker": resource_path("assets/fonts/PermanentMarker-Regular.ttf"),
    # андеграундные Rubik (SIL OFL, с кириллицей), подрезаны до латиницы и кириллицы
    "Rubik Dirt": resource_path("assets/fonts/RubikDirt-Regular.ttf"),
    "Rubik Distressed": resource_path("assets/fonts/RubikDistressed-Regular.ttf"),
    "Rubik Wet Paint": resource_path("assets/fonts/RubikWetPaint-Regular.ttf"),
    "Rubik Spray Paint": resource_path("assets/fonts/RubikSprayPaint-Regular.ttf"),
    "Rubik Glitch": resource_path("assets/fonts/RubikGlitch-Regular.ttf"),
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
    "overprint3": 0,
    "ink3": (0, 120, 190),
    "overprint4": 0,
    "ink4": (255, 200, 0),
    "tape": 0,
    "fold": 0,
    "holes": 0,
    "stains": 0,
    "dust": 0,
    "ghost": 0,
    "bands": 0,
    "smear": 0,
    "stamp": "",
    "stamp_rot": -12,
    "layers": [],
    "crop": [0.0, 0.0, 1.0, 1.0],
    "seed": 42,
    "img": None,
}


# --- слои: искажение текста, готовые стили надписей и шаблоны свободного листа
WARPS = {
    "Без искажения": "none",
    "Арка": "arch",
    "Прогиб": "dip",
    "Волна": "wave",
    "Раздувание": "bulge",
    "Наклон": "slant",
}
TEXT_DEFAULTS = {"warp": "none", "warp_k": 0.5, "sx": 1.0, "rot": 0}
# Свойства слоя-надписи, которые накладывает готовый стиль (всё остальное остаётся как было)
TEXT_PRESETS = {
    "Панк-плашка": {"style": "box", "font": "Impact", "rot": -3},
    "Арка-вывеска": {"style": "plain", "font": "Rubik Mono One", "warp": "arch", "warp_k": 0.55},
    "Кислотная волна": {"style": "tape", "font": "Rubik Wet Paint", "warp": "wave", "warp_k": 0.5, "rot": -2},
    "Раздутый заголовок": {"style": "plain", "font": "Arial Black", "warp": "bulge", "warp_k": 0.7, "sx": 1.2},
    "Падающий наклон": {"style": "box", "font": "Impact", "warp": "slant", "warp_k": 0.6, "rot": -4},
    "Записка из газеты": {"style": "ransom", "font": "Arial Black"},
    "Лента Dymo": {"style": "tape", "font": "Courier New Bold"},
    "Машинопись": {"style": "box", "font": "Special Elite"},
    "Глитч-крик": {"style": "plain", "font": "Rubik Glitch", "warp": "dip", "warp_k": 0.4},
    "Растянутый плакат": {"style": "tape", "font": "Impact", "sx": 1.9},
    "Узкий столбик": {"style": "box", "font": "Impact", "sx": 0.55},
    "Баллончик": {"style": "plain", "font": "Rubik Spray Paint", "warp": "wave", "warp_k": 0.3, "rot": -6},
}
# Шаблоны свободного листа. photo=True: фото страницы как слой. Координаты и размер - доли ширины листа.
LAYER_TEMPLATES = {
    "Афиша": [
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.42, "size": 0.84, "rot": -2},
        {"type": "text", "text": "ЖИВОЙ ЗВУК", "text_en": "LIVE NOISE", "preset": "Арка-вывеска", "x": 0.5, "y": 0.1, "size": 0.2},
        {"type": "text", "text": "ПЯТНИЦА · 23:00 · ПОДВАЛ", "text_en": "FRIDAY · 11PM · BASEMENT", "preset": "Лента Dymo", "x": 0.5, "y": 0.86, "size": 0.12},
        {"type": "sticker", "sticker": "star", "x": 0.86, "y": 0.72, "size": 0.2, "rot": 14},
    ],
    "Обложка зина": [
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.5, "size": 0.74, "rot": 2},
        {"type": "text", "text": "НЕТ БОГОВ", "text_en": "NO GODS", "preset": "Записка из газеты", "x": 0.5, "y": 0.1, "size": 0.2},
        {"type": "text", "text": "ВЫПУСК №1", "text_en": "ISSUE #1", "preset": "Панк-плашка", "x": 0.3, "y": 0.92, "size": 0.14},
    ],
    "Коллаж-стопка": [
        {"type": "bitmap", "photo": True, "x": 0.38, "y": 0.3, "size": 0.62, "rot": -6},
        {"type": "bitmap", "photo": True, "x": 0.62, "y": 0.58, "size": 0.5, "rot": 5},
        {"type": "bitmap", "photo": True, "x": 0.35, "y": 0.8, "size": 0.36, "rot": -3},
        {"type": "text", "text": "ВЫРЕЗКИ", "text_en": "CLIPPINGS", "preset": "Кислотная волна", "x": 0.7, "y": 0.1, "size": 0.18},
    ],
    "Объявление": [
        {"type": "text", "text": "ВНИМАНИЕ", "text_en": "ATTENTION", "preset": "Раздутый заголовок", "x": 0.5, "y": 0.12, "size": 0.24},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.5, "size": 0.6, "rot": 0},
        {"type": "text", "text": "ЗВОНИТЬ ПОСЛЕ ПОЛУНОЧИ", "text_en": "CALL AFTER MIDNIGHT", "preset": "Машинопись", "x": 0.5, "y": 0.86, "size": 0.1},
    ],
    "Манифест": [
        {"type": "text", "text": "ДЕЛАЙ\nСАМ", "text_en": "DO IT\nYOURSELF", "preset": "Падающий наклон", "x": 0.5, "y": 0.27, "size": 0.25},
        {"type": "bitmap", "photo": True, "x": 0.66, "y": 0.68, "size": 0.56, "rot": 4},
        {"type": "text", "text": "КОПИРУЙ", "text_en": "COPY IT", "preset": "Узкий столбик", "x": 0.2, "y": 0.8, "size": 0.18, "rot": -90},
    ],
    "Плакат-крик": [
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.55, "size": 0.9, "rot": 0},
        {"type": "text", "text": "ГРОМЧЕ", "text_en": "LOUDER", "preset": "Растянутый плакат", "x": 0.5, "y": 0.12, "size": 0.2},
        {"type": "text", "text": "ГРОМЧЕ", "text_en": "LOUDER", "preset": "Глитч-крик", "x": 0.5, "y": 0.92, "size": 0.2},
    ],
}
