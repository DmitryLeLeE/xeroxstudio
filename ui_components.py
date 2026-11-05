"""
UI Components: тема, бесконечный холст Pan/Zoom, рамка кадрирования, слайдеры,
аккордеоны, Toast и диалог прогресса.
"""

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

# ---------------------------------------------------------------- тема
BG = "#121212"
PANEL = "#181818"
PANEL2 = "#1f1f1f"
FIELD = "#2a2a2a"
LINE = "#333333"
FG = "#e8e8e8"
MUTED = "#8c8c8c"
ACCENT = "#d6ff00"      # кислотный лайм, как на иконке
ACCENT_DIM = "#a3c400"
PINK = "#ff2a85"
DANGER = "#ff5470"
VIEW_BG = "#0b0b0b"

UI_SCALE = 1.0  # main.py подставляет масштаб Windows (1.0, 1.25, 1.5...)

FONT = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_SMALL = ("Segoe UI", 8)

_BUTTON_KINDS = {
    "primary": (ACCENT, "#0a0a0a", "#e6ff4d"),
    "secondary": ("#2b2b2b", FG, "#383838"),
    "ghost": (PANEL, MUTED, "#262626"),
    "danger": ("#2b2b2b", DANGER, "#3a2229"),
    "pink": (PINK, "#0a0a0a", "#ff5ea5"),
}


def setup_ttk_style(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "TCombobox", fieldbackground=FIELD, background=FIELD, foreground=FG, arrowcolor=ACCENT,
        bordercolor=LINE, lightcolor=FIELD, darkcolor=FIELD, selectbackground=FIELD,
        selectforeground=FG, padding=3,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", FIELD), ("disabled", PANEL)],
        foreground=[("disabled", MUTED)],
        selectbackground=[("readonly", FIELD)],
        selectforeground=[("readonly", FG)],
        arrowcolor=[("disabled", MUTED)],
    )
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#0a0a0a")
    root.option_add("*TCombobox*Listbox.font", FONT)
    style.configure(
        "Dark.Vertical.TScrollbar", troughcolor=PANEL, background="#3a3a3a", bordercolor=PANEL,
        arrowcolor=MUTED, lightcolor="#3a3a3a", darkcolor="#3a3a3a",
    )
    style.map("Dark.Vertical.TScrollbar", background=[("active", "#555555")])
    style.configure(
        "Dark.Horizontal.TScrollbar", troughcolor=PANEL, background="#3a3a3a", bordercolor=PANEL,
        arrowcolor=MUTED, lightcolor="#3a3a3a", darkcolor="#3a3a3a",
    )
    style.map("Dark.Horizontal.TScrollbar", background=[("active", "#555555")])
    style.configure(
        "Lime.Horizontal.TProgressbar", troughcolor=FIELD, background=ACCENT,
        bordercolor=LINE, lightcolor=ACCENT, darkcolor=ACCENT,
    )


def make_button(parent, text, command=None, kind="secondary", **kwargs):
    bg, fg, hover = _BUTTON_KINDS[kind]
    options = dict(
        text=text, command=command, bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
        relief="flat", bd=0, highlightthickness=0, cursor="hand2", padx=10, pady=4,
        font=FONT_BOLD if kind in ("primary", "pink") else FONT,
    )
    options.update(kwargs)
    btn = tk.Button(parent, **options)
    btn.bind("<Enter>", lambda e: btn.config(bg=hover) if str(btn["state"]) == "normal" else None)
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def enable_mousewheel_scroll(widget, canvas_target):
    """Рекурсивно привязывает колесо мыши ко всем вложенным виджетам панели."""
    def _on_wheel(e):
        if getattr(e, "num", 0) == 4 or e.delta > 0:
            canvas_target.yview_scroll(-2, "units")
        else:
            canvas_target.yview_scroll(2, "units")
        return "break"  # не даём Combobox менять значение при прокрутке панели

    widget.bind("<MouseWheel>", _on_wheel)
    widget.bind("<Button-4>", _on_wheel)
    widget.bind("<Button-5>", _on_wheel)
    for child in widget.winfo_children():
        enable_mousewheel_scroll(child, canvas_target)


