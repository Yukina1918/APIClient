# ai_chat/about_page.py
"""关于页（PyQt6）：版本 / 开发者 / 工具链 / 帮助入口 / B 站 / GitHub。"""
from __future__ import annotations

import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QScrollArea, QVBoxLayout,
                             QWidget)

from .config import APP_VERSION
from .i18n import tr
from .widgets import Divider, FlatButton, clear_layout

GITHUB_URL = "https://github.com/Yukina1918/APIClient"
BILI_URL = "https://space.bilibili.com/1666042245"
TOOLS = "Python 3.14.7  |  Microsoft VS Code  |  PyCharm"


class AboutPage(QWidget):
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
        self.body_layout.setContentsMargins(40, 28, 40, 24)
        self.body_layout.setSpacing(4)
        self.scroll.setWidget(self._body)
        root.addWidget(self.scroll)

        self._populate()

    # ------------------------------------------------------------------

    def _populate(self) -> None:
        clear_layout(self.body_layout)

        title = QLabel("AI Chat")
        f = title.font()
        f.setPointSize(max(18, self.app.font_size + 13))
        f.setBold(True)
        title.setFont(f)
        self.body_layout.addWidget(title)

        sub = QLabel(tr("about.subtitle"))
        sub.setProperty("role", "hint")
        self.body_layout.addWidget(sub)
        self.body_layout.addSpacing(12)
        self.body_layout.addWidget(Divider(self._body, self.theme))
        self.body_layout.addSpacing(10)

        self._field(tr("about.version"), "v" + APP_VERSION)
        self._field(tr("about.author"), "Yukina1918")
        self._field(tr("about.tools"), TOOLS)

        body = QLabel(tr("about.body"))
        body.setWordWrap(True)
        body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.body_layout.addWidget(body)

        self.body_layout.addSpacing(10)
        self.body_layout.addWidget(Divider(self._body, self.theme))
        self.body_layout.addSpacing(8)

        self._section("about.help")
        self._add_button_widget(
            FlatButton(self._body, text=tr("about.help_btn"),
                       command=self.app.open_tutorial, kind="accent",
                       theme=self.theme, padx=18, pady=8))
        self._add_button_widget(
            FlatButton(self._body, text="▶  " + tr("about.bilibili"),
                       command=lambda: self._open(BILI_URL),
                       theme=self.theme, padx=18, pady=8))

        self._section("about.github")
        self._add_button_widget(
            FlatButton(self._body, text="▶  " + tr("about.github"),
                       command=lambda: self._open(GITHUB_URL),
                       theme=self.theme, padx=18, pady=8))

        self.body_layout.addStretch(1)
        footer = QLabel("© 2025 Yukina1918 · MIT License")
        footer.setProperty("role", "hint")
        self.body_layout.addWidget(footer)

    def _add_button_widget(self, btn) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 0)
        row.addWidget(btn)
        row.addStretch(1)
        self.body_layout.addLayout(row)

    def _field(self, key: str, value: str) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 3, 0, 3)
        lbl = QLabel(key)
        lbl.setProperty("role", "hint")
        lbl.setFixedWidth(120)
        row.addWidget(lbl)
        val = QLabel(value)
        f = val.font()
        if key == tr("about.version"):
            f.setBold(True)
        val.setFont(f)
        row.addWidget(val)
        row.addStretch(1)
        self.body_layout.addLayout(row)

    def _section(self, key: str) -> None:
        lbl = QLabel(tr(key))
        lbl.setProperty("role", "section")
        f = lbl.font()
        f.setPointSize(max(11, self.app.font_size + 1))
        f.setBold(True)
        lbl.setFont(f)
        self.body_layout.addWidget(lbl)

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
