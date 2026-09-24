# ai_chat/about_page.py
"""关于页：版本 / 开发者 / 工具链 / 帮助入口 / B 站。"""
from __future__ import annotations

import tkinter as tk
import webbrowser

from .config import APP_VERSION
from .i18n import tr
from .widgets import Divider, FlatButton, apply_theme_to_tree


GITHUB_URL = "https://github.com/Yukina1918/APIClient"
BILI_URL = "https://space.bilibili.com/1666042245"
TOOLS = "Python 3.14.7  |  Microsoft VS Code  |  PyCharm"


class AboutPage(tk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, bg=app.theme["bg"])
        self.app = app
        self.theme = app.theme

        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        pad = tk.Frame(self, bg=self.theme["bg"])
        pad.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

        title = tk.Label(pad, text="AI Chat", bg=self.theme["bg"],
                         fg=self.theme["fg"], font=("", 24, "bold"),
                         anchor="w")
        title.pack(fill=tk.X)

        sub = tk.Label(pad, text=tr("about.subtitle"), bg=self.theme["bg"],
                       fg=self.theme["hint_color"], font=("", 11),
                       anchor="w")
        sub._theme_role = "hint"
        sub.pack(fill=tk.X, pady=(0, 18))

        Divider(pad, self.theme).pack(fill=tk.X, pady=(0, 16))

        self._field(pad, tr("about.version"), "v" + APP_VERSION)
        self._field(pad, tr("about.author"), "Yukina1918")
        self._field(pad, tr("about.tools"), TOOLS)

        body = tk.Label(pad, text=tr("about.body"), bg=self.theme["bg"],
                        fg=self.theme["fg"], font=("", 10), anchor="w",
                        justify=tk.LEFT, wraplength=620)
        body.pack(fill=tk.X, pady=(14, 14))

        Divider(pad, self.theme).pack(fill=tk.X, pady=(0, 16))

        self._section(pad, "about.help")
        FlatButton(pad, text=tr("about.help_btn"), theme=self.theme,
                   command=self.app.open_tutorial,
                   kind="accent", padx=18, pady=8).pack(anchor="w", pady=4)

        self._section(pad, "about.bilibili")
        FlatButton(pad, text="▶  " + tr("about.bilibili"),
                   theme=self.theme,
                   command=lambda: self._open(BILI_URL),
                   padx=18, pady=8).pack(anchor="w", pady=4)

        self._section(pad, "about.github")
        FlatButton(pad, text="▶  " + tr("about.github"),
                   theme=self.theme,
                   command=lambda: self._open(GITHUB_URL),
                   padx=18, pady=8).pack(anchor="w", pady=4)

        footer = tk.Label(pad, text="© 2025 Yukina1918 · MIT License",
                          bg=self.theme["bg"], fg=self.theme["hint_color"],
                          font=("", 9), anchor="w")
        footer._theme_role = "hint"
        footer.pack(fill=tk.X, pady=(24, 0))

    def _field(self, parent, key: str, value: str) -> None:
        row = tk.Frame(parent, bg=self.theme["bg"])
        row.pack(fill=tk.X, pady=3)

        lbl = tk.Label(row, text=key, bg=self.theme["bg"],
                       fg=self.theme["hint_color"], font=("", 10),
                       width=14, anchor="w")
        lbl._theme_role = "hint"
        lbl.pack(side=tk.LEFT)

        val = tk.Label(row, text=value, bg=self.theme["bg"],
                       fg=self.theme["fg"], font=("", 10), anchor="w")
        val.pack(side=tk.LEFT)

    def _section(self, parent, key: str) -> None:
        lbl = tk.Label(parent, text=tr(key), bg=self.theme["bg"],
                       fg=self.theme["accent"], font=("", 11, "bold"),
                       anchor="w")
        lbl._theme_role = "section"
        lbl.pack(fill=tk.X, pady=(10, 4))

    @staticmethod
    def _open(url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    # ------------------------------------------------------------------

    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme
        self.configure(bg=theme["bg"])
        apply_theme_to_tree(self, theme)

    def retranslate(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        self._build()