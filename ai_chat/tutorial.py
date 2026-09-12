# ai_chat/tutorial.py
"""独立的教程窗口（跟随主题，纯 tk 控件）。"""
from __future__ import annotations

import tkinter as tk

from .i18n import get_language, tr
from .tutorials import TUTORIALS
from .widgets import Divider, FlatButton, apply_theme_to_tree


def _tut_text(key: str) -> str:
    entry = TUTORIALS.get(key, {})
    lang = get_language()
    return entry.get(lang) or entry.get("en") or entry.get("zh_CN") or ""


class TutorialWindow(tk.Toplevel):
    def __init__(self, parent, app) -> None:
        super().__init__(parent)
        self.app = app
        self.theme = app.theme

        self.transient(parent)
        self.geometry("820x620")
        self.minsize(640, 420)
        self.configure(bg=self.theme["bg"])

        # 顶部：页签
        tabs_bar = tk.Frame(self, bg=self.theme["bg"])
        tabs_bar.pack(fill=tk.X, padx=14, pady=(12, 6))

        self._tab_buttons: dict[str, FlatButton] = {}
        self._current = "tut.tab.api"

        for key in ("tut.tab.api", "tut.tab.search", "tut.tab.faq"):
            btn = FlatButton(tabs_bar, text=tr(key), theme=self.theme,
                             command=lambda k=key: self._select_tab(k))
            btn.pack(side=tk.LEFT, padx=(0, 6))
            self._tab_buttons[key] = btn

        Divider(self, self.theme).pack(fill=tk.X, padx=14)

        # 内容区
        body = tk.Frame(self, bg=self.theme["bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)
        self._body = body

        self._text = tk.Text(
            body, wrap=tk.WORD, relief=tk.FLAT, padx=14, pady=12,
            font=(app.font_family, app.font_size),
            bg=self.theme["panel_bg"], fg=self.theme["fg"],
            insertbackground=self.theme["fg"],
            highlightthickness=1,
            highlightbackground=self.theme["border"],
            highlightcolor=self.theme["border"],
            spacing1=1, spacing3=3,
        )
        sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=self._text.yview,
                          bd=0, width=10, relief=tk.FLAT,
                          troughcolor=self.theme["bg"],
                          bg=self.theme["scrollbar"])
        self._text.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar = sb

        # 底部
        bottom = tk.Frame(self, bg=self.theme["bg"])
        bottom.pack(fill=tk.X, padx=14, pady=(0, 12))
        self.btn_close = FlatButton(bottom, text=tr("tut.close"),
                                    theme=self.theme, kind="accent",
                                    command=self.destroy)
        self.btn_close.pack(side=tk.RIGHT)

        self._select_tab(self._current)
        self._center(parent)
        self.grab_set()
        self.focus_set()

    # ------------------------------------------------------------------

    def _select_tab(self, key: str) -> None:
        self._current = key
        body_key = key.replace("tut.tab.", "tut.") + ".body"
        body = _tut_text(body_key)
        self._text.configure(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.insert("1.0", body)
        self._text.configure(state=tk.DISABLED)

        for k, btn in self._tab_buttons.items():
            btn._kind = "accent" if k == key else "ghost"
            btn.refresh_theme(self.theme)

    # ------------------------------------------------------------------

    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme
        self.configure(bg=theme["bg"])
        # 递归刷所有子控件（Divider 会走自己的 refresh_theme，不会被误改）
        apply_theme_to_tree(self, theme)

        # 教程正文的 Text 单独用 panel_bg / border，覆盖 Text 默认的 input_bg
        self._text.configure(
            bg=theme["panel_bg"], fg=theme["fg"],
            insertbackground=theme["fg"],
            highlightbackground=theme["border"],
            highlightcolor=theme["border"],
        )
        self._scrollbar.configure(
            bg=theme["scrollbar"],
            troughcolor=theme["bg"],
            activebackground=theme["scrollbar_hl"],
        )

    def retranslate(self) -> None:
        self.title(tr("tut.title"))
        for key, btn in self._tab_buttons.items():
            btn.set_text(tr(key))
        self.btn_close.set_text(tr("tut.close"))
        self._select_tab(self._current)

    # ------------------------------------------------------------------

    def _center(self, parent) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        self.geometry("+%d+%d" % (
            px + max(0, (pw - w) // 2),
            py + max(0, (ph - h) // 3),
        ))