# ---------------------------------------------------------------- холст предпросмотра
class InteractivePanZoomCanvas(tk.Canvas):
    """Предпросмотр: ЛКМ - двигать лист (или слой под курсором), колесо - зум, Shift+ЛКМ - поставить подпись."""

    MIN_ZOOM, MAX_ZOOM = 0.05, 12.0

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=VIEW_BG, highlightthickness=0, **kwargs)
        self.current_image = None
        self.tk_image = None
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.drag_start = None
        self._placing = False
        self._user_moved = False
        self._overlay = None

        self.on_transform_changed = None
        self.on_text_click_relocate = None
        # свободные слои: попадание курсора, перенос, рамка выбранного (доли листа: cx, cy, w, h)
        self.layer_hit = None
        self.on_layer_press = None
        self.on_layer_move = None
        self.layer_frame = None
        self._layer_drag = None

        self.bind("<ButtonPress-2>", self._start_pan)
        self.bind("<B2-Motion>", self._drag_pan)
        self.bind("<ButtonPress-1>", self._on_left_press)
        self.bind("<B1-Motion>", self._on_left_drag)
        self.bind("<ButtonRelease-1>", self._on_left_release)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", self._on_wheel)
        self.bind("<Button-5>", self._on_wheel)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Configure>", self._on_configure)

    # --- публичный API
    def set_image(self, pil_img, keep_view=True):
        first = self.current_image is None
        resized = first or self.current_image.size != pil_img.size
        self.current_image = pil_img
        if not keep_view or resized or not self._user_moved:
            self.fit_to_view()
        else:
            self.redraw()

    def set_overlay(self, text):
        self._overlay = text
        self.redraw()

    def fit_to_view(self):
        if not self.current_image:
            return
        self._user_moved = False
        cw, ch = max(50, self.winfo_width()), max(50, self.winfo_height())
        scale = min(cw / self.current_image.width, ch / self.current_image.height) * 0.94
        self.zoom_scale = max(self.MIN_ZOOM, min(self.MAX_ZOOM, scale))
        self.pan_x = (cw - self.current_image.width * self.zoom_scale) / 2.0
        self.pan_y = (ch - self.current_image.height * self.zoom_scale) / 2.0
        self.redraw()

    def reset_100_percent(self):
        if not self.current_image:
            return
        self._user_moved = True
        self._set_zoom(1.0, self.winfo_width() / 2.0, self.winfo_height() / 2.0)

    # --- события
    def _on_configure(self, _event):
        if not self._user_moved:
            self.fit_to_view()
        else:
            self.redraw()

    def _frac(self, event):
        rw = self.current_image.width * self.zoom_scale
        rh = self.current_image.height * self.zoom_scale
        return (event.x - self.pan_x) / max(1.0, rw), (event.y - self.pan_y) / max(1.0, rh)

    def _on_motion(self, event):
        cur = "arrow"
        if event.state & 0x0001:
            cur = "crosshair"
        elif self.layer_hit and self.current_image:
            fx, fy = self._frac(event)
            if self.layer_hit(fx, fy) is not None:
                cur = "fleur"
        self.config(cursor=cur)

    def _start_pan(self, event):
        self.drag_start = (event.x, event.y)

    def _drag_pan(self, event):
        if not self.drag_start:
            return
        self._user_moved = True
        self.pan_x += event.x - self.drag_start[0]
        self.pan_y += event.y - self.drag_start[1]
        self.drag_start = (event.x, event.y)
        self.redraw()

    def _place_text(self, event):
        if self.on_text_click_relocate and self.current_image:
            rw = self.current_image.width * self.zoom_scale
            rh = self.current_image.height * self.zoom_scale
            nx = (event.x - self.pan_x) / max(1.0, rw)
            ny = (event.y - self.pan_y) / max(1.0, rh)
            self.on_text_click_relocate(nx, ny)

    def _on_left_press(self, event):
        self.focus_set()
        self._placing = bool(event.state & 0x0001)
        self._layer_drag = None
        if self._placing:
            self._place_text(event)
            return
        if self.layer_hit and self.current_image:
            fx, fy = self._frac(event)
            idx = self.layer_hit(fx, fy)
            if idx is not None:
                cx, cy = self.on_layer_press(idx) if self.on_layer_press else (fx, fy)
                self._layer_drag = (idx, cx - fx, cy - fy)
                return
        self._start_pan(event)

    def _on_left_drag(self, event):
        if self._placing:
            self._place_text(event)
        elif self._layer_drag:
            idx, dx, dy = self._layer_drag
            fx, fy = self._frac(event)
            if self.on_layer_move:
                self.on_layer_move(idx, min(1.0, max(0.0, fx + dx)), min(1.0, max(0.0, fy + dy)))
        else:
            self._drag_pan(event)

    def _on_left_release(self, _event):
        self._placing = False
        self._layer_drag = None

    def _on_wheel(self, event):
        up = getattr(event, "num", 0) == 4 or getattr(event, "delta", 0) > 0
        self._user_moved = True
        self._set_zoom(self.zoom_scale * (1.15 if up else 1 / 1.15), event.x, event.y)

    def _set_zoom(self, new_scale, fx, fy):
        new_scale = max(self.MIN_ZOOM, min(self.MAX_ZOOM, new_scale))
        k = new_scale / self.zoom_scale
        self.pan_x = fx - (fx - self.pan_x) * k
        self.pan_y = fy - (fy - self.pan_y) * k
        self.zoom_scale = new_scale
        self.redraw()

    # --- отрисовка (ресайзится только видимая часть: на зуме 12x картинка не раздувается в память)
    def redraw(self):
        self.delete("all")
        cw, ch = max(1, self.winfo_width()), max(1, self.winfo_height())
        img = self.current_image
        if img is not None:
            z = self.zoom_scale
            x0 = max(0, int(-self.pan_x / z))
            y0 = max(0, int(-self.pan_y / z))
            x1 = min(img.width, int((cw - self.pan_x) / z) + 2)
            y1 = min(img.height, int((ch - self.pan_y) / z) + 2)
            if x1 > x0 and y1 > y0:
                part = img.crop((x0, y0, x1, y1))
                size = (max(1, round((x1 - x0) * z)), max(1, round((y1 - y0) * z)))
                resample = Image.Resampling.NEAREST if z > 2.0 else Image.Resampling.BILINEAR
                self.tk_image = ImageTk.PhotoImage(part.resize(size, resample=resample))
                self.create_image(round(self.pan_x + x0 * z), round(self.pan_y + y0 * z), anchor="nw", image=self.tk_image)
            self.create_rectangle(
                self.pan_x - 1, self.pan_y - 1, self.pan_x + img.width * z, self.pan_y + img.height * z,
                outline="#2a2a2a",
            )
        if self.layer_frame and img is not None:
            fcx, fcy, fw, fh = self.layer_frame
            z = self.zoom_scale
            x0 = self.pan_x + (fcx - fw / 2) * img.width * z
            y0 = self.pan_y + (fcy - fh / 2) * img.height * z
            x1 = self.pan_x + (fcx + fw / 2) * img.width * z
            y1 = self.pan_y + (fcy + fh / 2) * img.height * z
            self.create_rectangle(x0, y0, x1, y1, outline=ACCENT, width=2, dash=(6, 4))
        if self._overlay:
            k = UI_SCALE
            self.create_rectangle(cw / 2 - 190 * k, ch - 92 * k, cw / 2 + 190 * k, ch - 36 * k, fill="#000000", outline=ACCENT)
            self.create_text(cw / 2, ch - 64 * k, text=self._overlay, fill=ACCENT, font=("Segoe UI", 10, "bold"), justify="center")
        if self.on_transform_changed:
            self.on_transform_changed(self.zoom_scale)


