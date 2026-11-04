"""
Manifest dialog: окно выбора готовых манифестов с поиском и предпросмотром.
Окно не модальное: можно листать список и сразу видеть результат на странице.
"""

import random
import tkinter as tk
from tkinter import ttk

import manifestos
from ui_components import ACCENT, FG, FIELD, FONT, FONT_BOLD, FONT_SMALL, LINE, MUTED, PANEL, PANEL2, make_button

ALL_CATS = "Все категории"


class ManifestoDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Библиотека манифестов")
        self.configure(bg=PANEL, padx=10, pady=10)
        self.geometry(f"{app.px(880)}x{app.px(580)}")
        self.minsize(app.px(720), app.px(440))
        self.transient(app.root)

        self.items, self.shown = [], []
        self.lang_var = tk.StringVar(value=manifestos.LANG_LABELS["all"])
        self.cat_var = tk.StringVar(value=ALL_CATS)
        self.query_var = tk.StringVar()

        self._build()
        self.reload()
        self.bind("<Escape>", lambda e: self.destroy())
        self.search.focus_set()

    # ------------------------------------------------------------------ интерфейс
    def _build(self):
        bar = tk.Frame(self, bg=PANEL)
        bar.pack(fill=tk.X)
        self.lang_combo = ttk.Combobox(bar, textvariable=self.lang_var, state="readonly", width=10, font=FONT,
                                       values=list(manifestos.LANG_LABELS.values()))
        self.lang_combo.pack(side=tk.LEFT)
        self.cat_combo = ttk.Combobox(bar, textvariable=self.cat_var, state="readonly", width=18, font=FONT)
        self.cat_combo.pack(side=tk.LEFT, padx=6)
        tk.Label(bar, text="Поиск:", bg=PANEL, fg=MUTED, font=FONT_SMALL).pack(side=tk.LEFT, padx=(10, 4))
        self.search = tk.Entry(bar, textvariable=self.query_var, bg=FIELD, fg=FG, insertbackground=ACCENT, relief="flat",
                               font=FONT, highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT)
        self.search.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        self.count_lbl = tk.Label(bar, text="", bg=PANEL, fg=MUTED, font=FONT_SMALL, width=12, anchor="e")
        self.count_lbl.pack(side=tk.RIGHT)

        body = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=PANEL, sashwidth=6, sashrelief="flat", bd=0)
        body.pack(fill=tk.BOTH, expand=True, pady=8)
        left = tk.Frame(body, bg=PANEL)
        body.add(left, width=self.app.px(470), minsize=self.app.px(300))
        self.listbox = tk.Listbox(left, bg=FIELD, fg=FG, selectbackground=ACCENT, selectforeground="#0a0a0a", relief="flat",
                                  highlightthickness=1, highlightbackground=LINE, activestyle="none", font=FONT,
                                  exportselection=False, height=8)
        sb = ttk.Scrollbar(left, orient="vertical", style="Dark.Vertical.TScrollbar", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(fill=tk.BOTH, expand=True)

        right = tk.Frame(body, bg=PANEL2)
        body.add(right, minsize=self.app.px(260))
        self.cat_lbl = tk.Label(right, text="", bg=PANEL2, fg=ACCENT, font=FONT_BOLD, anchor="w", padx=12, pady=8)
        self.cat_lbl.pack(fill=tk.X)
        self.preview = tk.Text(right, bg=PANEL2, fg=FG, relief="flat", wrap="word", padx=14, pady=4, cursor="arrow",
                               font=("Consolas", 12, "bold"), highlightthickness=0, spacing1=2, spacing3=2, height=8)
        self.preview.pack(fill=tk.BOTH, expand=True)
        self.preview.tag_configure("sep", foreground=MUTED, justify="left")
        self.preview.config(state="disabled")

        btns = tk.Frame(self, bg=PANEL)
        btns.pack(side=tk.BOTTOM, fill=tk.X, before=body)  # кнопки всегда видны, даже если окно сжали
        self.btn_apply = make_button(btns, "Применить к странице", self.apply_selected, kind="primary")
        self.btn_apply.pack(side=tk.LEFT)
        make_button(btns, "Раздать по страницам", self.spread).pack(side=tk.LEFT, padx=6)
        make_button(btns, "🎲 Случайный", self.pick_random).pack(side=tk.LEFT)
        self.btn_delete = make_button(btns, "Удалить свой", self.delete_selected, kind="danger")
        self.btn_delete.pack(side=tk.RIGHT)
        make_button(btns, "＋ Сохранить текст страницы", self.save_current).pack(side=tk.RIGHT, padx=6)
        make_button(btns, "✎ Написать свой", self.write_own).pack(side=tk.RIGHT)

        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self._on_filter(reset_cat=True))
        self.cat_combo.bind("<<ComboboxSelected>>", lambda e: self._on_filter())
        self.query_var.trace_add("write", lambda *a: self._on_filter())
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._show_preview())
        self.listbox.bind("<Double-Button-1>", lambda e: self.apply_selected())
        self.listbox.bind("<Return>", lambda e: self.apply_selected())

    # ------------------------------------------------------------------ данные
    def _lang_key(self):
        inverse = {v: k for k, v in manifestos.LANG_LABELS.items()}
        return inverse.get(self.lang_var.get(), "all")

    def reload(self):
        self.items = manifestos.all_items()
        self._on_filter(reset_cat=False)

    def _on_filter(self, reset_cat=False):
        lang = self._lang_key()
        if reset_cat:
            self.cat_var.set(ALL_CATS)
        pool = manifestos.filter_items(self.items, lang)
        cats = manifestos.categories(pool)
        self.cat_combo["values"] = [ALL_CATS] + cats
        if self.cat_var.get() not in cats:
            self.cat_var.set(ALL_CATS)
        cat = "" if self.cat_var.get() == ALL_CATS else self.cat_var.get()
        self.shown = manifestos.filter_items(self.items, lang, cat, self.query_var.get())
        self.listbox.delete(0, "end")
        for item in self.shown:
            self.listbox.insert("end", manifestos.label(item))
        self.count_lbl.config(text=f"найдено: {len(self.shown)}")
        if self.shown:
            self.listbox.selection_set(0)
        self._show_preview()

    def _selected(self):
        sel = self.listbox.curselection()
        return self.shown[sel[0]] if sel else None

    def _show_preview(self):
        item = self._selected()
        self.preview.config(state="normal")
        self.preview.delete("1.0", "end")
        if item:
            self.cat_lbl.config(text=f"{item['cat'] or '—'}  ·  {manifestos.LANG_LABELS[item['lang']]}")
            self.preview.insert("end", item["top"] + "\n\n")
            self.preview.insert("end", "— — —\n\n", "sep")
            self.preview.insert("end", item["bottom"])
        else:
            self.cat_lbl.config(text="Ничего не найдено")
        self.preview.config(state="disabled")
        self.btn_apply.config(state="normal" if item else "disabled")
        self.btn_delete.config(state="normal" if item and item["lang"] == "user" else "disabled")

    # ------------------------------------------------------------------ действия
    def apply_selected(self):
        item = self._selected()
        if item:
            self.app.apply_manifesto(item)

    def spread(self):
        if not self.shown:
            return
        start = self.listbox.curselection()[0] if self.listbox.curselection() else 0
        self.app.spread_manifestos(self.shown[start:] + self.shown[:start])

    def pick_random(self):
        if not self.shown:
            return
        i = random.randrange(len(self.shown))
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(i)
        self.listbox.see(i)
        self._show_preview()
        self.apply_selected()

    def save_current(self):
        if self.app.save_current_manifesto():
            self.reload()

    def delete_selected(self):
        item = self._selected()
        if item and item["lang"] == "user":
            manifestos.delete_user(item["top"], item["bottom"])
            self.reload()

    def write_own(self):
        """Маленькое окно: две строки текста -> «Мои»."""
        win = tk.Toplevel(self)
        win.title("Свой манифест")
        win.configure(bg=PANEL, padx=14, pady=12)
        win.transient(self)
        win.resizable(False, False)
        boxes = []
        for caption in ("Верхний текст (Enter: новая строка)", "Нижний текст"):
            tk.Label(win, text=caption, bg=PANEL, fg=MUTED, font=FONT_SMALL, anchor="w").pack(fill=tk.X, pady=(6, 2))
            t = tk.Text(win, width=44, height=3, bg=FIELD, fg=FG, insertbackground=ACCENT, relief="flat", wrap="word",
                        font=("Consolas", 12, "bold"), highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT)
            t.pack(fill=tk.X)
            boxes.append(t)
        msg = tk.Label(win, text="", bg=PANEL, fg="#ff6b6b", font=FONT_SMALL, anchor="w")
        msg.pack(fill=tk.X, pady=(6, 0))

        def save():
            top, bottom = (b.get("1.0", "end").strip().upper() for b in boxes)
            if not top or not bottom:
                msg.config(text="Заполните обе строки")
                return
            if not manifestos.save_user(top, bottom):
                msg.config(text="Такой манифест уже есть среди ваших")
                return
            win.destroy()
            self.lang_var.set(manifestos.LANG_LABELS["user"])
            self.cat_var.set(ALL_CATS)
            self.query_var.set("")
            self.reload()
            for i, item in enumerate(self.shown):
                if item["top"] == top and item["bottom"] == bottom:
                    self.listbox.selection_clear(0, "end")
                    self.listbox.selection_set(i)
                    self.listbox.see(i)
                    self._show_preview()
                    break

        row = tk.Frame(win, bg=PANEL)
        row.pack(fill=tk.X, pady=(8, 0))
        make_button(row, "★ Сохранить в «Мои»", save, kind="primary").pack(side=tk.LEFT)
        make_button(row, "Отмена", win.destroy).pack(side=tk.LEFT, padx=6)
        win.bind("<Escape>", lambda e: win.destroy())
        boxes[0].focus_set()
        win.grab_set()
