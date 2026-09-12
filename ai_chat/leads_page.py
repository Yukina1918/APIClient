# ai_chat/leads_page.py
"""线索页：GitHub / B 站 / 各 AI 服务商官网。"""
from __future__ import annotations

import tkinter as tk
import webbrowser

from .i18n import tr
from .providers import PROVIDERS
from .widgets import Divider, FlatButton, apply_theme_to_tree


LEAD_SECTIONS = [
    ("lead.developer", [
        ("GitHub · Yukina1918",
         "https://github.com/Yukina1918/APIClient"),
        ("Bilibili · Yukina1918",
         "https://space.bilibili.com/1666042245"),
    ]),
]


class LeadsPage(tk.Frame):
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

        title = tk.Label(pad, text=tr("lead.title"), bg=self.theme["bg"],
                         fg=self.theme["fg"], font=("", 16, "bold"),
                         anchor="w")
        title.pack(fill=tk.X, pady=(0, 4))

        Divider(pad, self.theme).pack(fill=tk.X, pady=(0, 18))

        # 开发者
        self._section(pad, "lead.developer")
        for name, url in LEAD_SECTIONS[0][1]:
            self._link_row(pad, name, url)

        # AI 服务商
        self._section(pad, "lead.ai_official")
        for p in PROVIDERS:
            if p.id == "custom":
                continue
            url = p.console or (p.base_url if p.base_url.startswith("http")
                                else "https://" + p.base_url)
            if not url or not url.startswith("http"):
                url = "https://" + (p.base_url or "localhost")
            self._link_row(pad, p.name, url)

    # ------------------------------------------------------------------

    def _section(self, parent, key: str) -> None:
        lbl = tk.Label(parent, text=tr(key), bg=self.theme["bg"],
                       fg=self.theme["accent"], font=("", 12, "bold"),
                       anchor="w")
        lbl._theme_role = "section"
        lbl.pack(fill=tk.X, pady=(16, 4))
        Divider(parent, self.theme).pack(fill=tk.X, pady=(0, 8))

    def _link_row(self, parent, name: str, url: str) -> None:
        row = tk.Frame(parent, bg=self.theme["bg"])
        row.pack(fill=tk.X, pady=3)

        btn = FlatButton(row, text="▶  " + name, theme=self.theme,
                         anchor="w", padx=10, pady=5,
                         command=lambda u=url: self._open(u))
        btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        url_lbl = tk.Label(row, text=url, bg=self.theme["bg"],
                           fg=self.theme["link"], font=("", 9), anchor="e",
                           cursor="hand2")
        url_lbl._theme_role = "link"
        url_lbl.pack(side=tk.RIGHT, padx=(10, 4))
        url_lbl.bind("<Button-1>", lambda e, u=url: self._open(u))

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
        self._scrollbar.configure(
            bg=theme["scrollbar"],
            troughcolor=theme["bg"],
            activebackground=theme["scrollbar_hl"],
        )

    def retranslate(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        self._build()