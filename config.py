"""
Config: константы, палитры Risograph, форматы, манифесты самиздата и состояние по умолчанию.
"""

import os
import sys

APP_NAME = "Xerox Zine Studio"
APP_VERSION = "2.7.0"


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
    "A-серия 1:1.414 (A4, A3, A2) (1000×1414)": (1000, 1414),
    "A-серия горизонт (1414×1000)": (1414, 1000),
    "Афиша 11×17 дюймов (1000×1545)": (1000, 1545),
    "16:9 Широкий экран (1600×900)": (1600, 900),
}

# Заготовки фигур-слоёв (то же в вебе, SHAPE_PRESETS в app.js)
SHAPE_PRESETS = [
    ("Плашка", {"shape": "rect", "fill": "solid", "aspect": 0.5, "size": 0.6}),
    ("Полоса", {"shape": "rect", "fill": "solid", "aspect": 0.07, "size": 0.9}),
    ("Рамка", {"shape": "rect", "fill": "outline", "aspect": 1.3, "size": 0.8}),
    ("Круг", {"shape": "ellipse", "fill": "solid", "aspect": 1.0, "size": 0.4}),
    ("Кольцо", {"shape": "ellipse", "fill": "outline", "aspect": 1.0, "size": 0.5}),
    ("Треугольник", {"shape": "triangle", "fill": "solid", "aspect": 0.9, "size": 0.4}),
    ("Растровое затухание", {"shape": "rect", "fill": "fade", "aspect": 0.55, "size": 0.95}),
    ("Градиентная плашка", {"shape": "rect", "fill": "gradient", "aspect": 0.5, "size": 1.0}),
    ("Диагональные полосы", {"shape": "rect", "fill": "stripes", "aspect": 0.4, "size": 0.8}),
    ("Точки", {"shape": "rect", "fill": "dots", "aspect": 0.5, "size": 0.7}),
]

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
    # ХАНДРА (RU)
    ("[ХАНДРА] Я В ПОРЯДКЕ", "ПРОСТО ДАВНО НЕ ПРОВЕРЯЛ"),
    ("[ХАНДРА] СЕГОДНЯ НИЧЕГО\nНЕ ПРОИЗОШЛО", "И ЭТО БЫЛО ТЯЖЕЛО"),
    ("[ХАНДРА] ВСТАЛ. ПОЕЛ.\nСНОВА ЛЁГ", "СЧИТАЕТСЯ ЗА ДЕНЬ"),
    ("[ХАНДРА] ГРУСТЬ — ЭТО СЕРЫЙ", "КОТОРЫЙ ВДРУГ ПОЯВИЛСЯ ВО ВСЁМ"),
    ("[ХАНДРА] УСТАЛОСТЬ\nНЕ ОТ ДЕЛ", "А ОТ ТОГО, ЧТО НИКТО НЕ СПРОСИЛ"),
    ("[ХАНДРА] ПИШУ ТЕБЕ\nИЗ СЕРЕДИНЫ НЕДЕЛИ", "ЗДЕСЬ ВСЕГДА ВТОРНИК"),
    ("[ХАНДРА] ВСЕ ДОМА.\nМНЕ ТОЖЕ ДОМА", "ЭТО НЕ ОДНО И ТО ЖЕ"),
    ("[ХАНДРА] ТИХО, КАК В ЧАТЕ\nГДЕ ВСЕ ПРОЧИТАЛИ", "И НИКТО НЕ ОТВЕТИЛ"),
    ("[ХАНДРА] ДУША В РЕЖИМЕ\nЭНЕРГОСБЕРЕЖЕНИЯ", "ЯРКОСТЬ 10%"),
    ("[ХАНДРА] НЕ ТО ЧТОБЫ ПЛОХО", "СКОРЕЕ НИКАК"),
    ("[ХАНДРА] ЗАВТРА НАЧНУ", "ГОВОРИЛ ВЧЕРА ТОЖЕ ОН"),
    ("[ХАНДРА] ГОЛОВА ПОЛНА,", "А ВНУТРИ ПУСТО"),
    # БЕССОННИЦА (RU)
    ("[БЕССОННИЦА] 03:47.\nПОТОЛОК СНОВА СМОТРИТ ПЕРВЫМ", "Я ПРОИГРАЛ"),
    ("[БЕССОННИЦА] ТЕЛО ЛЕЖИТ,\nГОЛОВА В КОМАНДИРОВКЕ", "ВЕРНЁТСЯ К УТРУ ПОД УТРО"),
    ("[БЕССОННИЦА] ВЕСЬ ГОРОД СПИТ", "А МЫСЛИ В НОЧНУЮ СМЕНУ"),
    ("[БЕССОННИЦА] ЕЩЁ ОДНА СЕРИЯ.\nЕЩЁ ОДНА ПАЧКА СВЕТА", "ЗА ОКНОМ УЖЕ СЕРО"),
    ("[БЕССОННИЦА] ПОДУШКА ТЕПЛАЯ\nС ОБЕИХ СТОРОН", "ПОВЕРНУЛСЯ — НЕ ПОМОГЛО"),
    ("[БЕССОННИЦА] СНЫ ОТМЕНЕНЫ\nПО ТЕХНИЧЕСКИМ ПРИЧИНАМ", "ПРИНОСИМ ИЗВИНЕНИЯ"),
    # ГОРОД (RU)
    ("[ГОРОД] ПАНЕЛЬКИ, ЛАМПЫ,\nМОКРЫЙ АСФАЛЬТ", "ДОМА ДАЖЕ СТЕНЫ УСТАЛИ"),
    ("[ГОРОД] ПОСЛЕДНЯЯ МАРШРУТКА\nУЕХАЛА БЕЗ НАС", "ЗНАЧИТ, ИДЁМ ПЕШКОМ"),
    ("[ГОРОД] ГАРАЖИ. ЗАБОРЫ.\nНЕБО В ДЫРКУ", "ВСЁ, ЧТО ОСТАЛОСЬ ОТ ЛЕТА"),
    ("[ГОРОД] ЛИФТ СНОВА СЛОМАН", "ВЫБЕРУ ЭТАЖ ПОВЫШЕ ПО ЖИЗНИ"),
    ("[ГОРОД] ПОДЪЕЗД ПАХНЕТ\nЧУЖИМ УЖИНОМ", "МОЙ ПАХНЕТ ПУСТОТОЙ"),
    ("[ГОРОД] ОСЕНЬ ОТМЕНЯЕТ\nВСЕ ПЛАНЫ", "КРОМЕ ТЕХ, ЧТО ПОД ОДЕЯЛОМ"),
    ("[ГОРОД] ФОНАРЬ МИГАЕТ\nПО-СВОЕМУ", "ПОНИМАЮ ЕГО"),
    ("[ГОРОД] РАЙОН СПИТ\nПОД ЛЕНТОЙ ДОЖДЯ", "Я В НЁМ ЗА ЧЕРТОЙ"),
    # ИТ (RU)
    ("[ИТ-ВЫГОРАНИЕ] ЗАДАЧА ЗАКРЫТА.\nЛЮДИ — НЕТ", "СТАТУС: ЖДЁТ РЕВЬЮ"),
    ("[ИТ-ВЫГОРАНИЕ] В ПРОДЕ ВСЁ ХОРОШО", "ВО МНЕ — КРИТИЧЕСКАЯ ОШИБКА"),
    ("[ИТ-ВЫГОРАНИЕ] ОТВЕЧАЮ\nНА ПИСЬМА В 2 НОЧИ", "РЕЗУЛЬТАТ — ТОЛЬКО ХУЖЕ"),
    ("[ИТ-ВЫГОРАНИЕ] ДЕДЛАЙН ПЕРЕНЕСЁН.\nНА ЭТОТ РАЗ — НА ВЧЕРА", "НЕ СПРАШИВАЙТЕ КАК"),
    ("[ИТ-ВЫГОРАНИЕ] ВЫХОДНЫЕ\nЭТО ПРОСТО\nДЕНЬ БЕЗ КОММИТОВ", "НЕ ОТДЫХ"),
    ("[ИТ-ВЫГОРАНИЕ] ПЕРЕЗАГРУЗИ МЕНЯ", "ПОЖАЛУЙСТА, БЕЗ ПОТЕРИ ДАННЫХ"),
    ("[ИТ-ВЫГОРАНИЕ] КОД РАБОТАЕТ.\nНИКТО НЕ ЗНАЕТ ПОЧЕМУ", "КАК И СО МНОЙ"),
    ("[ИТ-ВЫГОРАНИЕ] ЗВОНОК В 18:00\nО ТОМ, ЧТО МОЖНО БЫЛО В ПОЧТЕ", "ЖИЗНЬ ТОЖЕ МОГЛА БЫ"),
    # ПАМЯТЬ И ЛЮБОВЬ (RU)
    ("[ПАМЯТЬ] ПЛЁНКА ДЕРЖИТ\nТО, ЧТО Я ОТПУСТИЛ", "ТЕПЕРЬ ЖДЁТ ПРОЯВИТЕЛЯ"),
    ("[ПАМЯТЬ] ТЫ — ЛУЧШАЯ\nИЗ МОИХ ПОМЕХ", "В СИГНАЛЕ ТЕБЯ БОЛЬШЕ"),
    ("[ПАМЯТЬ] КОПИЯ КОПИИ\nМОЕГО ЛЕТА", "ПОЧТИ УЖЕ НЕ ВИДНО ЛИЦ"),
    ("[ПАМЯТЬ] СТАРЫЕ ФОТО\nМОЛЧАТ ГРОМЧЕ ВСЕХ", "ПЕРЕСМОТРЮ ЕЩЁ РАЗ"),
    ("[ПАМЯТЬ] МЫ БЫЛИ ЗДЕСЬ.\nЭТО ТОЧНО", "ПО ПЯТНУ ОТ КОФЕ ВИДНО"),
    ("[ПАМЯТЬ] ПИСАЛ ТЕБЕ\nТРИ РАЗА И СТЁР", "ЧЕТВЁРТЫЙ — В ЗИН"),
    ("[ПАМЯТЬ] ТЕПЛО ОТ КСЕРОКСА\nЕДИНСТВЕННОЕ ТЕПЛО СЕГОДНЯ", "ЧЕСТНО"),
    # ЗИН (RU)
    ("[ЗИН] СДЕЛАЙ ПЛОХО.\nСДЕЛАЙ СЕЙЧАС", "ХОРОШО ПОДОЖДЁТ"),
    ("[ЗИН] ТОНЕР ЗАКАНЧИВАЕТСЯ", "МОЖЕТ, ТАК И НАДО"),
    ("[ЗИН] ОДИН ОРИГИНАЛ", "ТЫСЯЧА СОУЧАСТНИКОВ"),
    ("[ЗИН] НЕ ВЫКЛАДЫВАЙ В СЕТЬ.\nРАСКЛЕЙ НА ОСТАНОВКЕ", "ПУСТЬ ПРОЧТУТ ПОД ДОЖДЁМ"),
    ("[ЗИН] ЗАЛОМ — ЭТО КОРЕШОК", "СКРЕПКА — ПЕРЕПЛЁТ"),
    ("[ЗИН] ПЕЧАТАЮ ДЛЯ ТЕХ,\nКТО НЕ ГОВОРИТ ВСЛУХ", "ЧИТАЮ ИХ МОЛЧАНИЕ"),
    ("[ЗИН] ЛУЧШЕ КРИВО,\nЧЕМ НИКОГДА", "ДАЖЕ ЕСЛИ НИКТО НЕ УВИДИТ"),
    ("[ЗИН] ЭТО НЕ ИСКУССТВО.\nЭТО ЛИСТОК", "С МОИМ КРИКОМ ВНУТРИ"),
    # DEPRESSIVE (EN)
    ("[GLOOM] I'M FINE.\nTHE LIGHT IS JUST LOW", "SO IS EVERYTHING ELSE"),
    ("[GLOOM] SLEEP WELL\nWHEN YOU CAN", "I STILL HAVE THE WINDOW"),
    ("[GLOOM] WEEKDAYS ARE A LOOP", "WEEKENDS ARE THE SAME LOOP, QUIETER"),
    ("[GLOOM] EMPTY INBOX.\nEMPTY ROOM", "FULL SCREEN BRIGHTNESS"),
    ("[GLOOM] 3 A.M. THOUGHTS\nARE ALWAYS OVERTIME", "NOBODY PAYS FOR THEM"),
    ("[GLOOM] NOTHING IS WRONG", "THAT IS THE WRONG PART"),
    ("[GLOOM] SOFT STATIC\nIN THE CHEST", "SCAN AGAIN. STILL GREY"),
    ("[GLOOM] I WANT TO BE\nA PHOTOCOPY", "NOBODY EXPECTS A COPY TO FEEL"),
    ("[GLOOM] EVERY DAY IS A\nLOW-RES SCAN OF YESTERDAY", "MORE NOISE EACH TIME"),
    ("[GLOOM] WRITE IT DOWN.\nPRINT IT. LET IT GO", "THE PAPER CAN CARRY IT"),
    # IT / HACKER (EN)
    ("[ROOT] SUDO MAKE ME\nFEEL SOMETHING", "PERMISSION DENIED"),
    ("[ROOT] ALL SYSTEMS NOMINAL.\nONE USER OFFLINE", "NO TICKET OPENED"),
    ("[ROOT] REBOOT THE WORLD.\nKEEP MY DATA", "ERROR: NOT FOUND"),
    ("[ROOT] I SPEAK FLUENT\nCOMMAND LINE", "AND NO SMALL TALK"),
    ("[ROOT] NO SIGNAL.\nNO PROBLEM", "THE MACHINE IS LISTENING ANYWAY"),
    ("[ROOT] EVERY PASSWORD IS A\nSMALL CONFESSION", "MINE IS OLD AND TIRED"),
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
    "gutter": 0,
    "recopy": 0,
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
TEXT_DEFAULTS = {"warp": "none", "warp_k": 0.5, "sx": 1.0, "rot": 0, "color": "ink"}
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
    "Неон-вывеска": {"style": "tape", "font": "Rubik Mono One", "warp": "arch", "warp_k": 0.4, "color": "ink2"},
    "Терминал": {"style": "tape", "font": "Courier New Bold"},
    "Розыск (вестерн)": {"style": "box", "font": "Special Elite", "warp": "arch", "warp_k": 0.25, "rot": -2},
    "Бейсбольный гимн": {"style": "plain", "font": "Impact", "warp": "arch", "warp_k": 0.6},
    "Пиксель-игра": {"style": "box", "font": "Press Start 2P"},
    "Рукописный": {"style": "plain", "font": "Marck Script", "warp": "wave", "warp_k": 0.2},
    "Маркер из гаража": {"style": "plain", "font": "Permanent Marker", "warp": "slant", "warp_k": 0.3, "rot": -5},
    "Мем-капс": {"style": "plain", "font": "Impact", "warp": "bulge", "warp_k": 0.35, "sx": 1.1},
    "Грязный принт": {"style": "box", "font": "Rubik Dirt"},
    "Шёпот": {"style": "plain", "font": "Rubik Distressed", "warp": "dip", "warp_k": 0.3},
}
# Шаблоны свободного листа. photo=True: фото страницы как слой. Координаты и размер - доли ширины листа.
LAYER_TEMPLATES = {
    "Арт-постер: затухание": [
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.4, "size": 0.9, "rot": 0},
        {"type": "shape", "shape": "rect", "fill": "fade", "aspect": 0.5, "size": 1.0, "x": 0.5, "y": 0.78, "rot": 180, "color": "ink"},
        {"type": "text", "text": "ТИШИНА\nГРОМЧЕ", "text_en": "SILENCE\nIS LOUDER", "preset": "Растянутый плакат", "x": 0.5, "y": 0.84, "size": 0.2, "color": "paper"},
        {"type": "shape", "shape": "rect", "fill": "solid", "aspect": 0.012, "size": 0.84, "x": 0.5, "y": 0.955, "color": "ink"},
    ],
    "Свисс-постер: круг и полоса": [
        {"type": "shape", "shape": "ellipse", "fill": "solid", "aspect": 1.0, "size": 0.62, "x": 0.5, "y": 0.4, "color": "ink2"},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.4, "size": 0.56, "rot": 0, "blend": "multiply"},
        {"type": "shape", "shape": "rect", "fill": "solid", "aspect": 0.045, "size": 0.84, "x": 0.5, "y": 0.78, "color": "ink"},
        {"type": "text", "text": "ФОРМА СЛЕДУЕТ\nЗА ШУМОМ", "text_en": "FORM FOLLOWS\nNOISE", "preset": "Узкий столбик", "x": 0.5, "y": 0.87, "size": 0.14},
    ],
    "Манифест: плотный шрифт": [
        {"type": "shape", "shape": "rect", "fill": "solid", "aspect": 0.02, "size": 0.84, "x": 0.5, "y": 0.1, "color": "ink"},
        {"type": "text", "text": "МЫ НЕ\nПРОСИЛИ\nТИШИНЫ", "text_en": "WE DID NOT\nASK FOR\nSILENCE", "preset": "Растянутый плакат", "x": 0.5, "y": 0.4, "size": 0.9, "style": "plain", "lead": 0.8, "track": -0.03, "sx": 1.0},
        {"type": "text", "text": "ЗИН · ВЫПУСК 01", "text_en": "ZINE · ISSUE 01", "preset": "Лента Dymo", "x": 0.5, "y": 0.9, "size": 0.2, "track": 0.2},
    ],
    "Плакат с широкой разрядкой": [
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.44, "size": 0.86, "rot": 0},
        {"type": "shape", "shape": "rect", "fill": "gradient", "aspect": 0.4, "size": 1.0, "x": 0.5, "y": 0.8, "rot": 180, "color": "ink"},
        {"type": "text", "text": "НОЧНОЙ ГОРОД", "text_en": "NIGHT CITY", "preset": "Машинопись", "x": 0.5, "y": 0.88, "size": 0.4, "style": "plain", "color": "paper", "track": 0.35},
    ],
    "Депрессивный постер": [
        {"type": "shape", "shape": "rect", "fill": "fade", "aspect": 0.7, "size": 1.0, "x": 0.5, "y": 0.28, "color": "ink"},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.5, "size": 0.7, "rot": 0, "blend": "multiply"},
        {"type": "text", "text": "всё нормально\nпросто пусто", "text_en": "it's fine\njust empty", "preset": "Машинопись", "x": 0.5, "y": 0.86, "size": 0.45, "lead": 1.4, "track": 0.05},
    ],
    "Лайнап фестиваля": [
        {"type": "shape", "shape": "ellipse", "fill": "stripes", "aspect": 1.0, "size": 0.7, "x": 0.5, "y": 0.28, "color": "ink2"},
        {"type": "text", "text": "ПОДВАЛ\nФЕСТ", "text_en": "BASEMENT\nFEST", "preset": "Растянутый плакат", "x": 0.5, "y": 0.28, "size": 0.8, "lead": 0.85},
        {"type": "text", "text": "КАБЕЛЬ · ШУМ\nОСТАНОВКА · ТРАМВАЙ\nНОЧНАЯ СМЕНА", "text_en": "CABLE · NOISE\nBUS STOP · TRAM\nNIGHT SHIFT", "preset": "Машинопись", "x": 0.5, "y": 0.68, "size": 0.5, "lead": 1.5, "track": 0.1},
        {"type": "shape", "shape": "rect", "fill": "solid", "aspect": 0.05, "size": 0.84, "x": 0.5, "y": 0.92, "color": "ink"},
    ],
    "Градиентная обложка": [
        {"type": "shape", "shape": "rect", "fill": "gradient", "aspect": 0.8, "size": 1.0, "x": 0.5, "y": 0.4, "color": "ink"},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.55, "size": 0.7, "rot": 0, "blend": "screen"},
        {"type": "text", "text": "ОБЛОЖКА", "text_en": "COVER", "preset": "Панк-плашка", "x": 0.5, "y": 0.1, "size": 0.7, "track": 0.15},
    ],
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
    "Route 66": [
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.46, "size": 0.86, "rot": -1.5},
        {"type": "sticker", "sticker": "route66", "x": 0.84, "y": 0.72, "size": 0.26, "rot": -8, "shadow": 0.6},
        {"type": "text", "text": "ТРАССА ИЛИ НИЧЕГО", "text_en": "ROUTE 66 OR BUST", "preset": "Бейсбольный гимн", "x": 0.5, "y": 0.1, "size": 0.2},
        {"type": "text", "text": "ОТ ЧИКАГО ДО ЛОС-АНДЖЕЛЕСА", "text_en": "CHICAGO TO LOS ANGELES", "preset": "Лента Dymo", "x": 0.5, "y": 0.92, "size": 0.09},
    ],
    "Розыск": [
        {"type": "text", "text": "РАЗЫСКИВАЕТСЯ", "text_en": "WANTED", "preset": "Розыск (вестерн)", "x": 0.5, "y": 0.1, "size": 0.2},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.47, "size": 0.7, "rot": 0},
        {"type": "sticker", "sticker": "sheriff", "x": 0.84, "y": 0.2, "size": 0.18, "rot": 12},
        {"type": "text", "text": "ЖИВЫМ ИЛИ ПЕРЕПЕЧАТАННЫМ\nНАГРАДА $500", "text_en": "DEAD OR PHOTOCOPIED\nREWARD $500", "preset": "Машинопись", "x": 0.5, "y": 0.88, "size": 0.14},
    ],
    "Хакер-терминал": [
        {"type": "sticker", "sticker": "terminal", "x": 0.5, "y": 0.2, "size": 0.5, "rot": 0},
        {"type": "text", "text": "> ДОСТУП РАЗРЕШЁН", "text_en": "> ACCESS GRANTED", "preset": "Терминал", "x": 0.5, "y": 0.4, "size": 0.14},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.68, "size": 0.62, "rot": 0},
        {"type": "text", "text": "ВЗЛОМАЙ ВСЁ", "text_en": "HACK THE PLANET", "preset": "Пиксель-игра", "x": 0.5, "y": 0.94, "size": 0.12},
    ],
    "Закусочная": [
        {"type": "sticker", "sticker": "open_sign", "x": 0.5, "y": 0.1, "size": 0.5, "rot": -3, "shadow": 0.7},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.5, "size": 0.74, "rot": 2},
        {"type": "sticker", "sticker": "coffee", "x": 0.82, "y": 0.78, "size": 0.2, "rot": 8},
        {"type": "text", "text": "КОФЕ · ПИРОГ · ПАНК", "text_en": "COFFEE · PIE · PUNK", "preset": "Неон-вывеска", "x": 0.5, "y": 0.92, "size": 0.085},
    ],
    "Релиз-ноутс": [
        {"type": "text", "text": "ВЕРСИЯ 6.6.6", "text_en": "VERSION 6.6.6", "preset": "Терминал", "x": 0.5, "y": 0.08, "size": 0.2},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.44, "size": 0.7, "rot": 0},
        {"type": "text", "text": "ИСПРАВЛЕНО: ВСЁ\nСЛОМАНО: НИЧЕГО\nДОБАВЛЕНО: ПАНК", "text_en": "FIXED: EVERYTHING\nBROKEN: NOTHING\nADDED: PUNK", "preset": "Машинопись", "x": 0.5, "y": 0.82, "size": 0.12},
        {"type": "sticker", "sticker": "bug", "x": 0.86, "y": 0.1, "size": 0.14, "rot": 20},
    ],
    "Ошибка 404": [
        {"type": "sticker", "sticker": "e404", "x": 0.5, "y": 0.16, "size": 0.6, "rot": -2, "shadow": 0.6},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.52, "size": 0.66, "rot": 3},
        {"type": "sticker", "sticker": "error_window", "x": 0.78, "y": 0.62, "size": 0.32, "rot": -6, "shadow": 0.5},
        {"type": "text", "text": "СТРАНИЦА НЕ НАЙДЕНА", "text_en": "PAGE NOT FOUND", "preset": "Глитч-крик", "x": 0.5, "y": 0.92, "size": 0.14},
    ],
    "Микстейп": [
        {"type": "sticker", "sticker": "cassette", "x": 0.5, "y": 0.26, "size": 0.7, "rot": -4},
        {"type": "text", "text": "МИКСТЕЙП ТОМ 1", "text_en": "MIXTAPE VOL.1", "preset": "Баллончик", "x": 0.5, "y": 0.5, "size": 0.2},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.78, "size": 0.5, "rot": 2},
    ],
    "Бейсбольная карточка": [
        {"type": "sticker", "sticker": "stripes", "x": 0.5, "y": 0.06, "size": 0.9, "rot": 0},
        {"type": "bitmap", "photo": True, "x": 0.5, "y": 0.46, "size": 0.78, "rot": 0},
        {"type": "sticker", "sticker": "usa_badge", "x": 0.2, "y": 0.8, "size": 0.2, "rot": -10},
        {"type": "text", "text": "ИГРОК №7", "text_en": "PLAYER #7", "preset": "Бейсбольный гимн", "x": 0.58, "y": 0.9, "size": 0.2},
    ],
    "Питч стартапа": [
        {"type": "text", "text": "МЫ ПОСТРОИМ ВСЁ", "text_en": "WE WILL BUILD IT ALL", "preset": "Мем-капс", "x": 0.5, "y": 0.12, "size": 0.2},
        {"type": "sticker", "sticker": "rocket", "x": 0.74, "y": 0.5, "size": 0.4, "rot": 20, "shadow": 0.6},
        {"type": "bitmap", "photo": True, "x": 0.34, "y": 0.52, "size": 0.5, "rot": -4},
        {"type": "sticker", "sticker": "dollar", "x": 0.22, "y": 0.84, "size": 0.18, "rot": -8},
        {"type": "text", "text": "РАУНД A · ПОЧТИ", "text_en": "SERIES A · ALMOST", "preset": "Пиксель-игра", "x": 0.6, "y": 0.9, "size": 0.07},
    ],
    "Баг-репорт": [
        {"type": "text", "text": "БАГ-РЕПОРТ", "text_en": "BUG REPORT", "preset": "Терминал", "x": 0.5, "y": 0.08, "size": 0.18},
        {"type": "sticker", "sticker": "bug", "x": 0.2, "y": 0.26, "size": 0.26, "rot": -10},
        {"type": "bitmap", "photo": True, "x": 0.56, "y": 0.5, "size": 0.7, "rot": 2},
        {"type": "text", "text": "ШАГИ: 1. ВКЛЮЧИТЬ  2. ВЗОРВАТЬСЯ", "text_en": "STEPS: 1. TURN ON  2. EXPLODE", "preset": "Машинопись", "x": 0.5, "y": 0.9, "size": 0.09},
    ],
}


def _fit_template_texts():
    """Подгоняет размер надписей шаблонов так, чтобы самая длинная строка помещалась в лист (с запасом на широкие шрифты)."""
    for tpl in LAYER_TEMPLATES.values():
        for t in tpl:
            if t.get("type") != "text":
                continue
            longest = max(max(len(x) for x in str(t.get(k, "")).split("\n")) for k in ("text", "text_en"))
            sx = float(t.get("sx", TEXT_PRESETS.get(t.get("preset"), {}).get("sx", 1.0)))
            per = 0.375 + 0.5 * max(0.0, float(t.get("track", 0)))  # трекинг расширяет строку
            t["size"] = round(min(t["size"], 0.9 / ((per * longest + 0.3) * sx)), 3)


_fit_template_texts()