# ---------------------------------------------------------------- рамка кадрирования
class CropCanvas(tk.Canvas):
    """Превью исходного фото. Потяните мышью - выделите кадр, двойной клик - сброс."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#0a0a0a", highlightthickness=1, highlightbackground=LINE, cursor="crosshair", **kwargs)
        self.image = None
        self.crop = [0.0, 0.0, 1.0, 1.0]
        self.on_crop_changed = None
        self._tk = None
        self._box = (0, 0, 1, 1)  # x, y, w, h изображения на холсте
        self._drag = None
        self._live = None
        self._placeholder = "Фото не загружено"

        self.bind("<Configure>", lambda e: self._render())
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Double-Button-1>", self._reset)

    def set_image(self, pil_img):
        self.image = pil_img
        self._render()

    def set_crop(self, crop):
        self.crop = [float(v) for v in crop]
        self._render()

    def _render(self):
        self.delete("all")
        cw, ch = max(1, self.winfo_width()), max(1, self.winfo_height())
        if self.image is None:
            self.create_text(cw / 2, ch / 2, text=self._placeholder, fill=MUTED, font=FONT, justify="center")
            return
        iw, ih = self.image.size
        k = min((cw - 12) / iw, (ch - 12) / ih)
        w, h = max(1, int(iw * k)), max(1, int(ih * k))
        x, y = (cw - w) // 2, (ch - h) // 2
        self._box = (x, y, w, h)
        self._tk = ImageTk.PhotoImage(self.image.resize((w, h), Image.Resampling.BILINEAR))
        self.create_image(x, y, anchor="nw", image=self._tk)
        self._draw_crop()

    def _draw_crop(self):
        x, y, w, h = self._box
        cx1, cy1, cx2, cy2 = self.crop
        px1, py1, px2, py2 = x + cx1 * w, y + cy1 * h, x + cx2 * w, y + cy2 * h
        if self.crop != [0.0, 0.0, 1.0, 1.0]:
            for rect in ((x, y, x + w, py1), (x, py2, x + w, y + h), (x, py1, px1, py2), (px2, py1, x + w, py2)):
                self.create_rectangle(*rect, fill="#000000", stipple="gray50", outline="")
        self.create_rectangle(px1, py1, px2, py2, outline=ACCENT, width=2)

    def _norm(self, event):
        x, y, w, h = self._box
        return (min(max((event.x - x) / w, 0.0), 1.0), min(max((event.y - y) / h, 0.0), 1.0))

    def _press(self, event):
        if self.image is not None:
            self._drag = self._norm(event)

    def _motion(self, event):
        if self.image is None or self._drag is None:
            return
        nx, ny = self._norm(event)
        x, y, w, h = self._box
        if self._live:
            self.delete(self._live)
        self._live = self.create_rectangle(
            x + self._drag[0] * w, y + self._drag[1] * h, x + nx * w, y + ny * h, outline=PINK, width=2, dash=(4, 3)
        )

    def _release(self, event):
        if self.image is None or self._drag is None:
            return
        nx, ny = self._norm(event)
        sx, sy = self._drag
        self._drag = None
        self._live = None
        if abs(nx - sx) < 0.04 or abs(ny - sy) < 0.04:
            self._render()
            return
        self.crop = [min(sx, nx), min(sy, ny), max(sx, nx), max(sy, ny)]
        self._render()
        if self.on_crop_changed:
            self.on_crop_changed(list(self.crop))

    def _reset(self, _event=None):
        if self.image is None:
            return
        self._drag = None
        self.crop = [0.0, 0.0, 1.0, 1.0]
        self._render()
        if self.on_crop_changed:
            self.on_crop_changed(list(self.crop))


# ---------------------------------------------------------------- мелкие виджеты
class LabeledSlider(tk.Frame):
    """Подпись + ползунок + значение. Двойной клик по ползунку возвращает значение по умолчанию."""

    def __init__(self, parent, text, var, from_, to, res=1, default=None, **kwargs):
        super().__init__(parent, bg=PANEL2, **kwargs)
        self.var, self.res = var, res
        self.default = default if default is not None else var.get()
        tk.Label(self, text=text, bg=PANEL2, fg=MUTED, font=FONT_SMALL, width=24, anchor="w").pack(side=tk.LEFT)
        self.value_lbl = tk.Label(self, bg=PANEL2, fg=FG, font=FONT_SMALL, width=5, anchor="e")
        self.value_lbl.pack(side=tk.RIGHT)
        self.scale = tk.Scale(
            self, from_=from_, to=to, resolution=res, orient=tk.HORIZONTAL, variable=var, showvalue=False,
            bg=ACCENT, activebackground="#ffffff", troughcolor="#333333", highlightthickness=0, bd=0,
            sliderrelief="flat", sliderlength=int(14 * UI_SCALE), width=int(10 * UI_SCALE), cursor="hand2",
        )
        self.scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), pady=3)
        self.scale.bind("<Double-Button-1>", self._reset)
        var.trace_add("write", self._update_label)
        self._update_label()

    def _reset(self, _event=None):
        self.var.set(self.default)
        return "break"

    def _update_label(self, *_):
        try:
            v = float(self.var.get())
        except (tk.TclError, ValueError):
            return
        self.value_lbl.config(text=f"{v:.0f}" if self.res >= 1 else f"{v:.1f}")


class CollapsibleSection(tk.Frame):
    def __init__(self, parent, title="", is_open=True, **kwargs):
        super().__init__(parent, bg=PANEL, **kwargs)
        self.is_open = is_open
        self.single = False
        self.title = title
        self.header = tk.Label(
            self, text="", bg="#242424", fg=ACCENT, font=FONT_BOLD, anchor="w", padx=8, pady=5, cursor="hand2"
        )
        self.header.pack(fill=tk.X)
        self.header.bind("<Button-1>", lambda e: self.toggle())
        self.header.bind("<Enter>", lambda e: self.header.config(bg="#2e2e2e"))
        self.header.bind("<Leave>", lambda e: self.header.config(bg="#242424"))
        self.content = tk.Frame(self, bg=PANEL2, padx=8, pady=6)
        self._refresh()

    def _refresh(self):
        self.header.config(text=f"{'▼' if self.is_open else '▶'}  {self.title}")
        if self.is_open:
            self.content.pack(fill=tk.X)
        else:
            self.content.pack_forget()

    def toggle(self):
        self.is_open = not self.is_open
        self._refresh()

    def set_single(self, single):
        """Режим «одна секция в панели»: заголовок прячется, содержимое всегда раскрыто."""
        self.single = single
        if single:
            self.header.pack_forget()
            self.content.pack(fill=tk.X)
        else:
            self.content.pack_forget()
            self.header.pack(fill=tk.X)
            self._refresh()


# ---------------------------------------------------------------- лента значков
_RIBBON_ICONS = {  # фигуры в сетке 24x24: те же значки, что в браузерной версии
    "styles": [("poly", [(12, 3), (14, 9), (20, 11), (14, 13), (12, 19), (10, 13), (4, 11), (10, 9)]), ("poly", [(19, 16), (20, 19), (23, 20), (20, 21), (19, 24), (18, 21), (15, 20), (18, 19)])],
    "photo": [("rect", 3, 5, 21, 19), ("oval", 7, 9, 11, 13), ("line", [(21, 17), (16, 12), (7, 19)])],
    "s0": [("rect", 3, 3, 11, 11), ("rect", 13, 3, 21, 11), ("rect", 3, 13, 11, 21), ("rect", 13, 13, 21, 21)],
    "s1": [("line", [(6, 2), (6, 16), (8, 18), (22, 18)]), ("line", [(2, 6), (16, 6), (18, 8), (18, 22)])],
    "s2": [("oval", 3.4, 3.4, 8.6, 8.6), ("oval", 13.4, 4.4, 16.6, 7.6), ("oval", 4.4, 13.4, 7.6, 16.6), ("oval", 12.4, 12.4, 17.6, 17.6), ("oval", 19, 19, 21, 21)],
    "s3": [("line", [(12, 3), (15, 7), (18, 12), (18, 15), (16, 19), (12, 20), (8, 19), (6, 15), (6, 12), (9, 7), (12, 3)])],
    "s4": [("line", [(5, 3), (15, 3), (19, 7), (19, 21), (5, 21), (5, 3)]), ("line", [(8, 14), (10, 16), (13, 12), (16, 15)])],
    "s5": [("line", [(12, 3), (21, 8), (12, 13), (3, 8), (12, 3)]), ("line", [(3, 13), (12, 18), (21, 13)])],
    "s6": [("text", 12, 12, "Aa")],
    "all": [("line", [(4, 6), (20, 6)]), ("line", [(4, 12), (20, 12)]), ("line", [(4, 18), (20, 18)])],
}


def draw_ribbon_icon(cv, name, color, k):
    cv.delete("all")
    for sh in _RIBBON_ICONS.get(name, []):
        if sh[0] == "poly":
            cv.create_polygon([c * k for xy in sh[1] for c in xy], fill=color, outline=color)
        elif sh[0] == "line":
            cv.create_line([c * k for xy in sh[1] for c in xy], fill=color, width=max(2, round(1.8 * k)), capstyle="round", joinstyle="round")
        elif sh[0] == "rect":
            cv.create_rectangle(sh[1] * k, sh[2] * k, sh[3] * k, sh[4] * k, outline=color, width=max(2, round(1.8 * k)))
        elif sh[0] == "oval":
            cv.create_oval(sh[1] * k, sh[2] * k, sh[3] * k, sh[4] * k, outline=color, fill=color if sh[3] - sh[1] < 7 else "", width=max(2, round(1.8 * k)))
        elif sh[0] == "text":
            cv.create_text(sh[1] * k, sh[2] * k, text=sh[3], fill=color, font=("Segoe UI", max(9, round(11 * k)), "bold"))


class RibbonTile(tk.Frame):
    """Плитка ленты: значок и подпись. Активная заливается акцентом."""
    def __init__(self, parent, icon, label, command, tip="", scale=1.0, accent=None, **kw):
        super().__init__(parent, bg="#1f1f1f", highlightthickness=2, highlightbackground="#555", cursor="hand2", **kw)
        self.icon, self.command, self.active, self.k = icon, command, False, 1.15 * scale
        self.accent = accent or ACCENT
        size = int(24 * self.k)
        self.cv = tk.Canvas(self, width=size, height=size, bg="#1f1f1f", highlightthickness=0, cursor="hand2")
        self.cv.pack(pady=(5, 0))
        self.lbl = tk.Label(self, text=label.upper(), bg="#1f1f1f", fg=FG, font=("Segoe UI", 7, "bold"), cursor="hand2")
        self.lbl.pack(pady=(0, 4))
        for w in (self, self.cv, self.lbl):
            w.bind("<Button-1>", lambda e: self.command())
            w.bind("<Enter>", lambda e: self._paint(hover=True))
            w.bind("<Leave>", lambda e: self._paint())
        self.tip = tip
        self._paint()

    def set_active(self, on):
        self.active = on
        self._paint()

    def _paint(self, hover=False):
        if self.active:
            bg, fg, edge = self.accent, "#0a0a0a", "#0a0a0a"
        else:
            bg, fg, edge = ("#2e2e2e" if hover else "#1f1f1f"), FG, ("#999" if hover else "#555")
        self.config(bg=bg, highlightbackground=edge)
        self.cv.config(bg=bg)
        self.lbl.config(bg=bg, fg=fg)
        draw_ribbon_icon(self.cv, self.icon, fg, self.k)


class ToastNotification:
    def __init__(self, parent):
        self.parent = parent
        self.lbl = None
        self._after_id = None

    def show(self, text, kind="ok", duration=2000):
        bg, fg = {"ok": (ACCENT, "#0a0a0a"), "error": (DANGER, "#0a0a0a"), "info": ("#2b2b2b", FG)}.get(kind, (ACCENT, "#0a0a0a"))
        if self._after_id:
            self.parent.after_cancel(self._after_id)
            self._after_id = None
        if self.lbl:
            self.lbl.destroy()
        self.lbl = tk.Label(self.parent, text=text, bg=bg, fg=fg, font=FONT_BOLD, padx=14, pady=7)
        self.lbl.place(relx=0.5, rely=0.94, anchor="center")
        self._after_id = self.parent.after(duration, self._dismiss)

    def _dismiss(self):
        self._after_id = None
        if self.lbl:
            self.lbl.destroy()
            self.lbl = None


class ProgressDialog(tk.Toplevel):
    """Модальное окно прогресса для долгих экспортов (рендер идёт в фоновом потоке)."""

    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=PANEL, padx=22, pady=18)
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.label = tk.Label(self, text=text, bg=PANEL, fg=FG, font=FONT, width=44, anchor="w")
        self.label.pack(fill=tk.X)
        self.bar = ttk.Progressbar(self, style="Lime.Horizontal.TProgressbar", mode="determinate", maximum=1.0, length=340)
        self.bar.pack(fill=tk.X, pady=(10, 0))
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_reqheight()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def set_progress(self, text, fraction):
        self.label.config(text=text)
        self.bar["value"] = fraction
