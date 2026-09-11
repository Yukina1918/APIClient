# ai_chat/tutorial.py
"""独立的教程窗口（跟随主题）。"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .i18n import get_language, tr
from .tutorials import TUTORIALS


def _tut_text(key: str) -> str:
    entry = TUTORIALS.get(key, {})
    lang = get_language()
    return entry.get(lang) or entry.get("en") or entry.get("zh_CN") or ""


class TutorialWindow(tk.Toplevel):
    def __init__(self, parent, fonts: dict, theme: dict) -> None:
        super().__init__(parent)
        self.fonts = fonts
        self.theme = theme
        self.transient(parent)
        self.geometry("860x620")
        self.minsize(680, 460)
        self.configure(bg=theme["bg"])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 6))

        self._tabs: dict[str, tk.Text] = {}
        for key in ("tut.tab.api", "tut.tab.search", "tut.tab.faq"):
            frame = ttk.Frame(self.notebook)
            text = tk.Text(
                frame, wrap=tk.WORD, relief=tk.FLAT, padx=14, pady=12,
                font=fonts["base"],
                bg=theme["panel_bg"], fg=theme["fg"],
                insertbackground=theme["fg"],
                highlightthickness=0, spacing1=1, spacing3=3,
            )
            scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
            text.configure(yscrollcommand=scroll.set)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.notebook.add(frame, text="")
            self._tabs[key] = text

        bottom = ttk.Frame(self, padding=(12, 0, 12, 12))
        bottom.pack(fill=tk.X)
        self.btn_close = ttk.Button(bottom, text=tr("tut.close"), command=self.destroy)
        self.btn_close.pack(side=tk.RIGHT)

        self.retranslate()
        self._center(parent)
        self.grab_set()
        self.focus_set()

    def retranslate(self) -> None:
        self.title(tr("tut.title"))
        for key, text in self._tabs.items():
            body_key = key.replace("tut.tab.", "tut.") + ".body"
            body = _tut_text(body_key)
            text.configure(state=tk.NORMAL)
            text.delete("1.0", tk.END)
            text.insert("1.0", body)
            text.configure(state=tk.DISABLED)
        for idx, key in enumerate(("tut.tab.api", "tut.tab.search", "tut.tab.faq")):
            self.notebook.tab(idx, text="  " + tr(key) + "  ")
        self.btn_close.configure(text=tr("tut.close"))

    def _center(self, parent) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        self.geometry("+%d+%d" % (
            px + max(0, (pw - w) // 2),
            py + max(0, (ph - h) // 3),
        ))