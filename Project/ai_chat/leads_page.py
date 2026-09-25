# ai_chat/leads_page.py
"""线索页（PyQt6）：GitHub / B 站 / 各 AI 服务商官网。"""
from __future__ import annotations

import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QScrollArea, QVBoxLayout,
                             QWidget)

from .i18n import tr
from .providers import PROVIDERS
from .widgets import Divider, FlatButton, clear_layout


class LeadsPage(QWidget):
    def __init__(self, parent, app) -> None:
        super().__init__(parent)
        self.app = app
        self.theme = app.theme

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self._body = QWidget()
        self.body_layout = QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(32, 20, 32, 20)
        self.body_layout.setSpacing(4)
        self.scroll.setWidget(self._body)
        root.addWidget(self.scroll)

        self._populate()

    # ------------------------------------------------------------------

    def _section(self, key: str) -> None:
        lbl = QLabel(tr(key))
        lbl.setProperty("role", "section")
        f = lbl.font()
        f.setPointSize(max(11, self.app.font_size + 1))
        f.setBold(True)
        lbl.setFont(f)
        self.body_layout.addWidget(lbl)
        self.body_layout.addWidget(Divider(self._body, self.theme))

    def _populate(self) -> None:
        clear_layout(self.body_layout)

        title = QLabel(tr("lead.title"))
        f = title.font()
        f.setPointSize(max(12, self.app.font_size + 5))
        f.setBold(True)
        title.setFont(f)
        self.body_layout.addWidget(title)
        self.body_layout.addWidget(Divider(self._body, self.theme))

        # 开发者
        self._section("lead.developer")
        self._link_row("GitHub · Yukina1918",
                       "https://github.com/Yukina1918/APIClient")
        self._link_row("Bilibili · Yukina1918",
                       "https://space.bilibili.com/1666042245")

        # AI 服务商
        self._section("lead.ai_official")
        for p in PROVIDERS:
            if p.id == "custom":
                continue
            url = p.console or (p.base_url if p.base_url.startswith("http")
                                else "https://" + p.base_url)
            if not url or not url.startswith("http"):
                url = "https://" + (p.base_url or "localhost")
            self._link_row(p.name, url)

        self.body_layout.addStretch(1)

    def _link_row(self, name: str, url: str) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 3, 0, 3)

        btn = FlatButton(self._body, text="▶  " + name, anchor="w",
                         command=lambda u=url: self._open(u),
                         theme=self.theme, padx=10, pady=5)
        row.addWidget(btn, 1)

        url_lbl = QLabel(url)
        url_lbl.setProperty("role", "link")
        url_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(url_lbl, 1)

        self.body_layout.addLayout(row)

    @staticmethod
    def _open(url: str) -> None:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    # ------------------------------------------------------------------

    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme

    def retranslate(self) -> None:
        self._populate()
