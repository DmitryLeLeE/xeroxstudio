"""
Main: точка входа, фоновый рендер и диспетчер интерфейса Xerox Zine Studio.
"""

import copy
import math
import logging
import os
import queue
import random
import sys
import threading
import time
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps, ImageTk

import appdata
import config
import copier_sound
import imposition
import manifestos
import pdf_writer
import presets
import project_io
import ui_components
from engine import ZineGraphicEngine
from manifest_dialog import ManifestoDialog
from ui_components import (
    ACCENT, BG, FG, FIELD, FONT, FONT_BOLD, FONT_SMALL, LINE, MUTED, PANEL, PANEL2, VIEW_BG,
    CollapsibleSection, CropCanvas, RibbonTile, InteractivePanZoomCanvas, LabeledSlider, ProgressDialog,
    ToastNotification, enable_mousewheel_scroll, make_button, setup_ttk_style,
)

APP_ID = "mitra.xerox.zinestudio"
MAX_SOURCE_SIDE = 2600
AUTOSAVE_MS = 120_000
HISTORY_LIMIT = 60
PRESET_HINT = "Выберите пресет…"
log = logging.getLogger("zine")
HINT = "ЛКМ — двигать вид  ·  колесо — зум  ·  Shift+ЛКМ — поставить подпись"

HELP_TEXT = """Ctrl+O — загрузить фото (можно выбрать сразу несколько: каждое станет страницей)
Ctrl+S — экспорт PNG
Ctrl+Shift+S — сохранить проект (.zine)
Ctrl+Z / Ctrl+Y — отменить / вернуть
Ctrl+Shift+O — открыть проект (.zine)
Ctrl+R — Remix (случайный стиль и цитата)
Ctrl+N — новая страница
Ctrl+M — библиотека манифестов
Перетащите фото или .zine в окно — они откроются
Ctrl+D — дублировать страницу
Ctrl+0 — вписать превью в окно
Ctrl+1 — масштаб 100%

В превью: ЛКМ — двигать, колесо — зум, Shift+ЛКМ — поставить подпись
(ближайшую к курсору: верхнюю или нижнюю).
В левой панели: потяните мышью по фото — выделить кадр, двойной клик — сбросить.
Двойной клик по ползунку возвращает значение по умолчанию."""


def enable_windows_integration():
    """Чёткий интерфейс на HiDPI и своя иконка в панели задач."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def read_image_bgr(path):
    """Читает фото через Pillow: учитывает поворот из EXIF, прозрачность и кириллицу в пути."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[3])
            im = bg
        else:
            im = im.convert("RGB")
        if max(im.size) > MAX_SOURCE_SIDE:
            im.thumbnail((MAX_SOURCE_SIDE, MAX_SOURCE_SIDE), Image.Resampling.LANCZOS)
        return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


class RenderWorker(threading.Thread):
    """Рендер в отдельном потоке: из очереди берётся только самое свежее задание."""

    def __init__(self, engine, results):
        super().__init__(daemon=True)
        self.engine = engine
        self.results = results
        self._cond = threading.Condition()
        self._job = None

    def submit(self, job):
        with self._cond:
            self._job = job
            self._cond.notify()

    def run(self):
        while True:
            with self._cond:
                while self._job is None:
                    self._cond.wait()
                job, self._job = self._job, None
            token, cv_img, state = job
            t0 = time.time()
            try:
                img, bits = self.engine.render_zine_page(cv_img, state)
                self.results.put(("ok", token, img, bits, time.time() - t0))
            except Exception as exc:  # ошибка показывается пользователю, а не глотается
                log.exception("ошибка рендера")
                self.results.put(("err", token, f"{type(exc).__name__}: {exc}", None, 0.0))


