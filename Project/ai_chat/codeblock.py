# ai_chat/codeblock.py
"""独立代码 / 文本区块组件（PyQt6）。

在聊天流里把 fenced code block（```lang ... ```）渲染成一个带边框的区块：
  · 顶部条：语言名 + 图标按钮（预览 ▶ / 复制 ⧉ / 展开 ⛶）
  · 正文：等宽字体、跟随主题、横竖滚动、超长不自动换行
区块作为普通 QWidget 直接加进聊天区布局。
"""
from __future__ import annotations

import os
import tempfile
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel,
                             QPlainTextEdit, QPushButton, QSizePolicy,
                             QVBoxLayout, QWidget)

MONO_CANDIDATES = (
    "Cascadia Code", "Cascadia Mono", "JetBrains Mono", "Consolas",
    "Source Code Pro", "Menlo", "DejaVu Sans Mono", "Courier New",
)

# 图标
ICON_COPY = "⧉"
ICON_EXPAND = "⛶"
ICON_PREVIEW = "▶"
ICON_DONE = "✓"

MAX_BODY_ROWS = 18
MIN_BODY_ROWS = 2


def pick_mono(size: int = 11):
    """返回一个等宽 QFont。"""
    from PyQt6.QtGui import QFont, QFontDatabase

    db = QFontDatabase
    family = None
    available = db.families()
    for name in MONO_CANDIDATES:
        if name in available:
            family = name
            break

    if family is None:
        font = db.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font

    font = QFont(family, size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


# ---------------------------------------------------------------- 图标按钮

class _IconBtn(QPushButton):
    def __init__(self, glyph: str, command, tip: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(glyph, parent)
        self.setObjectName("codeIcon")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tip)
        self.setFlat(True)
        if command is not None:
            self.clicked.connect(lambda *_: self._safe(command))

    @staticmethod
    def _safe(command) -> None:
        try:
            command()
        except Exception:
            pass

    def set_glyph(self, glyph: str) -> None:
        self.setText(glyph)


# ---------------------------------------------------------------- 展开窗口

class CodeViewer(QDialog):
    def __init__(self, parent: QWidget | None, mono, size: int,
                 lang: str, code: str) -> None:
        super().__init__(parent)
        self.theme = None
        self._code = code
        self.setWindowTitle(lang or "code")
        self.resize(820, 600)
        self.setMinimumSize(420, 300)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        head = QHBoxLayout()
        title = QLabel(lang or "text")
        title.setProperty("role", "section")
        head.addWidget(title)
        head.addStretch(1)
        btn_copy = _IconBtn(ICON_COPY, self._copy, "复制")
        head.addWidget(btn_copy)
        root.addLayout(head)

        self.txt = QPlainTextEdit()
        self.txt.setObjectName("codeBody")
        self.txt.setReadOnly(True)
        self.txt.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        f = mono
        self.txt.setFont(f)
        self.txt.setPlainText(code)
        root.addWidget(self.txt, 1)

    def _copy(self) -> None:
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(self._code)


# ---------------------------------------------------------------- 代码块

class CodeBlock(QFrame):
    def __init__(self, parent: QWidget | None, theme: dict, lang: str = "",
                 code: str = "", mono=None, size: int = 11) -> None:
        super().__init__(parent)
        self.setObjectName("codeCard")
        self.theme = theme
        self.size = size
        self.mono = mono or pick_mono(size)
        self.lang = (lang or "").strip() or "text"
        self.code = (code or "").rstrip("\n")

        self._build()

    # ----------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        inner = QFrame()
        inner.setObjectName("codeCard")
        root.addWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 顶部条
        header = QFrame()
        header.setObjectName("codeHeader")
        h = QHBoxLayout(header)
        h.setContentsMargins(10, 3, 6, 3)
        h.setSpacing(2)

        self.lbl_lang = QLabel(self.lang)
        self.lbl_lang.setObjectName("codeLang")
        f = self.lbl_lang.font()
        f.setPointSize(max(8, self.size - 2))
        self.lbl_lang.setFont(f)
        h.addWidget(self.lbl_lang)
        h.addStretch(1)

        is_html = self.lang.lower() in ("html", "htm", "xml", "svg")
        if is_html:
            self.btn_preview = _IconBtn(ICON_PREVIEW, self.preview,
                                        "在浏览器中预览")
            h.addWidget(self.btn_preview)
        self.btn_copy = _IconBtn(ICON_COPY, self.copy, "一键复制")
        h.addWidget(self.btn_copy)
        self.btn_expand = _IconBtn(ICON_EXPAND, self.expand, "全屏展开")
        h.addWidget(self.btn_expand)

        v.addWidget(header)

        # 正文
        self.body = QPlainTextEdit()
        self.body.setObjectName("codeBody")
        self.body.setReadOnly(True)
        self.body.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.body.setFont(self.mono)
        self.body.setPlainText(self.code)
        self.body.setSizePolicy(QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Fixed)
        v.addWidget(self.body)

        self._adjust_height()

    def _adjust_height(self) -> None:
        line_count = self.code.count("\n") + 1
        rows = max(MIN_BODY_ROWS, min(line_count, MAX_BODY_ROWS))
        fm = self.body.fontMetrics()
        # QSS 上下 padding 各 8px
        self.body.setFixedHeight(rows * fm.lineSpacing() + 16)

    # ---------------------------------------------------------------- 动作

    def copy(self) -> None:
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.code)
        self.btn_copy.set_glyph(ICON_DONE)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1200, lambda: self.btn_copy.set_glyph(ICON_COPY))

    def expand(self) -> None:
        dlg = CodeViewer(self.window(), self.mono, self.size,
                         self.lang, self.code)
        dlg.exec()

    def preview(self) -> None:
        ext = ".html" if self.lang.lower() in ("html", "htm") else \
              (".svg" if self.lang.lower() == "svg" else ".xml")
        fd, path = tempfile.mkstemp(suffix=ext)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(self.code)
            webbrowser.open("file://" + path.replace("\\", "/"))
        except Exception:
            pass

    # ---------------------------------------------------------------- 字体 / 宽度

    def apply_font(self, mono, size: int) -> None:
        self.mono = mono
        self.size = size
        self.body.setFont(mono)
        self._adjust_height()

    def set_width(self, px: int) -> None:
        """Qt 布局自动处理宽度，保留方法以兼容旧调用。"""
        pass

    # ---------------------------------------------------------------- 主题

    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()
