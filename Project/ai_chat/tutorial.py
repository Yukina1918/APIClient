# ai_chat/tutorial.py
"""教程窗口（PyQt6）：顶部页签 + 正文 + 关闭。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QPlainTextEdit,
                             QPushButton, QVBoxLayout, QWidget)

from .i18n import get_language, tr
from .tutorials import TUTORIALS
from .widgets import Divider, FlatButton

TAB_KEYS = ("tut.tab.api", "tut.tab.search", "tut.tab.agent",
             "tut.tab.vision", "tut.tab.faq")


def _tut_text(key: str) -> str:
    entry = TUTORIALS.get(key, {})
    lang = get_language()
    return entry.get(lang) or entry.get("en") or entry.get("zh_CN") or ""


class TutorialWindow(QDialog):
    def __init__(self, parent, app) -> None:
        super().__init__(parent)
        self.app = app
        self.theme = app.theme
        self._current = "tut.tab.api"

        self.setWindowTitle(tr("tut.title"))
        self.resize(820, 620)
        self.setMinimumSize(640, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(6)

        # 页签
        tabs_bar = QHBoxLayout()
        tabs_bar.setSpacing(6)
        self._tab_buttons: dict[str, FlatButton] = {}
        for key in TAB_KEYS:
            btn = FlatButton(self, text=tr(key),
                             command=lambda k=key: self._select_tab(k),
                             theme=self.theme, kind="ghost",
                             checkable=True)
            tabs_bar.addWidget(btn)
            self._tab_buttons[key] = btn
        tabs_bar.addStretch(1)
        root.addLayout(tabs_bar)
        root.addWidget(Divider(self, self.theme))

        # 正文
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont_like(app))
        root.addWidget(self._text, 1)

        # 底部
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.btn_close = FlatButton(self, text=tr("tut.close"),
                                    kind="accent", command=self.accept,
                                    theme=self.theme)
        bottom.addWidget(self.btn_close)
        root.addLayout(bottom)

        self._select_tab(self._current)
        self._center(parent)

    # ------------------------------------------------------------------

    def _select_tab(self, key: str) -> None:
        self._current = key
        body_key = key.replace("tut.tab.", "tut.") + ".body"
        self._text.setPlainText(_tut_text(body_key))

        for k, btn in self._tab_buttons.items():
            btn.setChecked(k == key)

    # ------------------------------------------------------------------

    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme
        style = self.style()
        style.unpolish(self)
        style.polish(self)

    def retranslate(self) -> None:
        self.setWindowTitle(tr("tut.title"))
        for key, btn in self._tab_buttons.items():
            btn.set_text(tr(key))
        self.btn_close.set_text(tr("tut.close"))
        self._select_tab(self._current)

    def _center(self, parent) -> None:
        try:
            geo_p = parent.frameGeometry()
        except Exception:
            return
        x = geo_p.x() + max(0, (geo_p.width() - 820) // 2)
        y = geo_p.y() + max(0, (geo_p.height() - 620) // 3)
        self.move(x, y)


def QFont_like(app):
    """教程正文字体（跟随应用基础字体）。"""
    from PyQt6.QtGui import QFont

    return QFont(app.font_family, app.font_size)