class XeroxZineStudioApp:
    def __init__(self, root, open_path=None):
        self.root = root
        self.settings = appdata.Settings()
        self.sc = max(1.0, root.winfo_fpixels("1i") / 96.0)  # масштаб Windows (125%, 150%...)
        ui_components.UI_SCALE = self.sc
        self.thumb_box = (self.px(58), self.px(86))

        self.dirty = False
        self.project_path = None
        self._rev = 0
        self._autosave_rev = 0
        self._autosave_busy = False
        self._autosave_thread = None
        self.hist, self.hist_idx, self._hist_after = [], 0, None

        self._setup_window()
        setup_ttk_style(root)
        self._update_title()

        self.engine = ZineGraphicEngine()
        self.results = queue.Queue()
        self.worker = RenderWorker(self.engine, self.results)
        self.worker.start()

        self.final_poster = None
        self.stencil_1bit = None
        self.render_token = 0
        self._loading = False
        self._busy = False

        self.pages = []
        self.page_thumbs = []
        self.page_btns = []
        self.cur_page_idx = 0
        self.images = {}
        self.cur_img_key = None
        self._img_counter = 0
        self.crop = [0.0, 0.0, 1.0, 1.0]
        self.seed = config.DEFAULT_STATE["seed"]
        self.custom_colors = config.DEFAULT_STATE["custom_colors"]
        self.ink2 = tuple(config.DEFAULT_STATE["ink2"])
        self.extra_inks = {"ink3": tuple(config.DEFAULT_STATE["ink3"]), "ink4": tuple(config.DEFAULT_STATE["ink4"])}
        self.layers = []

        self.vars = {}
        self._loading = True  # Tk-виджеты пишут в переменные при создании: рендерить рано
        self._build_ui()
        self._loading = False
        self._bind_hotkeys()
        self._init_first_page()

        root.report_callback_exception = self._on_tk_exception
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._setup_dnd()
        root.after(30, self._poll_results)
        root.after(AUTOSAVE_MS, self._autosave_tick)
        if open_path:
            root.after(200, lambda: self._open_from_cli(open_path))
        else:
            root.after(400, self._offer_recovery)

    # ------------------------------------------------------------------ окно
    def px(self, n):
        return int(round(n * self.sc))

    def _setup_window(self):
        r = self.root
        r.configure(bg=BG)
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        w, h = min(self.px(1600), sw - 40), min(self.px(980), sh - 90)
        r.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
        r.minsize(min(self.px(1100), sw - 40), min(self.px(620), sh - 90))
        try:
            if sys.platform == "win32":
                r.iconbitmap(default=config.resource_path("icon.ico"))
        except Exception:
            pass
        try:
            self._icon = tk.PhotoImage(file=config.resource_path("icon.png"))
            r.iconphoto(True, self._icon)
        except Exception:
            pass

    # ------------------------------------------------------------------ переменные
    def _var(self, key):
        default = config.DEFAULT_STATE[key]
        cls = tk.BooleanVar if isinstance(default, bool) else tk.IntVar if isinstance(default, int) else tk.DoubleVar if isinstance(default, float) else tk.StringVar
        v = cls(value=default)
        v.trace_add("write", self._on_var_changed)
        self.vars[key] = v
        return v

    def _on_var_changed(self, *_):
        if not self._loading:
            self.preset_var.set(PRESET_HINT)  # стиль изменён вручную: имя пресета больше не верно
            self.schedule_render()

    def _slider(self, parent, key, text, from_, to, res=1):
        s = LabeledSlider(parent, text, self._var(key), from_, to, res=res, default=config.DEFAULT_STATE[key])
        s.pack(fill=tk.X, pady=1)

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=PANEL2, fg=MUTED, font=FONT_SMALL, anchor="w").pack(fill=tk.X, pady=(4, 1))

    def _combo(self, parent, key, label, mapping):
        self._label(parent, label)
        var = self._var(key)
        inverse = {v: k for k, v in mapping.items()}
        shown = tk.StringVar(value=inverse.get(var.get(), next(iter(mapping))))
        cb = ttk.Combobox(parent, textvariable=shown, values=list(mapping), state="readonly", font=FONT)
        cb.pack(fill=tk.X, pady=(0, 3))

        def picked(_e):
            var.set(mapping[shown.get()])
            cb.selection_clear()
            if key == "layout" and var.get() == "free":
                self.root.after(0, self._ensure_free_start)

        cb.bind("<<ComboboxSelected>>", picked)
        var.trace_add("write", lambda *a: shown.set(inverse.get(var.get(), shown.get())))
        return cb

    def _check(self, parent, key, text, command=None):
        cb = tk.Checkbutton(
            parent, text=text, variable=self._var(key), bg=PANEL2, fg=FG, selectcolor=FIELD,
            activebackground=PANEL2, activeforeground=ACCENT, bd=0, highlightthickness=0,
            font=FONT, anchor="w", cursor="hand2", command=command,
        )
        cb.pack(fill=tk.X, pady=1)
        return cb

    def _entry(self, parent, key, label):
        self._label(parent, label)
        e = tk.Entry(parent, textvariable=self._var(key), bg=FIELD, fg=FG, insertbackground=ACCENT, font=("Consolas", 9), relief="flat",
                     highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT)
        e.pack(fill=tk.X, pady=(0, 3), ipady=3)
        return e

    def _text_box(self, parent):
        t = tk.Text(
            parent, height=3, bg=FIELD, fg=FG, insertbackground=ACCENT, font=("Consolas", 9), relief="flat",
            highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT, padx=6, pady=4, wrap="word",
        )
        t.pack(fill=tk.X, pady=(0, 3))
        t.bind("<KeyRelease>", lambda e: self.schedule_render())
        t.bind("<<Paste>>", lambda e: self.root.after_idle(self.schedule_render))
        t.bind("<<Cut>>", lambda e: self.root.after_idle(self.schedule_render))
        for seq in ("<Control-o>", "<Control-O>"):  # в Text это «вставить строку» - не нужно
            t.bind(seq, lambda e: (self.load_image(), "break")[1])
        return t

    # ------------------------------------------------------------------ интерфейс
    def _build_ui(self):
        self._build_menu()

        status = tk.Frame(self.root, bg="#0e0e0e")
        status.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(status, text=HINT, bg="#0e0e0e", fg=MUTED, font=FONT_SMALL, anchor="w", padx=8, pady=3).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="")
        tk.Label(status, textvariable=self.status_var, bg="#0e0e0e", fg=ACCENT, font=FONT_SMALL, anchor="e", padx=8).pack(side=tk.RIGHT)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)
        self._sections = []
        self.stage = tk.Frame(body, bg=VIEW_BG)
        self._build_ribbon(body)
        # выезжающая панель: шапка с названием и крестиком, ниже одна из двух колонок
        self.drawer = tk.Frame(body, bg=PANEL, width=self.px(410), highlightthickness=2, highlightbackground="#555")
        self.drawer.pack_propagate(False)
        head = tk.Frame(self.drawer, bg="#000")
        head.pack(fill=tk.X)
        self.drawer_title = tk.Label(head, text="", bg="#000", fg=ACCENT, font=("Segoe UI", 11, "bold"), anchor="w", padx=10, pady=6)
        self.drawer_title.pack(side=tk.LEFT, fill=tk.X, expand=True)
        make_button(head, "✕", lambda: self._set_fly(""), kind="secondary", padx=8, pady=1).pack(side=tk.RIGHT, padx=6, pady=4)
        self.drawer_body = tk.Frame(self.drawer, bg=PANEL)
        self.drawer_body.pack(fill=tk.BOTH, expand=True)
        self.col_source = self._build_source_column(self.drawer_body)
        self.col_settings = self._build_settings_column(self.drawer_body)
        self.stage.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4), pady=4)
        self._build_viewport_column(self.stage)
        self._fly = ""
        self._set_fly(self.settings.get("ui_fly", ""), remember=False)

    RIBBON = (("styles", "Стили"), ("photo", "Фото"), ("s0", "Сетка"), ("s1", "Кадры"), ("s2", "Растр"), ("s3", "Цвет"), ("s4", "Износ"), ("s5", "Слои"), ("s6", "Текст"))
    RIBBON_TITLES = {"photo": "ФОТО СТРАНИЦЫ", "s0": "ФОРМАТ И СЕТКА", "s1": "ФОТО И КАДРЫ", "s2": "РАСТР И ТОНЕР", "s3": "ПАЛИТРА", "s4": "ИЗНОС И ШТАМП", "s5": "СЛОИ: СТИКЕРЫ И НАДПИСИ", "s6": "ТЕКСТ И ШРИФТЫ", "all": "ВСЕ НАСТРОЙКИ"}

    def _build_ribbon(self, parent):
        rail = tk.Frame(parent, bg=BG, width=self.px(74))
        rail.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 6), pady=6)
        rail.pack_propagate(False)
        self.ribbon = {}
        for key, label in self.RIBBON:
            cmd = self._styles_popup if key == "styles" else (lambda k=key: self._set_fly("" if self._fly == k else k))
            t = RibbonTile(rail, key, label, cmd, scale=self.px(100) / 100.0, accent=(ACCENT if key != "styles" else "#ffe14a"))
            if key == "styles":
                t.config(highlightbackground="#ffe14a")
            t.pack(fill=tk.X, pady=3)
            self.ribbon[key] = t
        all_tile = RibbonTile(rail, "all", "Всё", lambda: self._set_fly("" if self._fly == "all" else "all"), scale=self.px(100) / 100.0)
        all_tile.pack(side=tk.BOTTOM, fill=tk.X, pady=3)
        self.ribbon["all"] = all_tile

    def _styles_popup(self):
        t = self.ribbon["styles"]
        self._style_menu.tk_popup(t.winfo_rootx() + t.winfo_width(), t.winfo_rooty())

    def _set_fly(self, fly, remember=True):
        """Открывает панель: 'photo', 's0'..'s6' (одна секция), 'all' (все настройки) или '' (лист на весь экран)."""
        self._fly = fly
        if remember:
            self.settings.set("ui_fly", fly)
        for k, t in self.ribbon.items():
            t.set_active(k == fly)
        for w in (self.col_source, self.col_settings):
            w.pack_forget()
        if not fly:
            self.drawer.pack_forget()
            return
        self.drawer_title.config(text="▮ " + self.RIBBON_TITLES.get(fly, ""))
        if self.drawer.winfo_manager() == "":
            self.drawer.pack(side=tk.LEFT, fill=tk.Y, before=self.stage, padx=(0, 6), pady=6)
        if fly == "photo":
            self.col_source.pack(fill=tk.BOTH, expand=True)
            return
        self.col_settings.pack(fill=tk.BOTH, expand=True)
        single = fly != "all"
        for s in self._sections:
            s.pack_forget()
        for i, s in enumerate(self._sections):
            s.set_single(single)
            if not single or fly == f"s{i}":
                s.pack(fill=tk.X, padx=6, pady=3)
        if single:
            self.preset_row.pack_forget()
        else:
            self.preset_row.pack(fill=tk.X, padx=6, pady=(6, 2), before=self._sections[0])
        self.c_settings.yview_moveto(0)

    def _build_menu(self):
        menu_bar = tk.Menu(self.root)
        f = tk.Menu(menu_bar, tearoff=0)
        f.add_command(label="Новый проект", command=self.new_project)
        f.add_command(label="Загрузить фото...", command=self.load_image, accelerator="Ctrl+O")
        f.add_separator()
        f.add_command(label="Сохранить проект", command=self.save_project, accelerator="Ctrl+Shift+S")
        f.add_command(label="Сохранить проект как...", command=self.save_project_as)
        f.add_command(label="Открыть проект (.zine)...", command=self.open_project, accelerator="Ctrl+Shift+O")
        f.add_separator()
        f.add_command(label="Экспорт страницы в PNG...", command=self.export_png, accelerator="Ctrl+S")
        f.add_command(label="Экспорт всех страниц в PNG...", command=self.export_all_png)
        f.add_command(label="Экспорт 1-bit трафарета (PNG)...", command=self.export_stencil)
        f.add_command(label="Экспорт разделения красок для ризографа (ZIP)...", command=self.export_separations)
        f.add_command(label="Экспорт книги в PDF...", command=self.export_multipage_pdf)
        f.add_command(label="Экспорт PDF для печати (A4, поля 10 мм)...", command=self.export_pdf_a4)
        f.add_command(label="Экспорт 8-page мини-зина (A4)...", command=self.export_mini_zine)
        f.add_command(label="Экспорт буклета на скрепку, A4 (PDF)...", command=lambda: self.export_booklet("a4"))
        f.add_command(label="Экспорт буклета на скрепку, Letter (PDF)...", command=lambda: self.export_booklet("letter"))
        f.add_command(label="Лист калибровки принтера (PNG)...", command=self.export_calibration)
        self.sound_on = tk.BooleanVar(value=bool(self.settings.get("copier_sound", False)))
        self.sound_on.trace_add("write", lambda *a: self.settings.set("copier_sound", self.sound_on.get()))
        f.add_checkbutton(label="Звук копира при экспорте", variable=self.sound_on)
        f.add_separator()
        f.add_command(label="Выход", command=self.on_close)
        menu_bar.add_cascade(label="Файл", menu=f)

        e = tk.Menu(menu_bar, tearoff=0)
        e.add_command(label="Отменить", command=self.undo, accelerator="Ctrl+Z")
        e.add_command(label="Вернуть", command=self.redo, accelerator="Ctrl+Y")
        menu_bar.add_cascade(label="Правка", menu=e)

        self._style_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Стиль", menu=self._style_menu)

        t = tk.Menu(menu_bar, tearoff=0)
        t.add_command(label="Библиотека манифестов...", command=self.open_manifesto_library, accelerator="Ctrl+M")
        t.add_command(label="Случайный манифест", command=self.random_quote)
        t.add_command(label="Сохранить текст страницы в «Мои манифесты»", command=self.save_current_manifesto)
        menu_bar.add_cascade(label="Манифесты", menu=t)

        p = tk.Menu(menu_bar, tearoff=0)
        p.add_command(label="Новая страница", command=self.add_page, accelerator="Ctrl+N")
        p.add_command(label="Дублировать страницу", command=self.duplicate_page, accelerator="Ctrl+D")
        p.add_command(label="Сдвинуть влево", command=lambda: self.move_page(-1))
        p.add_command(label="Сдвинуть вправо", command=lambda: self.move_page(1))
        p.add_command(label="Удалить страницу", command=self.delete_page)
        menu_bar.add_cascade(label="Страницы", menu=p)

        h = tk.Menu(menu_bar, tearoff=0)
        h.add_command(label="Горячие клавиши", command=self.show_help, accelerator="F1")
        h.add_command(label="Открыть журнал ошибок", command=self.show_log)
        h.add_command(label="Лицензии третьих сторон", command=self.show_licenses)
        h.add_command(label="О программе", command=self.show_about)
        menu_bar.add_cascade(label="Справка", menu=h)
        self.root.config(menu=menu_bar)

    def _build_source_column(self, parent):
        col = tk.Frame(parent, bg=PANEL)
        make_button(col, "📂  Загрузить фото", self.load_image, kind="primary").pack(fill=tk.X, padx=8, pady=(8, 4))
        tools = tk.Frame(col, bg=PANEL)
        tools.pack(fill=tk.X, padx=8)
        for text, kind in (("↺ 90°", "ccw"), ("↻ 90°", "cw"), ("⇋ Зеркало", "flip")):
            make_button(tools, text, lambda k=kind: self.transform_photo(k)).pack(side=tk.LEFT, padx=(0, 4), pady=2)
        self.src_info = tk.Label(col, text="", bg=PANEL, fg=MUTED, font=FONT_SMALL, anchor="w", justify="left", wraplength=self.px(360))
        self.src_info.pack(fill=tk.X, padx=8)
        self.canvas_crop = CropCanvas(col)
        self.canvas_crop.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.canvas_crop.on_crop_changed = self._on_crop_changed
        tk.Label(
            col, text="Потяните мышью по фото — выделить кадр.\nДвойной клик — сбросить.", bg=PANEL, fg=MUTED,
            font=FONT_SMALL, justify="left", anchor="w",
        ).pack(fill=tk.X, padx=8, pady=(0, 8))
        return col

    def _build_settings_column(self, parent):
        col = tk.Frame(parent, bg=PANEL)
        self.c_settings = tk.Canvas(col, bg=PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(col, orient="vertical", style="Dark.Vertical.TScrollbar", command=self.c_settings.yview)
        self.f_settings = tk.Frame(self.c_settings, bg=PANEL)
        self.f_settings.bind("<Configure>", lambda e: self.c_settings.configure(scrollregion=self.c_settings.bbox("all")))
        win = self.c_settings.create_window((0, 0), window=self.f_settings, anchor="nw")
        self.c_settings.bind("<Configure>", lambda e: self.c_settings.itemconfigure(win, width=e.width))
        self.c_settings.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.c_settings.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_settings_controls(self.f_settings)
        enable_mousewheel_scroll(self.f_settings, self.c_settings)
        enable_mousewheel_scroll(self.c_settings, self.c_settings)
        return col

    def _section(self, parent, title):
        s = CollapsibleSection(parent, title=title)
        self._sections.append(s)
        return s.content

    def _build_settings_controls(self, p):
        row = tk.Frame(p, bg=PANEL)
        self.preset_row = row
        tk.Label(row, text="СТИЛЬ", bg=PANEL, fg=MUTED, font=FONT_BOLD).pack(side=tk.LEFT, padx=(2, 6))
        self.preset_var = tk.StringVar(value=PRESET_HINT)
        self.preset_combo = ttk.Combobox(row, textvariable=self.preset_var, state="readonly", font=FONT)
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)
        make_button(row, "＋ Сохранить", self.save_preset).pack(side=tk.LEFT, padx=(6, 0))
        self._refresh_presets()

        # 1. Формат и сетка
        c = self._section(p, "1. ФОРМАТ И СЕТКА")
        self._combo(c, "format", "Формат холста", {k: k for k in config.CANVAS_FORMATS})
        self._combo(c, "layout", "Раскладка кадров", config.LAYOUTS)
        self._slider(c, "rows", "Строк / копий", 3, 16)
        self._slider(c, "tilt", "Наклон кадров (°)", 0.0, 5.0, 0.2)

        # 2. Фото и кадры
        c = self._section(p, "2. ФОТО И КАДРЫ")
        self._combo(c, "fit_mode", "Как класть фото в кадр", config.FIT_MODES)
        self._slider(c, "bright", "Яркость фото", 0.6, 2.0, 0.05)
        self._slider(c, "edge_x", "Рваный край по X", 0, 50)
        self._slider(c, "edge_y", "Рваный край по Y", 0, 50)
        self._slider(c, "tape", "Малярный скотч на кадрах", 0, 100)
        self._slider(c, "loss", "Потеря качества копий", 0, 100)
        self._check(c, "censor", "Чёрная полоса на глазах (поиск лиц)", command=self._on_censor_toggle)
        self._check(c, "sticker", "Вырезка-стикер (тёмный объект на светлом фоне)")
        make_button(c, "🎲  Другие края и пыль", self.reshuffle_seed, kind="secondary").pack(fill=tk.X, pady=(6, 0))
        make_button(c, "🧬  Мутировать вид", self.mutate_look, kind="secondary").pack(fill=tk.X, pady=(3, 0))
        self._label(c, "Не менять при Remix:")
        self.locks = {}
        saved = self.settings.get("remix_locks", {}) or {}
        for key, text in (("palette", "палитру"), ("layout", "раскладку"), ("raster", "растр"), ("text", "текст"), ("font", "шрифт"), ("wear", "износ")):
            var = tk.BooleanVar(value=bool(saved.get(key, False)))
            var.trace_add("write", lambda *a: self.settings.set("remix_locks", {k: v.get() for k, v in self.locks.items()}))
            self.locks[key] = var
            tk.Checkbutton(c, text=text, variable=var, bg=PANEL2, fg=FG, selectcolor=FIELD, activebackground=PANEL2, activeforeground=ACCENT,
                           bd=0, highlightthickness=0, font=FONT, anchor="w", cursor="hand2").pack(fill=tk.X, pady=0)

        # 3. Растр и тонер
        c = self._section(p, "3. РАСТР И ТОНЕР")
        self._combo(c, "dither", "Тип растра", config.DITHERS)
        self._slider(c, "dot_size", "Размер точки растра", 3, 22)
        self._slider(c, "angle", "Угол растра (°)", 0, 90)
        self._slider(c, "contrast", "Контраст", 1.0, 4.5, 0.1)
        self._slider(c, "noise", "Шум тонера", 0, 100)
        self._slider(c, "streaks", "Полосы сканера", 0, 100)
        self._slider(c, "misreg", "Приводка (сдвиг краски)", 0, 12)
        self._slider(c, "copier_edge", "Тень края копира", 0, 100)
        self._slider(c, "paper", "Фактура бумаги", 0, 100)
        self._slider(c, "overprint", "Второй цвет (оверпринт)", 0, 100)
        row2 = tk.Frame(c, bg=PANEL2)
        row2.pack(fill=tk.X, pady=(0, 2))
        self.sw_ink2 = tk.Label(row2, width=6, bg="#%02x%02x%02x" % self.ink2, relief="flat", highlightthickness=1, highlightbackground=LINE)
        self.sw_ink2.pack(side=tk.LEFT, ipady=6)
        make_button(row2, "Цвет второй краски…", self._pick_ink2).pack(side=tk.LEFT, padx=6)
        self.sw_extra = {}
        for key, over, label in (("ink3", "overprint3", "Третья краска (полутона)"), ("ink4", "overprint4", "Четвёртая краска (света)")):
            self._slider(c, over, label, 0, 100)
            rowx = tk.Frame(c, bg=PANEL2)
            rowx.pack(fill=tk.X, pady=(0, 2))
            sw = tk.Label(rowx, width=6, bg="#%02x%02x%02x" % self.extra_inks[key], relief="flat", highlightthickness=1, highlightbackground=LINE)
            sw.pack(side=tk.LEFT, ipady=6)
            self.sw_extra[key] = sw
            make_button(rowx, f"Цвет: {label.split(' (')[0].lower()}…", lambda k=key: self._pick_extra_ink(k)).pack(side=tk.LEFT, padx=6)

        # 4. Палитра
        c = self._section(p, "4. ПАЛИТРА (RISOGRAPH)")
        self._combo(c, "palette", "Бумага / краска", {k: k for k in list(config.RISO_PALETTES) + [config.CUSTOM_PALETTE]})
        row = tk.Frame(c, bg=PANEL2)
        row.pack(fill=tk.X, pady=(2, 2))
        self.sw_paper = tk.Label(row, width=6, bg="#ffffff", relief="flat", highlightthickness=1, highlightbackground=LINE)
        self.sw_ink = tk.Label(row, width=6, bg="#000000", relief="flat", highlightthickness=1, highlightbackground=LINE)
        self.sw_paper.pack(side=tk.LEFT, ipady=6)
        self.sw_ink.pack(side=tk.LEFT, padx=(4, 8), ipady=6)
        make_button(row, "Бумага…", lambda: self._pick_color(0)).pack(side=tk.LEFT, padx=2)
        make_button(row, "Краска…", lambda: self._pick_color(1)).pack(side=tk.LEFT, padx=2)
        self._check(c, "invert", "Инвертировать цвета")
        self.vars["palette"].trace_add("write", lambda *a: self._update_swatches())
        self.vars["invert"].trace_add("write", lambda *a: self._update_swatches())

        # 5. Износ листа
        c = self._section(p, "5. ИЗНОС ЛИСТА, МЕХАНИКА КОПИРА И ШТАМП")
        self._slider(c, "fold", "Сгиб листа", 0, 100)
        self._check(c, "holes", "Дырки от дырокола")
        self._slider(c, "stains", "Пятна (кофе, жир)", 0, 100)
        self._slider(c, "dust", "Пыль и волоски", 0, 100)
        self._slider(c, "ghost", "Эхо барабана (бледный повтор)", 0, 100)
        self._slider(c, "bands", "Полосы тонера", 0, 100)
        self._slider(c, "smear", "Заедание бумаги", 0, 100)
        self._entry(c, "stamp", "Штамп (пусто = нет)")
        self._slider(c, "stamp_rot", "Поворот штампа (°)", -45, 45)

        # 6a. Слои
        c = self._section(p, "6. СЛОИ: СТИКЕРЫ И НАДПИСИ")
        self._layer_loading = False
        self.layer_list = tk.Listbox(c, height=5, bg=FIELD, fg=FG, selectbackground=ACCENT, activestyle="none", relief="flat",
                                     highlightthickness=1, highlightbackground=LINE, exportselection=False, font=FONT)
        self.layer_list.pack(fill=tk.X, pady=(0, 3))
        self.layer_list.bind("<<ListboxSelect>>", lambda e: (self._load_layer_controls(), self._update_layer_frame()))
        rowl = tk.Frame(c, bg=PANEL2)
        rowl.pack(fill=tk.X)
        make_button(rowl, "＋ Надпись", self._add_text_layer).pack(side=tk.LEFT, padx=(0, 3))
        make_button(rowl, "＋ Стикер…", self._add_sticker_layer).pack(side=tk.LEFT, padx=3)
        make_button(rowl, "＋ Фото…", self._add_photo_layer).pack(side=tk.LEFT, padx=3)
        rowl2 = tk.Frame(c, bg=PANEL2)
        rowl2.pack(fill=tk.X, pady=(3, 0))
        for text, what in (("Копия", "copy"), ("Удалить", "delete"), ("👁 Скрыть", "hide"), ("⇋ Отразить", "flip"), ("↑", "up"), ("↓", "down")):
            make_button(rowl2, text, lambda w=what: self._layer_action(w)).pack(side=tk.LEFT, padx=(0, 3))
        self.ly_vars = {"x": tk.DoubleVar(value=50), "y": tk.DoubleVar(value=50), "size": tk.DoubleVar(value=20), "rot": tk.DoubleVar(value=0), "opacity": tk.DoubleVar(value=100),
                        "warp_k": tk.DoubleVar(value=50), "sx": tk.DoubleVar(value=100)}
        for key, text, lo, hi in (("x", "Позиция X (%)", 0, 100), ("y", "Позиция Y (%)", 0, 100), ("size", "Размер (% ширины)", 4, 100), ("rot", "Поворот (°)", -180, 180), ("opacity", "Непрозрачность слоя (%)", 10, 100),
                                ("warp_k", "Сила искажения (%)", 5, 100), ("sx", "Растяжение текста (%)", 40, 300)):
            self.ly_vars[key].trace_add("write", lambda *a, k=key: self._layer_var_changed(k))
            LabeledSlider(c, text, self.ly_vars[key], lo, hi, res=1, default=self.ly_vars[key].get()).pack(fill=tk.X, pady=1)
        self.ly_text = tk.StringVar()
        self.ly_text.trace_add("write", lambda *a: self._layer_var_changed("text"))
        self._label(c, "Текст слоя (для надписей)")
        tk.Entry(c, textvariable=self.ly_text, bg=FIELD, fg=FG, insertbackground=ACCENT, font=("Consolas", 9), relief="flat",
                 highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT).pack(fill=tk.X, ipady=3)
        self.ly_color = tk.StringVar(value="ink")
        self.ly_color.trace_add("write", lambda *a: self._layer_var_changed("color"))
        self._label(c, "Цвет слоя")
        ttk.Combobox(c, textvariable=self.ly_color, values=["ink", "paper", "ink2", "ink3", "ink4"], state="readonly", font=FONT).pack(fill=tk.X, pady=(0, 3))

        self.ly_warp = tk.StringVar(value="none")
        self.ly_warp.trace_add("write", lambda *a: self._layer_var_changed("warp"))
        self._label(c, "Искажение текста")
        warp_names = {v: k for k, v in config.WARPS.items()}
        warp_cb = ttk.Combobox(c, values=list(config.WARPS), state="readonly", font=FONT)
        warp_cb.pack(fill=tk.X, pady=(0, 3))
        warp_cb.bind("<<ComboboxSelected>>", lambda e: (self.ly_warp.set(config.WARPS[warp_cb.get()]), warp_cb.selection_clear()))
        self.ly_warp.trace_add("write", lambda *a: warp_cb.set(warp_names.get(self.ly_warp.get(), "Без искажения")))
        self._label(c, "Готовый стиль надписи (к выбранному слою)")
        sp_cb = ttk.Combobox(c, values=list(config.TEXT_PRESETS), state="readonly", font=FONT)
        sp_cb.pack(fill=tk.X, pady=(0, 3))
        sp_cb.bind("<<ComboboxSelected>>", lambda e: (self._apply_text_preset(sp_cb.get()), sp_cb.set(""), sp_cb.selection_clear()))
        self._label(c, "Шаблон листа (заменяет все слои)")
        tp_cb = ttk.Combobox(c, values=list(config.LAYER_TEMPLATES), state="readonly", font=FONT)
        tp_cb.pack(fill=tk.X, pady=(0, 3))
        tp_cb.bind("<<ComboboxSelected>>", lambda e: (self._apply_layer_template(tp_cb.get()), tp_cb.set(""), tp_cb.selection_clear()))

        self.ly_style = tk.StringVar(value="box")
        self.ly_style.trace_add("write", lambda *a: self._layer_var_changed("style"))
        self._label(c, "Подложка надписи")
        ttk.Combobox(c, textvariable=self.ly_style, values=["box", "tape", "plain", "ransom"], state="readonly", font=FONT).pack(fill=tk.X, pady=(0, 3))

        # 7. Текст
        c = self._section(p, "7. МАНИФЕСТЫ И ТИПОГРАФИКА")
        self._label(c, "Верхняя надпись")
        self.txt_top = self._text_box(c)
        self._label(c, "Нижняя надпись")
        self.txt_bot = self._text_box(c)
        make_button(c, "📚  Библиотека манифестов…", self.open_manifesto_library, kind="primary").pack(fill=tk.X, pady=(2, 3))
        make_button(c, "🎲  Случайный манифест", self.random_quote, kind="secondary").pack(fill=tk.X, pady=(0, 4))
        self._combo(c, "font", "Шрифт", {k: k for k in config.FONT_FILES})
        self._combo(c, "tstyle", "Подложка", config.TEXT_STYLES)
        self._combo(c, "text_align", "Выравнивание", config.TEXT_ALIGNS)
        self._slider(c, "font_size", "Размер шрифта", 14, 120)
        self._slider(c, "txt_x", "Позиция X (%)", 2, 85)
        self._slider(c, "txt_y1", "Верхняя надпись Y (%)", 2, 50)
        self._slider(c, "txt_y2", "Нижняя надпись Y (%)", 30, 95)
        self._slider(c, "text_rot", "Поворот надписи (°)", -45.0, 45.0, 1.0)

    def _build_viewport_column(self, col):
        # страницы внизу полосой, лист занимает всё остальное, кнопки плавают поверх листа
        self.viewport_host = col
        self.viewport = InteractivePanZoomCanvas(col)
        self.viewport.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 2))
        self.viewport.on_text_click_relocate = self._on_canvas_text_relocate
        self.viewport.layer_hit = self._layer_hit
        self.viewport.on_layer_press = self._layer_press
        self.viewport.on_layer_move = self._layer_move
        self.viewport.on_transform_changed = lambda z: self.zoom_lbl.config(text=f"{z * 100:.0f}%")
        self.toast = ToastNotification(self.viewport)
        self._build_floating_hud(col)

        strip = tk.Frame(col, bg="#141414")
        strip.pack(fill=tk.X, padx=4, pady=2)
        ctl = tk.Frame(strip, bg="#141414")
        ctl.pack(fill=tk.X, padx=4, pady=(2, 0))
        tk.Label(ctl, text="СТРАНИЦЫ", bg="#141414", fg=MUTED, font=FONT_BOLD, anchor="w").pack(side=tk.LEFT, padx=(2, 12))
        self.strip_canvas = tk.Canvas(strip, bg="#141414", highlightthickness=0, height=self.thumb_box[1] + self.px(40))
        self.strip_scroll = ttk.Scrollbar(strip, orient="horizontal", style="Dark.Horizontal.TScrollbar", command=self.strip_canvas.xview)
        self.strip_canvas.configure(xscrollcommand=self.strip_scroll.set)
        self.strip_canvas.pack(fill=tk.X)
        self.strip_scroll.pack(fill=tk.X)
        self.f_page_btns = tk.Frame(self.strip_canvas, bg="#141414")
        self.strip_canvas.create_window((0, 0), window=self.f_page_btns, anchor="nw")
        self.f_page_btns.bind("<Configure>", lambda e: self.strip_canvas.configure(scrollregion=self.strip_canvas.bbox("all")))

        make_button(ctl, "+ Новая", self.add_page, kind="primary").pack(side=tk.LEFT, padx=3, pady=4)
        make_button(ctl, "Дублировать", self.duplicate_page).pack(side=tk.LEFT, padx=2)
        make_button(ctl, "◀", lambda: self.move_page(-1)).pack(side=tk.LEFT, padx=(8, 1))
        make_button(ctl, "▶", lambda: self.move_page(1)).pack(side=tk.LEFT, padx=1)
        make_button(ctl, "Удалить", self.delete_page, kind="danger").pack(side=tk.LEFT, padx=(8, 2))

    def _build_floating_hud(self, col):
        """Плавающие кнопки над листом (справа сверху), как в браузерной версии."""
        hud = tk.Frame(col, bg=VIEW_BG, highlightthickness=0)
        hud.place(relx=1.0, x=-self.px(14), y=self.px(12), anchor="ne")
        make_button(hud, "💾  PNG", self.export_png, kind="primary").pack(fill=tk.X, pady=2)
        make_button(hud, "🎲  Remix", self.apply_surprise, kind="pink").pack(fill=tk.X, pady=2)
        make_button(hud, "⛶  Вписать", lambda: self.viewport.fit_to_view(), kind="secondary").pack(fill=tk.X, pady=2)
        zoom = tk.Frame(hud, bg=VIEW_BG)
        zoom.pack(fill=tk.X, pady=2)
        make_button(zoom, "1:1", lambda: self.viewport.reset_100_percent(), kind="secondary", padx=8).pack(side=tk.LEFT)
        self.zoom_lbl = tk.Label(zoom, text="100%", bg=VIEW_BG, fg=MUTED, font=FONT_SMALL, width=6)
        self.zoom_lbl.pack(side=tk.LEFT)
        ex = tk.Frame(hud, bg=VIEW_BG)
        ex.pack(fill=tk.X, pady=(4, 0))
        tk.Label(ex, text="Экспорт", bg=VIEW_BG, fg=MUTED, font=FONT_SMALL).pack(side=tk.LEFT)
        self.export_scale = tk.StringVar(value=self.settings.get("export_scale", "2×"))
        self.export_scale.trace_add("write", lambda *a: self.settings.set("export_scale", self.export_scale.get()))
        ttk.Combobox(ex, textvariable=self.export_scale, values=["1×", "2×", "3×"], width=4, state="readonly", font=FONT).pack(side=tk.RIGHT)
        self.hud = hud
        hud.lift()

    def _bind_hotkeys(self):
        r = self.root
        for seq, fn in (
            ("<Control-o>", self.load_image), ("<Control-O>", self.open_project),
            ("<Control-s>", self.export_png), ("<Control-S>", self.save_project),
            ("<Control-r>", self.apply_surprise), ("<Control-n>", self.add_page),
            ("<Control-d>", self.duplicate_page),
            ("<Control-m>", self.open_manifesto_library), ("<Control-z>", self.undo), ("<Control-y>", self.redo), ("<Control-Z>", self.redo), ("<Control-Key-0>", lambda: self.viewport.fit_to_view()),
            ("<Control-Key-1>", lambda: self.viewport.reset_100_percent()), ("<F1>", self.show_help),
        ):
            r.bind(seq, lambda e, f=fn: (f(), "break")[1])

    # ------------------------------------------------------------------ состояние
    @property
    def cv_img(self):
        return self.images.get(self.cur_img_key)

    def _snapshot_state(self):
        s = {k: v.get() for k, v in self.vars.items()}
        s.update(
            txt_top=self.txt_top.get("1.0", tk.END).strip(),
            txt_bottom=self.txt_bot.get("1.0", tk.END).strip(),
            custom_colors=[list(c) for c in self.custom_colors],
            ink2=list(self.ink2),
            ink3=list(self.extra_inks["ink3"]),
            ink4=list(self.extra_inks["ink4"]),
            layers=copy.deepcopy(self.layers),
            crop=list(self.crop),
            seed=self.seed,
            img=self.cur_img_key,
        )
        return s

    def _set_text(self, widget, text):
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)

    def _apply_state(self, s):
        self._loading = True
        self.preset_var.set(PRESET_HINT)  # у каждой страницы свой стиль; apply_preset подставит имя после
        try:
            for key, var in self.vars.items():
                value = s.get(key, config.DEFAULT_STATE[key])
                if key == "layout":
                    value = config.LAYOUT_ALIASES.get(value, value)
                try:
                    var.set(value)
                except (tk.TclError, ValueError):
                    var.set(config.DEFAULT_STATE[key])
            self._set_text(self.txt_top, s.get("txt_top", ""))
            self._set_text(self.txt_bot, s.get("txt_bottom", ""))
            colors = s.get("custom_colors", config.DEFAULT_STATE["custom_colors"])
            self.custom_colors = (tuple(colors[0]), tuple(colors[1]))
            try:
                self.ink2 = tuple(int(v) for v in s.get("ink2", config.DEFAULT_STATE["ink2"]))[:3]
            except (TypeError, ValueError):
                self.ink2 = tuple(config.DEFAULT_STATE["ink2"])
            for key in ("ink3", "ink4"):
                try:
                    self.extra_inks[key] = tuple(int(v) for v in s.get(key, config.DEFAULT_STATE[key]))[:3]
                except (TypeError, ValueError):
                    self.extra_inks[key] = tuple(config.DEFAULT_STATE[key])
            self.layers = copy.deepcopy(s.get("layers") or [])
            self.crop = list(s.get("crop", [0.0, 0.0, 1.0, 1.0]))
            self.seed = int(s.get("seed", config.DEFAULT_STATE["seed"]))
            key = s.get("img")
            self.cur_img_key = key if key in self.images else None
        finally:
            self._loading = False
        self._update_swatches()
        self.sw_ink2.config(bg="#%02x%02x%02x" % tuple(self.ink2))
        for key, sw in self.sw_extra.items():
            sw.config(bg="#%02x%02x%02x" % tuple(self.extra_inks[key]))
        self._refresh_layers_ui()
        self._sync_source_preview()
        self.schedule_render(dirty=False)

    def _init_first_page(self):
        q = manifestos.builtin()[0]
        self._set_text(self.txt_top, q["top"])
        self._set_text(self.txt_bot, q["bottom"])
        self.pages = [self._snapshot_state()]
        self.page_thumbs = [None]
        self._update_swatches()
        self._sync_source_preview()
        self._refresh_page_strip()
        self._reset_history()
        self.schedule_render(dirty=False)

    # ------------------------------------------------------------------ палитра
    def _palette_colors(self):
        name = self.vars["palette"].get()
        if name == config.CUSTOM_PALETTE:
            paper, ink = self.custom_colors
        else:
            paper, ink = config.RISO_PALETTES.get(name, config.RISO_PALETTES["Classic B&W (Xerox)"])
        return (ink, paper) if self.vars["invert"].get() else (paper, ink)

    def _update_swatches(self):
        paper, ink = self._palette_colors()
        self.sw_paper.config(bg="#%02x%02x%02x" % tuple(paper))
        self.sw_ink.config(bg="#%02x%02x%02x" % tuple(ink))

    def _pick_ink2(self):
        rgb, _hex = colorchooser.askcolor(color="#%02x%02x%02x" % tuple(self.ink2), title="Цвет второй краски", parent=self.root)
        if not rgb:
            return
        self.ink2 = tuple(int(v) for v in rgb)
        self.sw_ink2.config(bg="#%02x%02x%02x" % self.ink2)
        self.schedule_render()

    @property
    def images(self):
        return self._images

    @images.setter
    def images(self, value):
        self._images = value
        self.engine.layer_images = value  # фото-объекты берут картинки отсюда

    # ------------------------------------------------------------------ слои
    def _refresh_layers_ui(self, select=None):
        lb = getattr(self, "layer_list", None)
        if lb is None:
            return
        import stickers
        lb.delete(0, tk.END)
        for i, ly in enumerate(self.layers):
            off = "○ " if ly.get("hidden") else ""
            if ly.get("type") == "sticker":
                name = stickers.STICKERS.get(ly.get("sticker"), ("?",))[0]
                lb.insert(tk.END, f"{i + 1}. {off}✦ {name}")
            elif ly.get("type") == "bitmap":
                lb.insert(tk.END, f"{i + 1}. {off}▣ Фото")
            else:
                lb.insert(tk.END, f"{i + 1}. {off}Aa «{str(ly.get('text', '')).splitlines()[0][:22] if ly.get('text') else 'пусто'}»")
        if self.layers:
            idx = len(self.layers) - 1 if select is None else max(0, min(select, len(self.layers) - 1))
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
        self._load_layer_controls()
        self._update_layer_frame()

    # --- слои мышью: выбрать и перетащить прямо на листе
    def _layer_box(self, ly, W, H):
        """Примерная рамка слоя в долях листа: (cx, cy, w, h). Угол поворота учитывается по габаритам."""
        size = max(0.02, float(ly.get("size", 0.2)))
        if ly.get("type") == "sticker":
            bw, bh = size * W, size * W
        elif ly.get("type") == "bitmap":
            src = self.images.get(ly.get("img"))
            bw = size * W
            bh = bw * (src.shape[0] / src.shape[1]) if src is not None else bw
        else:
            lines = str(ly.get("text", "")).strip().splitlines() or [""]
            fpx = max(8, size * W * 0.5)
            bw = (max(len(x) for x in lines) * fpx * 0.62 + fpx * 0.6) * float(ly.get("sx", 1.0) or 1.0)
            bh = len(lines) * fpx * 1.15 + fpx * 0.6
            if (ly.get("warp") or "none") != "none":
                bh *= 1 + 0.9 * float(ly.get("warp_k", 0.5) if ly.get("warp_k") is not None else 0.5)
        rot = math.radians(float(ly.get("rot", 0)))
        ew = abs(bw * math.cos(rot)) + abs(bh * math.sin(rot))
        eh = abs(bw * math.sin(rot)) + abs(bh * math.cos(rot))
        return float(ly.get("x", 0.5)), float(ly.get("y", 0.5)), ew / W, eh / H

    def _layer_hit(self, fx, fy):
        img = self.viewport.current_image
        if img is None or not self.layers:
            return None
        for i in range(len(self.layers) - 1, -1, -1):  # верхний слой первым
            if self.layers[i].get("hidden"):
                continue
            cx, cy, bw, bh = self._layer_box(self.layers[i], img.width, img.height)
            if abs(fx - cx) <= bw / 2 and abs(fy - cy) <= bh / 2:
                return i
        return None

    def _layer_press(self, idx):
        self.layer_list.selection_clear(0, tk.END)
        self.layer_list.selection_set(idx)
        self.layer_list.see(idx)
        self._load_layer_controls()
        self._update_layer_frame()
        ly = self.layers[idx]
        return float(ly.get("x", 0.5)), float(ly.get("y", 0.5))

    def _layer_move(self, idx, nx, ny):
        ly = self.layers[idx]
        ly["x"], ly["y"] = round(nx, 4), round(ny, 4)
        self._load_layer_controls()
        self._update_layer_frame()
        self.preset_var.set(PRESET_HINT)
        self.schedule_render()

    def _update_layer_frame(self):
        img = self.viewport.current_image
        ly = self._sel_layer() if getattr(self, "layer_list", None) is not None else None
        self.viewport.layer_frame = self._layer_box(ly, img.width, img.height) if (ly and img is not None) else None
        self.viewport.redraw()

    def _sel_layer(self):
        sel = self.layer_list.curselection()
        if sel and sel[0] < len(self.layers):
            return self.layers[sel[0]]
        return None

    def _load_layer_controls(self):
        ly = self._sel_layer()
        self._layer_loading = True
        try:
            if ly:
                self.ly_vars["x"].set(round(float(ly.get("x", 0.5)) * 100))
                self.ly_vars["y"].set(round(float(ly.get("y", 0.5)) * 100))
                self.ly_vars["size"].set(round(float(ly.get("size", 0.2)) * 100))
                self.ly_vars["rot"].set(round(float(ly.get("rot", 0))))
                self.ly_warp.set(ly.get("warp") or "none")
                self.ly_vars["warp_k"].set(round(float(ly.get("warp_k", 0.5) if ly.get("warp_k") is not None else 0.5) * 100))
                self.ly_vars["sx"].set(round(float(ly.get("sx", 1.0) or 1.0) * 100))
                self.ly_vars["opacity"].set(round(float(ly.get("opacity", 1.0) if ly.get("opacity") is not None else 1.0) * 100))
                self.ly_text.set(ly.get("text", ""))
                self.ly_color.set(ly.get("color", "ink"))
                self.ly_style.set(ly.get("style", "box"))
        finally:
            self._layer_loading = False

    def _layer_var_changed(self, key):
        if self._layer_loading:
            return
        ly = self._sel_layer()
        if not ly:
            return
        if key in ("x", "y", "size"):
            ly[key] = float(self.ly_vars[key].get()) / 100.0
        elif key == "rot":
            ly["rot"] = float(self.ly_vars["rot"].get())
        elif key == "warp":
            ly["warp"] = self.ly_warp.get()
        elif key == "warp_k":
            ly["warp_k"] = float(self.ly_vars["warp_k"].get()) / 100.0
        elif key == "sx":
            ly["sx"] = float(self.ly_vars["sx"].get()) / 100.0
        elif key == "opacity":
            ly["opacity"] = float(self.ly_vars["opacity"].get()) / 100.0
        elif key == "text":
            ly["text"] = self.ly_text.get()
        elif key == "color":
            ly["color"] = self.ly_color.get()
        elif key == "style":
            ly["style"] = self.ly_style.get()
        self.preset_var.set(PRESET_HINT)
        self.schedule_render()

    def _new_layer(self, **kw):
        ly = {"type": "text", "text": "", "sticker": "star", "x": 0.5, "y": 0.5, "size": 0.2, "rot": 0, "color": "ink", "style": "box", "font": "Arial Black"}
        ly.update(kw)
        self.layers.append(ly)
        if self._fly not in ("all", "s5"):
            self._set_fly("s5")
        self._refresh_layers_ui()
        self.schedule_render()

    def _add_text_layer(self):
        text = simpledialog.askstring("Новая надпись", "Текст:", parent=self.root)
        if text:
            self._new_layer(type="text", text=text)

    def _add_sticker_layer(self):
        import stickers
        names = list(stickers.STICKERS)
        dlg = tk.Toplevel(self.root)
        dlg.title("Стикеры")
        dlg.transient(self.root)
        dlg.configure(bg=PANEL)
        lb = tk.Listbox(dlg, height=min(16, len(names)), bg=FIELD, fg=FG, selectbackground=ACCENT, font=FONT, relief="flat", exportselection=False)
        for n in names:
            lb.insert(tk.END, stickers.STICKERS[n][0])
        lb.pack(padx=10, pady=10)
        lb.selection_set(0)

        def ok(_e=None):
            sel = lb.curselection()
            dlg.destroy()
            if sel:
                self._new_layer(type="sticker", sticker=names[sel[0]], size=0.22)

        lb.bind("<Double-Button-1>", ok)
        make_button(dlg, "Добавить", ok, kind="primary").pack(pady=(0, 10))
        dlg.grab_set()

    def _ensure_free_start(self):
        """Свободный лист без слоёв пуст: кладём на него фото страницы, чтобы было что двигать."""
        if self.layers or not self.cur_img_key or self.cur_img_key not in self.images:
            return
        self._new_layer(type="bitmap", img=self.cur_img_key, size=0.8, backing=True, torn=True, dot=5, contrast=1.6, cutout=False, opacity=1.0)

    def _apply_text_preset(self, name):
        ly = self._sel_layer()
        if not ly or name not in config.TEXT_PRESETS or ly.get("type") != "text":
            return
        base = {k: v for k, v in config.TEXT_DEFAULTS.items() if k != "rot"}
        ly.update(base)
        ly.update(config.TEXT_PRESETS[name])
        self._refresh_layers_ui(select=self.layers.index(ly))
        self.preset_var.set(PRESET_HINT)
        self.schedule_render()

    def _apply_layer_template(self, name):
        tpl = config.LAYER_TEMPLATES.get(name)
        if not tpl:
            return
        has_photo = bool(self.cur_img_key and self.cur_img_key in self.images)
        base = {k: v for k, v in config.TEXT_DEFAULTS.items() if k != "rot"}
        out = []
        for t in tpl:
            t = dict(t)
            photo, preset = t.pop("photo", False), t.pop("preset", None)
            t.pop("text_en", None)
            if photo:
                if has_photo:
                    out.append(dict({"type": "bitmap", "img": self.cur_img_key, "x": 0.5, "y": 0.5, "size": 0.8, "rot": 0, "color": "ink", "opacity": 1.0,
                                     "backing": True, "torn": True, "dot": 5, "contrast": 1.6, "cutout": False}, **t))
            elif t.get("type") == "sticker":
                out.append(dict({"color": "ink", "rot": 0, "opacity": 1.0}, **t))
            else:
                ly = {"type": "text", "sticker": "star", "color": "ink", "style": "box", "font": "Arial Black", "opacity": 1.0, "rot": 0}
                ly.update(base)
                ly.update(config.TEXT_PRESETS.get(preset, {}))
                ly.update(t)
                out.append(ly)
        self.layers = out
        self.vars["layout"].set("free")
        self.txt_top.delete("1.0", tk.END)
        self.txt_bot.delete("1.0", tk.END)
        self._refresh_layers_ui()
        self.preset_var.set(PRESET_HINT)
        self.schedule_render()
        self._mark_dirty(immediate=True)
        if not has_photo and any(t.get("photo") for t in tpl):
            messagebox.showinfo("Шаблон", "Фото не загружено: шаблон собран без него. Загрузи фото и выбери шаблон ещё раз.", parent=self.root)

    def _add_photo_layer(self):
        path = filedialog.askopenfilename(
            parent=self.root, initialdir=self._dir("images"), title="Фото для слоя",
            filetypes=[("Изображения", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            img = read_image_bgr(path)
        except Exception:
            messagebox.showerror("Ошибка", "Не удалось открыть файл.", parent=self.root)
            return
        key = self._new_img_key()
        self.images[key] = img
        self._new_layer(type="bitmap", img=key, size=0.45, backing=True, torn=True, dot=5, contrast=1.6, cutout=False, opacity=1.0)

    def _layer_action(self, what):
        sel = self.layer_list.curselection()
        if not sel:
            return
        i = sel[0]
        if what == "delete":
            del self.layers[i]
            self._refresh_layers_ui()
        elif what in ("hide", "flip"):
            ly = self.layers[i]
            ly["hidden" if what == "hide" else "flipx"] = not ly.get("hidden" if what == "hide" else "flipx")
            self._refresh_layers_ui(select=i)
        elif what in ("up", "down"):
            j = i + 1 if what == "up" else i - 1
            if 0 <= j < len(self.layers):
                self.layers[i], self.layers[j] = self.layers[j], self.layers[i]
                self._refresh_layers_ui(select=j)
        elif what == "copy":
            c = copy.deepcopy(self.layers[i])
            if c.get("img") in self.images:
                nk = self._new_img_key()
                self.images[nk] = self.images[c["img"]]
                c["img"] = nk
            c["x"] = min(0.95, c.get("x", 0.5) + 0.05)
            c["y"] = min(0.95, c.get("y", 0.5) + 0.05)
            self.layers.append(c)
            self._refresh_layers_ui()
        self.preset_var.set(PRESET_HINT)
        self.schedule_render()

    def _pick_extra_ink(self, key):
        rgb, _hex = colorchooser.askcolor(color="#%02x%02x%02x" % tuple(self.extra_inks[key]), title="Цвет краски", parent=self.root)
        if not rgb:
            return
        self.extra_inks[key] = tuple(int(v) for v in rgb)
        self.sw_extra[key].config(bg="#%02x%02x%02x" % self.extra_inks[key])
        self.schedule_render()

    def _pick_color(self, which):
        current = list(self.custom_colors)
        if self.vars["palette"].get() != config.CUSTOM_PALETTE:
            current = list(config.RISO_PALETTES.get(self.vars["palette"].get(), current))
        rgb, _hex = colorchooser.askcolor(color="#%02x%02x%02x" % tuple(current[which]), title="Цвет", parent=self.root)
        if not rgb:
            return
        current[which] = tuple(int(v) for v in rgb)
        self.custom_colors = (tuple(current[0]), tuple(current[1]))
        if self.vars["palette"].get() == config.CUSTOM_PALETTE:
            self._update_swatches()
            self.schedule_render()
        else:
            self.vars["palette"].set(config.CUSTOM_PALETTE)  # переключит палитру и запустит рендер

    # ------------------------------------------------------------------ фото и кадрирование
    def _on_censor_toggle(self):
        if self.vars["censor"].get() and not self.engine.face_cascade:
            self.vars["censor"].set(False)
            self.toast.show("Детектор лиц недоступен: не найден файл haarcascade", kind="error", duration=3500)

    def _on_crop_changed(self, crop):
        self.crop = list(crop)
        self.schedule_render()

    def _sync_source_preview(self):
        cv = self.cv_img
        if cv is None:
            self.canvas_crop._placeholder = "Фото не загружено\n\nCtrl+O — загрузить"
            self.canvas_crop.image = None
            self.canvas_crop.crop = [0.0, 0.0, 1.0, 1.0]
            self.canvas_crop._render()
            self.src_info.config(text="")
            self.viewport.set_overlay("Фото не загружено — показан тест.\nCtrl+O, чтобы загрузить своё")
        else:
            rgb = cv2.cvtColor(cv, cv2.COLOR_BGR2RGB)
            self.canvas_crop.image = Image.fromarray(rgb)
            self.canvas_crop.set_crop(self.crop)
            self.src_info.config(text=f"{cv.shape[1]}×{cv.shape[0]} px")
            self.viewport.set_overlay(None)

    def _new_img_key(self):
        self._img_counter += 1
        return f"img{self._img_counter}"

    def load_image(self):
        paths = filedialog.askopenfilenames(
            parent=self.root, initialdir=self._dir("images"), title="Выберите одно или несколько фото",
            filetypes=[("Изображения", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"), ("Все файлы", "*.*")],
        )
        if not paths:
            return
        self._remember_dir("images", paths[0])
        self._load_image_paths(paths)

    def _load_image_paths(self, paths):
        loaded, failed = [], []
        for p in paths:
            try:
                loaded.append((os.path.basename(p), read_image_bgr(p)))
            except Exception:
                log.warning("не удалось открыть фото %s", p, exc_info=True)
                failed.append(os.path.basename(p))
        if not loaded:
            messagebox.showerror("Ошибка", "Не удалось открыть файл:\n" + "\n".join(failed), parent=self.root)
            return

        self.pages[self.cur_page_idx] = self._snapshot_state()
        for i, (_name, img) in enumerate(loaded):
            key = self._new_img_key()
            self.images[key] = img
            if i == 0:
                self.cur_img_key = key
                self.crop = [0.0, 0.0, 1.0, 1.0]
                self.pages[self.cur_page_idx] = self._snapshot_state()
            else:  # каждое следующее фото - новая страница в том же стиле
                st = copy.deepcopy(self.pages[self.cur_page_idx])
                st.update(img=key, crop=[0.0, 0.0, 1.0, 1.0], seed=random.randint(1, 10 ** 6))
                self._insert_page(self.cur_page_idx + 1 + (i - 1), st)
        self._garbage_collect_images()
        self._sync_source_preview()
        self._build_missing_thumbs()
        self._refresh_page_strip()
        self.schedule_render()
        self._mark_dirty(immediate=True)
        msg = f"Фото загружено: {loaded[0][0]}" if len(loaded) == 1 else f"Загружено фото: {len(loaded)} (страниц добавлено: {len(loaded) - 1})"
        self.toast.show(msg + (f" · не открылись: {len(failed)}" if failed else ""), kind="error" if failed else "ok", duration=3000)

    def transform_photo(self, kind):
        """Поворот и зеркало фото страницы. Результат - новое фото, поэтому работает «Отменить»."""
        img = self.cv_img
        if img is None:
            self.toast.show("Сначала загрузите фото", kind="error")
            return
        if kind == "cw":
            new = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif kind == "ccw":
            new = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            new = cv2.flip(img, 1)
        key = self._new_img_key()
        self.images[key] = np.ascontiguousarray(new)
        self.cur_img_key = key
        self.crop = [0.0, 0.0, 1.0, 1.0]
        self._sync_source_preview()
        self.schedule_render()
        self._mark_dirty(immediate=True)

    def _garbage_collect_images(self):
        def keys(pages):
            return {p.get("img") for p in pages} | {ly.get("img") for p in pages for ly in (p.get("layers") or []) if isinstance(ly, dict)}
        used = keys(self.pages) | {self.cur_img_key} | {ly.get("img") for ly in self.layers}
        for doc in self.hist:  # фото из истории нужны для «Отменить»
            used |= keys(doc["pages"])
        for k in [k for k in self.images if k not in used]:
            del self.images[k]

    # ------------------------------------------------------------------ рендер предпросмотра
    def schedule_render(self, dirty=True):
        if self._loading:
            return
        if dirty:
            self._mark_dirty()
        self.render_token += 1
        self.worker.submit((self.render_token, self.cv_img, self._snapshot_state()))
        self.status_var.set("⏳ рендер…")

    def _poll_results(self):
        latest = None
        try:
            while True:
                latest = self.results.get_nowait()
        except queue.Empty:
            pass
        if latest:
            kind, token, a, b, secs = latest
            if token == self.render_token:
                if kind == "ok":
                    self._on_rendered(a, b, secs)
                else:
                    self.status_var.set("ошибка рендера")
                    self.toast.show(f"Ошибка рендера: {a}", kind="error", duration=4000)
        self.root.after(30, self._poll_results)

    def _on_rendered(self, poster, stencil, secs):
        self.final_poster, self.stencil_1bit = poster, stencil
        self.viewport.set_image(poster, keep_view=True)
        self._update_layer_frame()
        self._set_thumb(self.cur_page_idx, poster)
        self.status_var.set(f"стр. {self.cur_page_idx + 1}/{len(self.pages)}  ·  {poster.width}×{poster.height} px  ·  рендер {secs:.2f} с")

    def _on_canvas_text_relocate(self, nx, ny):
        x = int(np.clip(nx * 100, 2, 85))
        y = ny * 100
        v1, v2 = self.vars["txt_y1"], self.vars["txt_y2"]
        self._loading = True
        try:
            self.vars["txt_x"].set(x)
            if abs(y - v1.get()) <= abs(y - v2.get()):  # двигаем ту надпись, что ближе к курсору
                v1.set(int(np.clip(y, 2, 50)))
            else:
                v2.set(int(np.clip(y, 30, 95)))
        finally:
            self._loading = False
        self.schedule_render()

    def reshuffle_seed(self):
        self.seed = random.randint(1, 10 ** 6)
        self.schedule_render()

    def random_quote(self):
        self.apply_manifesto(random.choice(manifestos.all_items()), toast=False)

    # ------------------------------------------------------------------ библиотека манифестов
    def open_manifesto_library(self):
        win = getattr(self, "_manifest_win", None)
        if win is not None and win.winfo_exists():
            win.deiconify()
            win.lift()
            return
        self._manifest_win = ManifestoDialog(self)

    def apply_manifesto(self, item, toast=True):
        self._set_text(self.txt_top, item["top"])
        self._set_text(self.txt_bot, item["bottom"])
        self.schedule_render()
        self._mark_dirty(immediate=True)
        if toast:
            self.toast.show("✓ Манифест применён к странице")

    def spread_manifestos(self, items):
        """Каждой странице по своему манифесту, начиная с выбранного (по кругу)."""
        if not items:
            return
        self.pages[self.cur_page_idx] = self._snapshot_state()
        for i, st in enumerate(self.pages):
            st["txt_top"], st["txt_bottom"] = items[i % len(items)]["top"], items[i % len(items)]["bottom"]
            if i != self.cur_page_idx:
                self.page_thumbs[i] = None
        cur = self.pages[self.cur_page_idx]
        self._loading = True
        try:
            self._set_text(self.txt_top, cur["txt_top"])
            self._set_text(self.txt_bot, cur["txt_bottom"])
        finally:
            self._loading = False
        self._build_missing_thumbs()
        self._refresh_page_strip()
        self.schedule_render()
        self._mark_dirty(immediate=True)
        self.toast.show(f"✓ Манифесты розданы: {len(self.pages)} стр.")

    def save_current_manifesto(self):
        top = self.txt_top.get("1.0", tk.END).strip()
        bottom = self.txt_bot.get("1.0", tk.END).strip()
        if not (top or bottom):
            self.toast.show("На странице нет текста", kind="error")
            return False
        try:
            saved = manifestos.save_user(top, bottom)
        except OSError as exc:
            log.exception("не удалось сохранить манифест")
            messagebox.showerror("Ошибка", f"Не удалось сохранить манифест:\n{exc}", parent=self.root)
            return False
        self.toast.show("✓ Сохранено в «Мои манифесты»" if saved else "Такой манифест уже есть", kind="ok" if saved else "info")
        return saved

    def apply_surprise(self):
        L = {k: v.get() for k, v in self.locks.items()}
        self._loading = True
        try:
            v = self.vars
            if not L["text"]:
                q = random.choice(manifestos.all_items())
                self._set_text(self.txt_top, q["top"])
                self._set_text(self.txt_bot, q["bottom"])
                v["tstyle"].set(random.choice(list(config.TEXT_STYLES.values())))
            if not L["palette"]:
                v["palette"].set(random.choice(list(config.RISO_PALETTES)))
            if not L["layout"]:
                v["layout"].set(random.choice(list(config.LAYOUTS.values())))
                v["rows"].set(random.randint(4, 8))
            if not L["raster"]:
                v["dither"].set(random.choice(list(config.DITHERS.values())))
                v["dot_size"].set(random.randint(5, 12))
                v["angle"].set(random.randint(0, 90))
            if not L["font"]:
                v["font"].set(random.choice(list(config.FONT_FILES)))
            if not L["wear"]:
                v["fold"].set(random.randint(30, 90) if random.random() < 0.25 else 0)
                v["stains"].set(random.randint(20, 80) if random.random() < 0.3 else 0)
                v["dust"].set(random.randint(15, 70) if random.random() < 0.4 else 0)
                v["holes"].set(1 if random.random() < 0.15 else 0)
            v["tilt"].set(round(random.uniform(0.0, 2.5), 1))
            v["loss"].set(random.randint(10, 60))
            self.seed = random.randint(1, 10 ** 6)
        finally:
            self._loading = False
        self._update_swatches()
        self.schedule_render()
        self.toast.show("🎲 Сгенерирован новый стиль")

    MUTATE_RANGES = {"dot_size": (3, 22), "angle": (0, 90), "contrast": (1.0, 4.5), "noise": (0, 100), "streaks": (0, 100), "misreg": (0, 12),
                     "loss": (0, 100), "paper": (0, 100), "copier_edge": (0, 100), "tilt": (0.0, 5.0), "fold": (0, 100), "stains": (0, 100),
                     "dust": (0, 100), "overprint": (0, 100), "tape": (0, 100)}

    def mutate_look(self):
        """Слегка сдвигает числовые параметры вида (около 9% диапазона в обе стороны)."""
        self._loading = True
        try:
            for key, (lo, hi) in self.MUTATE_RANGES.items():
                var = self.vars.get(key)
                if var is None:
                    continue
                val = min(hi, max(lo, float(var.get()) + random.uniform(-0.09, 0.09) * (hi - lo)))
                var.set(round(val, 1) if isinstance(config.DEFAULT_STATE[key], float) else int(round(val)))
            self.seed = random.randint(1, 10 ** 6)
        finally:
            self._loading = False
        self.preset_var.set(PRESET_HINT)
        self.schedule_render()
        self.toast.show("🧬 Вид слегка изменён")

    # ------------------------------------------------------------------ страницы
    def _insert_page(self, idx, state, thumb=None):
        self.pages.insert(idx, state)
        self.page_thumbs.insert(idx, thumb)

    def _goto(self, idx):
        self.cur_page_idx = idx
        self._apply_state(self.pages[idx])
        self._refresh_page_strip()

    def _set_thumb(self, idx, poster):
        if not (0 <= idx < len(self.pages)):
            return
        thumb = poster.copy()
        thumb.thumbnail(self.thumb_box, Image.Resampling.BILINEAR)
        self.page_thumbs[idx] = ImageTk.PhotoImage(thumb)
        if idx < len(self.page_btns):
            self.page_btns[idx].config(image=self.page_thumbs[idx], width=0)

    def _refresh_page_strip(self):
        for w in self.f_page_btns.winfo_children():
            w.destroy()
        self.page_btns = []
        for i in range(len(self.pages)):
            active = i == self.cur_page_idx
            btn = tk.Button(
                self.f_page_btns, text=str(i + 1), image=self.page_thumbs[i] if self.page_thumbs[i] else "",
                compound="top", bg=ACCENT if active else "#262626", fg="#0a0a0a" if active else MUTED,
                activebackground=ACCENT, font=FONT_BOLD if active else FONT, relief="flat", bd=0, padx=4, pady=3,
                cursor="hand2", command=lambda idx=i: self.switch_page(idx),
                width=self.thumb_box[0] // 7 if not self.page_thumbs[i] else 0,
            )
            btn.pack(side=tk.LEFT, padx=2, pady=3)
            self.page_btns.append(btn)
        self.root.update_idletasks()
        n = max(1, len(self.pages))
        self.strip_canvas.xview_moveto(max(0.0, (self.cur_page_idx - 2) / n))

    def switch_page(self, idx):
        if idx == self.cur_page_idx or not (0 <= idx < len(self.pages)):
            return
        self.pages[self.cur_page_idx] = self._snapshot_state()
        self._goto(idx)

    def add_page(self):
        """Новая страница: тот же стиль, но без фото и с новым манифестом."""
        self.pages[self.cur_page_idx] = self._snapshot_state()
        st = copy.deepcopy(self.pages[self.cur_page_idx])
        q = random.choice(manifestos.all_items())
        st.update(img=None, crop=[0.0, 0.0, 1.0, 1.0], seed=random.randint(1, 10 ** 6),
                  txt_top=q["top"], txt_bottom=q["bottom"])
        self._insert_page(self.cur_page_idx + 1, st)
        self._goto(self.cur_page_idx + 1)
        self._mark_dirty(immediate=True)
        self.toast.show(f"✓ Добавлена страница {self.cur_page_idx + 1} — загрузите для неё фото (Ctrl+O)")

    def duplicate_page(self):
        self.pages[self.cur_page_idx] = self._snapshot_state()
        st = copy.deepcopy(self.pages[self.cur_page_idx])
        self._insert_page(self.cur_page_idx + 1, st, self.page_thumbs[self.cur_page_idx])
        self._goto(self.cur_page_idx + 1)
        self._mark_dirty(immediate=True)
        self.toast.show("✓ Страница продублирована")

    def move_page(self, delta):
        j = self.cur_page_idx + delta
        if not (0 <= j < len(self.pages)):
            return
        self.pages[self.cur_page_idx] = self._snapshot_state()
        i = self.cur_page_idx
        for lst in (self.pages, self.page_thumbs):
            lst[i], lst[j] = lst[j], lst[i]
        self.cur_page_idx = j
        self._refresh_page_strip()
        self._mark_dirty(immediate=True)
        self.status_var.set(f"стр. {j + 1}/{len(self.pages)}")

    def delete_page(self):
        if len(self.pages) <= 1:
            self.toast.show("В проекте должна остаться минимум 1 страница", kind="error")
            return
        if not messagebox.askyesno("Удалить страницу", f"Удалить страницу {self.cur_page_idx + 1}?", parent=self.root):
            return
        del self.pages[self.cur_page_idx]
        del self.page_thumbs[self.cur_page_idx]
        self.cur_page_idx = max(0, self.cur_page_idx - 1)
        self._goto(self.cur_page_idx)
        self._mark_dirty(immediate=True)

    # ------------------------------------------------------------------ экспорт (в фоне, с прогрессом)
    def _run_job(self, title, work, on_done):
        if self._busy:
            return
        self._busy = True
        dlg = ProgressDialog(self.root, title, "Подготовка…")
        job = {"text": "Подготовка…", "frac": 0.0, "done": False, "result": None, "error": None}

        def progress(text, frac):
            job["text"], job["frac"] = text, frac

        def target():
            try:
                job["result"] = work(progress)
            except Exception as exc:
                log.exception("ошибка фоновой задачи")
                job["error"] = exc
            finally:
                job["done"] = True

        threading.Thread(target=target, daemon=True).start()

        def poll():
            dlg.set_progress(job["text"], job["frac"])
            if not job["done"]:
                self.root.after(80, poll)
                return
            dlg.grab_release()
            dlg.destroy()
            self._busy = False
            if job["error"]:
                messagebox.showerror("Ошибка экспорта", f"{type(job['error']).__name__}: {job['error']}", parent=self.root)
            else:
                on_done(job["result"])
                if self.sound_on.get():
                    copier_sound.play()

        poll()

    def _scale(self):
        return int(self.export_scale.get().rstrip("×") or 1)

    def _pages_for_export(self):
        self.pages[self.cur_page_idx] = self._snapshot_state()
        return [(copy.deepcopy(st), self.images.get(st.get("img"))) for st in self.pages]

    def export_png(self):
        path = self._ask_save("export", defaultextension=".png", filetypes=[("PNG", "*.png")], initialfile="zine_page.png")
        if not path:
            return
        state, img = self._snapshot_state(), self.cv_img
        scale = self._scale()

        def work(progress):
            progress("Рендеринг страницы…", 0.3)
            out, _ = self.engine.render_zine_page(img, state, scale=scale)
            progress("Сохранение PNG…", 0.9)
            out.save(path, dpi=(300, 300))
            return out.size

        self._run_job("Экспорт PNG", work, lambda size: self.toast.show(f"✓ PNG сохранён ({size[0]}×{size[1]} px)"))

    def export_stencil(self):
        path = self._ask_save("export", defaultextension=".png", filetypes=[("PNG 1-bit", "*.png")], initialfile="zine_stencil.png")
        if not path:
            return
        state, img = self._snapshot_state(), self.cv_img
        scale = self._scale()

        def work(progress):
            progress("Рендеринг трафарета…", 0.3)
            _, bits = self.engine.render_zine_page(img, state, scale=scale)
            progress("Сохранение…", 0.9)
            bits.save(path, dpi=(300, 300))

        self._run_job("Экспорт трафарета", work, lambda _r: self.toast.show("✓ 1-bit трафарет сохранён (чёрный = краска)"))

    def export_separations(self):
        path = self._ask_save("export", defaultextension=".zip", filetypes=[("ZIP", "*.zip")], initialfile="zine_riso.zip")
        if not path:
            return
        state, img = self._snapshot_state(), self.cv_img
        scale = self._scale()

        def work(progress):
            import io, zipfile
            progress("Разделение красок…", 0.3)
            plates, (paper, ink, ink2) = self.engine.render_separations(img, state, scale=scale)
            hx = lambda c: "#%02X%02X%02X" % tuple(int(v) for v in c)
            lines = ["XEROX ZINE STUDIO - INK SEPARATIONS / RAZDELENIE KRASOK", "",
                     f"ink1: ink {hx(ink)}", f"ink2: ink {hx(ink2)}" if ink2 else "ink2: none (overprint is 0)",
                     *[f"{n}: ink {hx(rgb)}" for n, (_p, rgb) in getattr(self.engine, "last_extra", {}).items()],
                     f"paper: {hx(paper)}", "",
                     "Black = ink, white = nothing. Print ink1, let it dry, then lay the SAME sheet",
                     "into the machine again aligned by the corner crosses and print ink2.",
                     "Slight misregistration is not a bug. It is the point.", "",
                     "Чёрное = краска. Печатай ink1, дай высохнуть, затем тот же лист снова,",
                     "совместив по угловым крестам, и печатай ink2. Небольшой сдвиг - не ошибка, а суть.", ""]
            with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
                for name, im in plates:
                    buf = io.BytesIO(); im.save(buf, "PNG", dpi=(300, 300)); z.writestr(f"zine_{name}.png", buf.getvalue())
                z.writestr("README.txt", "\n".join(lines).encode("utf-8"))

        self._run_job("Разделение красок", work, lambda _r: self.toast.show("✓ Пластины красок сохранены (ZIP)"))

    def export_multipage_pdf(self):
        path = self._ask_save("export", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="zine_book.pdf")
        if not path:
            return
        items, scale = self._pages_for_export(), self._scale()

        def work(progress):
            def pages():
                for i, (st, img) in enumerate(items):
                    progress(f"Рендеринг страницы {i + 1} из {len(items)}…", i / (len(items) + 1))
                    yield self.engine.render_zine_page(img, st, scale=scale)[0]

            return pdf_writer.write_pdf(path, pages(), dpi=300.0)

        self._run_job("Экспорт PDF", work, lambda n: self.toast.show(f"✓ PDF ({n} стр.) готов"))

    def export_pdf_a4(self):
        path = self._ask_save("export", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="zine_book_A4.pdf")
        if not path:
            return
        items = self._pages_for_export()

        def work(progress):
            aw, ah, margin = 2480, 3508, 118  # A4 при 300 DPI, поля 10 мм
            pw, ph = aw - 2 * margin, ah - 2 * margin

            def sheets():
                for i, (st, img) in enumerate(items):
                    progress(f"Рендеринг страницы {i + 1} из {len(items)}…", i / (len(items) + 1))
                    bw, bh = config.CANVAS_FORMATS.get(st.get("format"), (1000, 1500))
                    k = min(pw / bw, ph / bh)
                    size = (int(bw * k), int(bh * k))
                    page = self.engine.render_zine_page(img, st, out_size=size)[0]
                    sheet = Image.new("RGB", (aw, ah), (255, 255, 255))
                    sheet.paste(page, ((aw - size[0]) // 2, (ah - size[1]) // 2))
                    yield sheet

            return pdf_writer.write_pdf(path, sheets(), dpi=300.0)

        self._run_job("PDF для печати", work, lambda n: self.toast.show(f"✓ PDF A4 ({n} стр.) готов к печати"))

    def export_booklet(self, paper):
        label = "Letter" if paper == "letter" else "A4"
        path = self._ask_save("export", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=f"zine_booklet_{label}.pdf")
        if not path:
            return
        items = self._pages_for_export()

        def work(progress):
            pw_, ph_ = (3300, 2550) if paper == "letter" else (3508, 2480)  # альбомный лист, 300 DPI
            margin, half = 70, pw_ // 2
            sides = imposition.booklet_sides(len(items))

            def gen():
                for si, side in enumerate(sides):
                    progress(f"Сторона листа {si + 1} из {len(sides)}…", si / (len(sides) + 1))
                    sheet = Image.new("RGB", (pw_, ph_), (255, 255, 255))
                    for h, idx in enumerate(side):
                        if idx >= len(items):
                            continue
                        st, img = items[idx]
                        bw, bh = config.CANVAS_FORMATS.get(st.get("format"), (1000, 1500))
                        k = min((half - 2 * margin) / bw, (ph_ - 2 * margin) / bh)
                        size = (int(bw * k), int(bh * k))
                        page = self.engine.render_zine_page(img, st, out_size=size)[0]
                        sheet.paste(page, (h * half + (half - size[0]) // 2, (ph_ - size[1]) // 2))
                    dr = ImageDraw.Draw(sheet)
                    for y in range(0, ph_, 26):
                        dr.line([(half, y), (half, y + 14)], fill=(150, 150, 150), width=2)
                    yield sheet

            return pdf_writer.write_pdf(path, gen(), dpi=300.0)

        self._run_job(f"Буклет {label}", work, lambda n: self.toast.show(f"✓ Буклет готов ({n} стор.). Печатай двусторонне, переворот по короткой стороне, сложи пополам"))

    def export_calibration(self):
        path = self._ask_save("export", defaultextension=".png", filetypes=[("PNG", "*.png")], initialfile="printer_calibration_A4.png")
        if not path:
            return

        def work(progress):
            progress("Лист калибровки…", 0.4)
            imposition.calibration_sheet(self.engine).save(path, dpi=(300, 300))

        self._run_job("Лист калибровки", work, lambda _r: self.toast.show("✓ Лист калибровки сохранён"))

    def export_all_png(self):
        items = self._pages_for_export()
        folder = filedialog.askdirectory(parent=self.root, initialdir=self._dir("export"), title="Папка для PNG всех страниц", mustexist=True)
        if not folder:
            return
        self._remember_dir("export", os.path.join(folder, "_"))
        width = max(2, len(str(len(items))))
        paths = [os.path.join(folder, f"page_{i + 1:0{width}d}.png") for i in range(len(items))]
        if any(os.path.exists(p) for p in paths) and not messagebox.askyesno(
                "Файлы уже есть", "В папке есть файлы page_XX.png. Заменить их?", parent=self.root):
            return
        scale = self._scale()

        def work(progress):
            for i, (st, img) in enumerate(items):
                progress(f"Страница {i + 1} из {len(items)}…", i / len(items))
                self.engine.render_zine_page(img, st, scale=scale)[0].save(paths[i], dpi=(300, 300))
            return len(items)

        self._run_job("Экспорт PNG", work, lambda n: self.toast.show(f"✓ Сохранено страниц: {n}"))

    def export_mini_zine(self):
        items = self._pages_for_export()
        n = len(items)
        if n != 8:
            note = (f"В проекте {n} стр., а в мини-зине их 8. Недостающие страницы будут копиями последней со случайными манифестами."
                    if n < 8 else f"В проекте {n} стр., а в мини-зине их 8. В лист попадут первые 8.")
            if not messagebox.askyesno("Мини-зин на 8 страниц", note + "\n\nПродолжить?", parent=self.root):
                return
        path = self._ask_save("export", defaultextension=".png", filetypes=[("PNG", "*.png")], initialfile="mini_zine_A4.png")
        if not path:
            return
        items = items[:8]
        while len(items) < 8:
            st, img = copy.deepcopy(items[-1][0]), items[-1][1]
            q = random.choice(manifestos.all_items())
            st.update(txt_top=q["top"], txt_bottom=q["bottom"], seed=random.randint(1, 10 ** 6))
            items.append((st, img))

        def work(progress):
            sw, sh = 3508, 2480  # A4 альбомная, 300 DPI
            cw, rh = sw // 4, sh // 2
            pages = []
            for i, (st, img) in enumerate(items):
                progress(f"Рендеринг страницы {i + 1} из 8…", i / 9.0)
                pages.append(self.engine.render_zine_page(img, st, out_size=(cw, rh))[0])
            sheet = Image.new("RGB", (sw, sh), (255, 255, 255))
            # классическая раскладка: верхний ряд перевёрнут 5-4-3-2, нижний 6-7-8-1
            for col, idx in enumerate((4, 3, 2, 1)):
                sheet.paste(pages[idx].rotate(180), (col * cw, 0))
            for col, idx in enumerate((5, 6, 7, 0)):
                sheet.paste(pages[idx], (col * cw, rh))
            draw = ImageDraw.Draw(sheet)
            for c in range(1, 4):  # линии сгиба
                for y in range(0, sh, 24):
                    draw.line([(c * cw, y), (c * cw, min(sh, y + 14))], fill=(160, 160, 160), width=2)
            for x in range(0, sw, 24):
                draw.line([(x, rh), (min(sw, x + 14), rh)], fill=(160, 160, 160), width=2)
            draw.line([(cw, rh), (cw * 3, rh)], fill=(220, 20, 20), width=5)  # разрез
            progress("Сохранение…", 0.95)
            sheet.save(path, dpi=(300, 300))

        self._run_job("Мини-зин A4", work, lambda _r: self.toast.show("✓ Мини-зин сохранён: сложите лист, разрежьте по красной линии", duration=5000))

    # ------------------------------------------------------------------ пресеты стиля
    def _refresh_presets(self):
        self._presets = presets.all_presets()
        self.preset_combo["values"] = list(self._presets)
        m = self._style_menu
        m.delete(0, "end")
        user = presets.load_user()
        for name in presets.BUILTIN:
            m.add_command(label=name, command=lambda n=name: self.apply_preset(n))
        if user:
            m.add_separator()
            for name in user:
                m.add_command(label=name, command=lambda n=name: self.apply_preset(n))
        m.add_separator()
        m.add_command(label="Сохранить текущий стиль как пресет...", command=self.save_preset)
        m.add_command(label="Применить стиль этой страницы ко всем страницам", command=self.apply_style_to_all_pages)
        if user:
            sub = tk.Menu(m, tearoff=0)
            for name in user:
                sub.add_command(label=name, command=lambda n=name: self.delete_preset(n))
            m.add_cascade(label="Удалить свой пресет", menu=sub)

    def _on_preset_selected(self, _event=None):
        self.apply_preset(self.preset_var.get())
        self.preset_combo.selection_clear()

    def apply_preset(self, name):
        style = self._presets.get(name)
        if not style:
            return
        state = self._snapshot_state()
        state.update(copy.deepcopy(style))
        self._apply_state(state)
        self._mark_dirty(immediate=True)
        self.preset_var.set(name)
        self.toast.show(f"Стиль «{name}» применён")

    def save_preset(self):
        name = simpledialog.askstring("Сохранить стиль", "Название пресета:", parent=self.root)
        name = (name or "").strip()[:40]
        if not name:
            return
        if name in presets.BUILTIN:
            self.toast.show("Это имя занято встроенным пресетом", kind="error")
            return
        try:
            presets.save_user(name, self._snapshot_state())
        except OSError as exc:
            log.exception("не удалось сохранить пресет")
            messagebox.showerror("Ошибка", f"Не удалось сохранить пресет:\n{exc}", parent=self.root)
            return
        self._refresh_presets()
        self.preset_var.set(name)
        self.toast.show(f"✓ Пресет «{name}» сохранён")

    def delete_preset(self, name):
        if messagebox.askyesno("Удалить пресет", f"Удалить пресет «{name}»?", parent=self.root):
            presets.delete_user(name)
            self._refresh_presets()
            if self.preset_var.get() == name:
                self.preset_var.set(PRESET_HINT)

    def apply_style_to_all_pages(self):
        if len(self.pages) < 2:
            self.toast.show("В проекте одна страница", kind="info")
            return
        if not messagebox.askyesno("Применить ко всем", "Перенести оформление этой страницы на все остальные?\nФото и тексты не изменятся.", parent=self.root):
            return
        style = presets.extract_style(self._snapshot_state())
        self.pages[self.cur_page_idx] = self._snapshot_state()
        for i, st in enumerate(self.pages):
            if i != self.cur_page_idx:
                st.update(copy.deepcopy(style))
                self.page_thumbs[i] = None
        self._build_missing_thumbs()
        self._refresh_page_strip()
        self._mark_dirty(immediate=True)
        self.toast.show("✓ Стиль применён ко всем страницам")

    # ------------------------------------------------------------------ проект .zine
    def _confirm_discard(self):
        """True - можно продолжать (сохранили или отказались сохранять); False - пользователь передумал."""
        if not self.dirty:
            return True
        ans = messagebox.askyesnocancel(config.APP_NAME, "Сохранить изменения в проекте?", parent=self.root)
        if ans is None:
            return False
        return self.save_project() if ans else True

    def save_project(self):
        path = self.project_path or self._ask_save(
            "project", defaultextension=".zine", filetypes=[("Zine Project", "*.zine")], initialfile="project.zine")
        return self._write_project_to(path) if path else False

    def save_project_as(self):
        initial = os.path.basename(self.project_path) if self.project_path else "project.zine"
        path = self._ask_save("project", defaultextension=".zine", filetypes=[("Zine Project", "*.zine")], initialfile=initial)
        return self._write_project_to(path) if path else False

    def _write_project_to(self, path):
        doc = self._doc_snapshot()
        self.pages[self.cur_page_idx] = doc["pages"][doc["cur"]]
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            project_io.write_project(path, doc["pages"], self.images, doc["cur"])
        except Exception as exc:
            log.exception("не удалось сохранить проект %s", path)
            messagebox.showerror("Ошибка", f"Не удалось сохранить проект:\n{exc}", parent=self.root)
            return False
        finally:
            self.root.config(cursor="")
        self.project_path = path
        self.dirty = False
        self._autosave_rev = self._rev
        self._update_title()
        self._clear_autosave()
        self.toast.show("✓ Проект сохранён")
        return True

    def open_project(self):
        path = filedialog.askopenfilename(parent=self.root, initialdir=self._dir("project"), filetypes=[("Zine Project", "*.zine")])
        if not path:
            return
        self._remember_dir("project", path)
        if self._confirm_discard():
            self._load_project_path(path)

    def _load_project_path(self, path, recovered=False):
        try:
            pages, images, cur = project_io.read_project(path)
        except Exception as exc:
            log.exception("не удалось открыть проект %s", path)
            messagebox.showerror("Ошибка", f"Не удалось прочесть .zine файл:\n{exc}", parent=self.root)
            return False
        self.images = images
        nums = [int(k[3:]) for k in images if k.startswith("img") and k[3:].isdigit()]
        self._img_counter = max(nums, default=0)
        self.pages = pages
        self.page_thumbs = [None] * len(pages)
        self.cur_page_idx = cur
        self.project_path = None if recovered else path
        self._apply_state(self.pages[cur])
        self._build_missing_thumbs()
        self._refresh_page_strip()
        self._reset_history()
        self.dirty = recovered
        self._rev += 1
        self._autosave_rev = -1 if recovered else self._rev
        self._update_title()
        self.toast.show(f"✓ Проект {'восстановлен' if recovered else 'загружен'} ({len(pages)} стр.)")
        return True

    def new_project(self):
        if not self._confirm_discard():
            return
        self.images, self.cur_img_key, self._img_counter = {}, None, 0
        quote = manifestos.builtin()[0]
        first = dict(config.DEFAULT_STATE, txt_top=quote["top"], txt_bottom=quote["bottom"])
        self.pages, self.page_thumbs, self.cur_page_idx = [first], [None], 0
        self._apply_state(first)
        self._refresh_page_strip()
        self._reset_history()
        self.project_path, self.dirty = None, False
        self._rev += 1
        self._autosave_rev = self._rev
        self._update_title()
        self._clear_autosave()

    def _setup_dnd(self):
        """Перетаскивание фото и .zine в окно (нужен пакет tkinterdnd2; без него просто не работает)."""
        try:
            from tkinterdnd2 import DND_FILES
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            log.info("перетаскивание файлов недоступно")

    def _on_drop(self, event):
        paths = [p for p in self.root.tk.splitlist(event.data) if os.path.isfile(p)]
        zines = [p for p in paths if p.lower().endswith(".zine")]
        if zines:
            if self._confirm_discard():
                self._load_project_path(zines[0])
        elif paths:
            self._load_image_paths(paths)
        return event.action

    def _open_from_cli(self, path):
        """Файл, переданный программе при запуске (двойной клик или перетаскивание на exe)."""
        if path.lower().endswith(".zine"):
            self._load_project_path(path)
        else:
            self._load_image_paths([path])

    # ------------------------------------------------------------------ отмена / вернуть
    def _mark_dirty(self, immediate=False):
        """immediate=True для разовых действий (поворот фото, страница, пресет): это отдельный шаг «Отменить».
        Правки ползунков и текста склеиваются в один шаг через 0,6 с."""
        self._rev += 1
        if not self.dirty:
            self.dirty = True
            self._update_title()
        if self._hist_after:
            self.root.after_cancel(self._hist_after)
            self._hist_after = None
        if immediate:
            self._commit_history()
        else:
            self._hist_after = self.root.after(600, self._commit_history)

    def _doc_snapshot(self):
        pages = copy.deepcopy(self.pages)
        pages[self.cur_page_idx] = self._snapshot_state()
        return {"pages": pages, "cur": self.cur_page_idx}

    def _reset_history(self):
        if self._hist_after:
            self.root.after_cancel(self._hist_after)
            self._hist_after = None
        self.hist, self.hist_idx = [self._doc_snapshot()], 0

    def _commit_history(self):
        self._hist_after = None
        doc = self._doc_snapshot()
        if self.hist and doc["pages"] == self.hist[self.hist_idx]["pages"]:
            return
        del self.hist[self.hist_idx + 1:]
        self.hist.append(doc)
        if len(self.hist) > HISTORY_LIMIT:
            del self.hist[0]
        self.hist_idx = len(self.hist) - 1

    def undo(self):
        self._step_history(-1)

    def redo(self):
        self._step_history(1)

    def _step_history(self, delta):
        if self._hist_after:
            self.root.after_cancel(self._hist_after)
            self._commit_history()
        j = self.hist_idx + delta
        if not 0 <= j < len(self.hist):
            self.toast.show("Нечего отменять" if delta < 0 else "Нечего возвращать", kind="info", duration=1200)
            return
        self.hist_idx = j
        doc = copy.deepcopy(self.hist[j])
        self.pages = doc["pages"]
        self.page_thumbs = [None] * len(self.pages)
        self.cur_page_idx = min(doc["cur"], len(self.pages) - 1)
        self._apply_state(self.pages[self.cur_page_idx])
        self._build_missing_thumbs()
        self._refresh_page_strip()
        self._rev += 1
        if not self.dirty:
            self.dirty = True
            self._update_title()
        self.toast.show("↶ Отменено" if delta < 0 else "↷ Возвращено", kind="info", duration=1200)

    # ------------------------------------------------------------------ автосохранение, настройки, выход
    def _autosave_tick(self):
        try:
            if self.dirty and self._autosave_rev != self._rev and not self._autosave_busy:
                doc = self._doc_snapshot()
                images, rev = dict(self.images), self._rev
                self._autosave_busy = True

                def work():
                    try:
                        project_io.write_project(appdata.autosave_path(), doc["pages"], images, doc["cur"])
                        self._autosave_rev = rev
                    except Exception:
                        log.exception("автосохранение не удалось")
                    finally:
                        self._autosave_busy = False

                self._autosave_thread = threading.Thread(target=work, daemon=True)
                self._autosave_thread.start()
        except Exception:
            log.exception("сбой автосохранения")
        self.root.after(AUTOSAVE_MS, self._autosave_tick)

    @staticmethod
    def _clear_autosave():
        try:
            os.remove(appdata.autosave_path())
        except OSError:
            pass

    def _offer_recovery(self):
        path = appdata.autosave_path()
        if not os.path.exists(path):
            return
        when = time.strftime("%d.%m.%Y %H:%M", time.localtime(os.path.getmtime(path)))
        if messagebox.askyesno(
            config.APP_NAME,
            f"Найдена несохранённая работа от {when}: программа закрылась некорректно.\n\nВосстановить?",
            parent=self.root,
        ):
            if not self._load_project_path(path, recovered=True):
                self._clear_autosave()
        else:
            self._clear_autosave()

    def on_close(self):
        if self._busy and not messagebox.askyesno(config.APP_NAME, "Сейчас идёт экспорт. Выйти и прервать его?", parent=self.root):
            return
        if not self._confirm_discard():
            return
        if self._autosave_thread:
            self._autosave_thread.join(timeout=5)
        self._clear_autosave()
        self.settings.save()
        self.root.destroy()

    def _update_title(self):
        name = os.path.basename(self.project_path) if self.project_path else "Без названия"
        self.root.title(f"{'*' if self.dirty else ''}{name} — {config.APP_NAME}")

    def _dir(self, kind):
        d = self.settings.get(f"dir_{kind}")
        return d if d and os.path.isdir(d) else os.path.expanduser("~")

    def _remember_dir(self, kind, path):
        if path:
            self.settings.set(f"dir_{kind}", os.path.dirname(os.path.abspath(path)))

    def _ask_save(self, kind, **kwargs):
        path = filedialog.asksaveasfilename(parent=self.root, initialdir=self._dir(kind), **kwargs)
        self._remember_dir(kind, path)
        return path

    def _on_tk_exception(self, exc, val, tb):
        log.error("необработанная ошибка интерфейса", exc_info=(exc, val, tb))
        try:
            self.toast.show(f"Внутренняя ошибка: {val}. Подробности в журнале: {appdata.log_path()}", kind="error", duration=7000)
        except Exception:
            pass

    def _build_missing_thumbs(self):
        for i, st in enumerate(self.pages):
            if self.page_thumbs[i] is None and i != self.cur_page_idx:
                try:
                    img, _ = self.engine.render_zine_page(self.images.get(st.get("img")), st, scale=0.18)
                    self._set_thumb(i, img)
                except Exception:
                    log.warning("не удалось построить миниатюру", exc_info=True)

    # ------------------------------------------------------------------ справка
    def show_help(self):
        messagebox.showinfo("Горячие клавиши", HELP_TEXT, parent=self.root)

    def show_about(self):
        messagebox.showinfo(
            config.APP_NAME,
            f"{config.APP_NAME} {config.APP_VERSION}\n\nГенератор ксерокс-зинов: полутон, рваные края,\n"
            "потеря качества копий и ризографская палитра.\n"
            "Страницы собираются в PDF, мини-зин A4 и 1-bit трафарет.",
            parent=self.root,
        )

    def show_licenses(self):
        try:
            with open(config.resource_path("THIRD_PARTY_NOTICES.md"), encoding="utf-8") as f:
                text = f.read()
        except OSError:
            text = "Файл THIRD_PARTY_NOTICES.md не найден."
        win = tk.Toplevel(self.root)
        win.title("Лицензии третьих сторон")
        win.configure(bg=PANEL)
        win.geometry(f"{self.px(760)}x{self.px(560)}")
        win.transient(self.root)
        box = tk.Text(win, bg=FIELD, fg=FG, font=("Consolas", 9), wrap="word", relief="flat", padx=10, pady=8)
        scroll = ttk.Scrollbar(win, orient="vertical", style="Dark.Vertical.TScrollbar", command=box.yview)
        box.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        box.pack(fill=tk.BOTH, expand=True)
        box.insert("1.0", text)
        box.config(state="disabled")

    def show_log(self):
        path = appdata.log_path()
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa: S606
            else:
                messagebox.showinfo("Журнал ошибок", path, parent=self.root)
        except OSError:
            messagebox.showinfo("Журнал ошибок", f"Файл журнала:\n{path}", parent=self.root)


def run_selftest(out_path=None):
    """Проверка сборки без окна: `XeroxZineStudio.exe --selftest result.json`. Код 0 = всё в порядке."""
    import json
    import tempfile

    appdata.setup_logging()
    result = {"ok": False, "version": config.APP_VERSION, "checks": {}}
    try:
        engine = ZineGraphicEngine()
        img, bits = engine.render_zine_page(None, {"txt_top": "TEST", "txt_bottom": "ТЕСТ"}, scale=0.5)
        colors = len(np.unique(np.asarray(img).reshape(-1, 3), axis=0))
        result["checks"]["render_size"] = img.size == (500, 750)
        result["checks"]["render_palette_colors<=3"] = colors <= 3
        result["checks"]["stencil_is_1bit"] = bits.mode == "1"
        for layout in config.LAYOUTS.values():
            for dither in config.DITHERS.values():
                engine.render_zine_page(None, {"layout": layout, "dither": dither}, scale=0.25)
        result["checks"]["all_layouts_and_dithers"] = True
        result["checks"]["icon_png_present"] = os.path.exists(config.resource_path("icon.png"))
        result["checks"]["icon_ico_present"] = os.path.exists(config.resource_path("icon.ico"))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.zine")
            pages = [dict(config.DEFAULT_STATE, img="img1")]
            project_io.write_project(path, pages, {"img1": np.zeros((24, 24, 3), np.uint8)}, 0)
            got_pages, got_images, _cur = project_io.read_project(path)
            result["checks"]["project_roundtrip"] = len(got_pages) == 1 and "img1" in got_images
        try:
            import tkinterdnd2
            dnd = os.path.isdir(os.path.join(os.path.dirname(tkinterdnd2.__file__), "tkdnd"))
        except Exception:
            dnd = False
        result["checks"]["face_detector"] = engine.face_cascade is not None
        result["checks"]["manifestos_loaded"] = len(manifestos.builtin()) >= 30
        result["checks"]["notices_bundled"] = os.path.exists(config.resource_path("THIRD_PARTY_NOTICES.md"))
        result["info"] = {"drag_and_drop": dnd}  # не критично: без него не работает только перетаскивание файлов
        result["ok"] = all(result["checks"].values())
    except Exception as exc:
        log.exception("selftest")
        result["error"] = f"{type(exc).__name__}: {exc}"
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    return 0 if result["ok"] else 1


def main():
    if "--selftest" in sys.argv:
        i = sys.argv.index("--selftest")
        sys.exit(run_selftest(sys.argv[i + 1] if len(sys.argv) > i + 1 else None))

    appdata.setup_logging()
    log.info("запуск %s %s", config.APP_NAME, config.APP_VERSION)
    sys.excepthook = lambda et, ev, tb: log.error("необработанное исключение", exc_info=(et, ev, tb))
    threading.excepthook = lambda a: log.error("исключение в потоке %s", a.thread, exc_info=(a.exc_type, a.exc_value, a.exc_traceback))

    enable_windows_integration()
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except Exception:
        root = tk.Tk()
    open_path = next((a for a in sys.argv[1:] if os.path.isfile(a)), None)
    XeroxZineStudioApp(root, open_path=open_path)
    root.mainloop()


if __name__ == "__main__":
    main()
