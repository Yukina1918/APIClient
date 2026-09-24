# ai_chat/settings_page.py
"""设置页：主题 / 语言 / 字号 / 数据 / 帮助。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from .config import data_dir, open_data_dir, reset_config, save_config
from .i18n import LANGUAGES, get_language, set_language, tr
from .keys import save_keys
from .widgets import (Divider, FlatButton, FlatCombo, apply_theme_to_tree)


class SettingsPage(tk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, bg=app.theme["bg"])
        self.app = app
        self.theme = app.theme
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        canvas = tk.Canvas(self, bg=self.theme["bg"],
                           highlightthickness=0, bd=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._canvas = canvas

        sb = tk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview,
                          bd=0, width=10, relief=tk.FLAT,
                          troughcolor=self.theme["bg"],
                          bg=self.theme["scrollbar"])
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=sb.set)
        self._scrollbar = sb

        self.inner = tk.Frame(canvas, bg=self.theme["bg"])
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        pad = tk.Frame(self.inner, bg=self.theme["bg"])
        pad.pack(fill=tk.BOTH, expand=True, padx=32, pady=20)
        self._pad = pad

        # 标题
        title = tk.Label(pad, text=tr("set.title"), bg=self.theme["bg"],
                         fg=self.theme["fg"], font=("", 16, "bold"),
                         anchor="w")
        title.pack(fill=tk.X, pady=(0, 4))

        Divider(pad, self.theme).pack(fill=tk.X, pady=(0, 18))

        # ---------- 外观 ----------
        self._section(pad, "set.appearance")
        self._row_theme(pad)
        self._row_language(pad)
        self._row_font(pad)

        # ---------- 数据 ----------
        self._section(pad, "set.data")
        self._row_open_folder(pad)
        self._row_reset_config(pad)

        # ---------- 帮助 ----------
        self._section(pad, "set.help")
        self._row_open_tutorial(pad)

        Divider(pad, self.theme).pack(fill=tk.X, pady=(20, 12))

        info = tk.Label(pad,
                        text=f"AI Chat v{self.app.version}\n"
                             f"Data: {data_dir()}",
                        bg=self.theme["bg"], fg=self.theme["hint_color"],
                        font=("", 9), anchor="w", justify=tk.LEFT)
        info._theme_role = "hint"
        info.pack(fill=tk.X, pady=(0, 8))

    # ------------------------------------------------------------------

    def _section(self, parent, key: str) -> None:
        lbl = tk.Label(parent, text=tr(key), bg=self.theme["bg"],
                       fg=self.theme["accent"], font=("", 11, "bold"),
                       anchor="w")
        lbl._theme_role = "section"
        lbl.pack(fill=tk.X, pady=(12, 4))
        Divider(parent, self.theme).pack(fill=tk.X, pady=(0, 10))

    def _row_frame(self, parent) -> tk.Frame:
        row = tk.Frame(parent, bg=self.theme["bg"])
        row.pack(fill=tk.X, pady=6)
        return row

    # ------------------------------------------------------------------

    def _row_theme(self, parent) -> None:
        row = self._row_frame(parent)
        tk.Label(row, text=tr("set.theme"), bg=self.theme["bg"],
                 fg=self.theme["fg"], width=18, anchor="w").pack(side=tk.LEFT)

        self.v_theme = tk.StringVar()
        self.cb_theme = FlatCombo(
            row, self.theme,
            values=[tr("set.theme.light"), tr("set.theme.dark")],
            variable=self.v_theme, command=self._on_theme, width=14)
        self.cb_theme.pack(side=tk.LEFT)

        self.v_theme.set(tr("set.theme.light")
                         if self.app.cfg.get("theme", "light") == "light"
                         else tr("set.theme.dark"))

    def _row_language(self, parent) -> None:
        row = self._row_frame(parent)
        tk.Label(row, text=tr("set.language"), bg=self.theme["bg"],
                 fg=self.theme["fg"], width=18, anchor="w").pack(side=tk.LEFT)

        values = list(LANGUAGES.values())
        self.v_lang = tk.StringVar(
            value=LANGUAGES.get(get_language(), "简体中文"))
        self.cb_lang = FlatCombo(row, self.theme, values=values,
                                 variable=self.v_lang,
                                 command=self._on_language, width=16)
        self.cb_lang.pack(side=tk.LEFT)

    def _row_font(self, parent) -> None:
        row = self._row_frame(parent)
        tk.Label(row, text=tr("set.font_size"), bg=self.theme["bg"],
                 fg=self.theme["fg"], width=18, anchor="w").pack(side=tk.LEFT)

        self.v_font = tk.StringVar(value=str(self.app.cfg.get("font_size", 11)))
        e = tk.Entry(row, textvariable=self.v_font, width=6, bd=0,
                     bg=self.theme["input_bg"], fg=self.theme["input_fg"],
                     insertbackground=self.theme["input_fg"],
                     highlightthickness=1,
                     highlightbackground=self.theme["border"],
                     highlightcolor=self.theme["accent"])
        e.pack(side=tk.LEFT, ipady=3)

        FlatButton(row, text="OK", theme=self.theme, kind="accent",
                   command=self._on_font, padx=12).pack(side=tk.LEFT,
                                                         padx=(8, 0))

    def _row_open_folder(self, parent) -> None:
        row = self._row_frame(parent)
        tk.Label(row, text=tr("set.open_folder"), bg=self.theme["bg"],
                 fg=self.theme["fg"], width=18, anchor="w").pack(side=tk.LEFT)
        FlatButton(row, text=tr("set.open_folder"), theme=self.theme,
                   command=open_data_dir).pack(side=tk.LEFT)

    def _row_reset_config(self, parent) -> None:
        row = self._row_frame(parent)
        tk.Label(row, text=tr("set.reset_config"), bg=self.theme["bg"],
                 fg=self.theme["fg"], width=18, anchor="w").pack(side=tk.LEFT)
        FlatButton(row, text=tr("set.reset_config"), theme=self.theme,
                   command=self._on_reset).pack(side=tk.LEFT)

    def _row_open_tutorial(self, parent) -> None:
        row = self._row_frame(parent)
        tk.Label(row, text=tr("set.about_help"), bg=self.theme["bg"],
                 fg=self.theme["fg"], width=18, anchor="w").pack(side=tk.LEFT)
        FlatButton(row, text=tr("set.about_help"), theme=self.theme,
                   command=self.app.open_tutorial).pack(side=tk.LEFT)

    # ------------------------------------------------------------------

    def _on_theme(self, label: str) -> None:
        new_theme = "dark" if label == tr("set.theme.dark") else "light"
        if new_theme == self.app.cfg.get("theme"):
            return
        self.app.cfg["theme"] = new_theme
        if self.app.cfg.get("remember", True):
            save_config(self.app.cfg)
        self.app.apply_theme()

    def _on_language(self, native_name: str) -> None:
        for code, name in LANGUAGES.items():
            if name == native_name:
                if code == get_language():
                    return
                set_language(code)
                self.app.cfg["language"] = code
                if self.app.cfg.get("remember", True):
                    save_config(self.app.cfg)
                self.app.retranslate()
                break

    def _on_font(self) -> None:
        try:
            size = int(self.v_font.get())
        except ValueError:
            return
        size = max(9, min(20, size))
        self.v_font.set(str(size))
        self.app.cfg["font_size"] = size
        if self.app.cfg.get("remember", True):
            save_config(self.app.cfg)
        self.app.apply_fonts()

    def _on_reset(self) -> None:
        if not messagebox.askyesno(tr("set.title"), tr("set.reset_confirm"),
                                   parent=self):
            return
        new_cfg = reset_config()
        self.app.cfg.clear()
        self.app.cfg.update(new_cfg)
        save_keys(self.app.keys)
        self.app.apply_theme()
        self.app.apply_fonts()
        self.app.retranslate()
        messagebox.showinfo(tr("set.title"), tr("set.reset_done"),
                            parent=self)

    # ------------------------------------------------------------------

    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme
        self.configure(bg=theme["bg"])
        apply_theme_to_tree(self, theme)
        self._scrollbar.configure(
            bg=theme["scrollbar"],
            troughcolor=theme["bg"],
            activebackground=theme["scrollbar_hl"],
        )

    def retranslate(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        self._build()