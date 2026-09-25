# ai_chat/widgets.py
"""PyQt6 轻量扁平控件。

颜色与悬停 / 按下效果全部由 theme.build_qss() 统一提供；
这里的控件只保留与旧版一致的接口（set_text / set_enabled /
refresh_theme），方便页面代码平移。
"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import (QFrame, QLabel, QLineEdit, QPushButton, QTextEdit,
                             QWidget)


# --------------------------------------------------------------------- 按钮

class FlatButton(QPushButton):
    def __init__(self, parent=None, text: str = "", command=None, theme=None,
                 kind: str = "normal", padx: int = 14, pady: int = 6,
                 anchor: str = "center", bg_key: str = "bg", **kw):
        super().__init__(text, parent)
        self._kind = kind
        self._command = command
        self._theme = theme or {}
        self._enabled = True

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # QSS 用 kind 属性区分 accent / ghost；普通按钮不设该属性
        qss_kind = kind if kind in ("accent", "ghost") else None
        self.setProperty("kind", qss_kind)

        if kw.pop("checkable", False):
            self.setCheckable(True)
        if kw.pop("checked", False):
            self.setChecked(True)

        if command is not None:
            self.clicked.connect(self._dispatch)

        # 未识别的旧式参数安全忽略（padx/pady 已由 QSS padding 接管）
        self._extra = kw

    def _dispatch(self, *_args) -> None:
        if not self._enabled:
            return
        if self._command is None:
            return
        try:
            self._command()
        except Exception:
            pass

    # ------------------------------------------------------------------

    def set_text(self, text: str) -> None:
        self.setText(text)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.setEnabled(enabled)

    def refresh_theme(self, theme: dict) -> None:
        self._theme = theme
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()


# --------------------------------------------------------------------- 分割线

class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None, theme: dict | None = None,
                 orient: str = "horizontal", **kw):
        super().__init__(parent)
        self._theme = theme or {}
        self.setFrameShape(QFrame.Shape.NoFrame)
        if orient == "horizontal":
            self.setFixedHeight(1)
        else:
            self.setFixedWidth(1)
        self.refresh_theme(self._theme)

    def refresh_theme(self, theme) -> None:
        self._theme = theme or {}
        color = (self._theme or {}).get("divider", "#eceef1")
        self.setStyleSheet("background-color: %s;" % color)


# --------------------------------------------------------------------- 输入框

class FlatEntry(QLineEdit):
    def __init__(self, parent: QWidget | None = None, theme: dict | None = None,
                 **kw):
        super().__init__(parent)
        self._theme = theme or {}
        text = kw.pop("text", None)
        if text:
            self.setText(text)
        if kw.pop("password", False):
            self.setEchoMode(QLineEdit.EchoMode.Password)
        self._extra = kw

    def refresh_theme(self, theme) -> None:
        self._theme = theme


class FlatText(QTextEdit):
    def __init__(self, parent: QWidget | None = None, theme: dict | None = None,
                 **kw):
        super().__init__(parent)
        self._theme = theme or {}
        text = kw.pop("text", None)
        if text:
            self.setText(text)
        self._extra = kw

    def refresh_theme(self, theme) -> None:
        self._theme = theme


# --------------------------------------------------------------------- 下拉

class FlatCombo(QFrame):
    """兼容旧接口的下拉；新代码可直接用 QComboBox。"""
    def __init__(self, parent: QWidget | None = None, theme: dict | None = None,
                 values=(), variable=None, width: int = 22, command=None,
                 **kw):
        from PyQt6.QtWidgets import QComboBox

        super().__init__(parent)
        from PyQt6.QtWidgets import QHBoxLayout
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self._theme = theme or {}
        self._user_command = command
        self._combo = QComboBox()
        lay.addWidget(self._combo)
        self.set_values(values)
        if width:
            self._combo.setMinimumWidth(width * 7)
        self._combo.currentTextChanged.connect(self._on_changed)

    def _on_changed(self, text: str) -> None:
        if self._user_command:
            try:
                self._user_command(text)
            except Exception:
                pass

    def set_values(self, values) -> None:
        self._combo.blockSignals(True)
        self._combo.clear()
        for v in values:
            self._combo.addItem(str(v))
        self._combo.blockSignals(False)

    def get(self) -> str:
        return self._combo.currentText()

    def set(self, value: str) -> None:
        self._combo.setCurrentText(str(value))

    def refresh_theme(self, theme) -> None:
        self._theme = theme


# --------------------------------------------------------------------- 复选

class FlatCheck(QFrame):
    """兼容旧接口的复选；新代码可直接用 QCheckBox。"""
    def __init__(self, parent: QWidget | None = None, theme: dict | None = None,
                 text: str = "", variable=None, command=None, **kw):
        from PyQt6.QtWidgets import QCheckBox, QHBoxLayout

        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._chk = QCheckBox(text)
        lay.addWidget(self._chk)
        self._user_command = command
        if command:
            self._chk.stateChanged.connect(lambda *_: command())

    def is_checked(self) -> bool:
        return self._chk.isChecked()

    def set_checked(self, value: bool) -> None:
        self._chk.setChecked(bool(value))

    def refresh_theme(self, theme) -> None:
        pass


# --------------------------------------------------------------------- 卡片

class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, theme: dict | None = None,
                 padx: int = 16, pady: int = 14, **kw):
        super().__init__(parent)
        self._theme = theme or {}
        self.setProperty("card", "true")
        from PyQt6.QtWidgets import QVBoxLayout
        self.body_layout = QVBoxLayout(self)
        self.body_layout.setContentsMargins(padx, pady, padx, pady)

    def refresh_theme(self, theme) -> None:
        self._theme = theme
        style = self.style()
        style.unpolish(self)
        style.polish(self)


# --------------------------------------------------------------------- 工具

def clear_layout(layout) -> None:
    """删除一个布局里的所有控件（含子布局）。"""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def styled_label(text: str = "", role: str | None = None,
                 bold: bool = False, wrap: bool = True,
                 parent: QWidget | None = None):
    from PyQt6.QtWidgets import QLabel

    lbl = QLabel(text, parent)
    if role:
        lbl.setProperty("role", role)
    if bold:
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
    if wrap:
        lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse |
        Qt.TextInteractionFlag.TextSelectableByKeyboard)
    lbl.setOpenExternalLinks(False)
    return lbl


def apply_theme_to_tree(root_widget, theme, skip_self: bool = True) -> None:
    """兼容旧接口：QSS 已全局生效，这里仅触发自定义控件的 refresh_theme。"""
    for w in root_widget.findChildren(QWidget):
        rt = getattr(w, "refresh_theme", None)
        if callable(rt):
            try:
                rt(theme)
            except Exception:
                pass


# ------------------------------------------------------------ 下拉文字箭头

class _ArrowLabel(QLabel):
    """叠加在 QComboBox 末尾的「▼」，点击即弹出下拉列表。"""
    def __init__(self, combo) -> None:
        super().__init__("▼", combo)
        self._combo = combo
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        f = self.font()
        if f.pointSize() > 8:
            f.setPointSize(f.pointSize() - 2)
        self.setFont(f)

    def mousePressEvent(self, event) -> None:
        self._combo.showPopup()
        super().mousePressEvent(event)

    def set_open(self, opened: bool) -> None:
        """下拉展开显示「▲」，收起显示「▼」。"""
        self.setText("▲" if opened else "▼")


class _ArrowReposition(QObject):
    """QComboBox 尺寸变化时，把箭头重新贴到右侧。"""
    def __init__(self, combo, arrow, width: int = 24) -> None:
        super().__init__(combo)
        self._combo = combo
        self._arrow = arrow
        self._width = width

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Resize:
            self._arrow.setGeometry(
                self._combo.width() - self._width - 2, 0,
                self._width, self._combo.height())
        return False


class _PopupWatcher(QObject):
    """监听下拉列表的弹出 / 收起，切换箭头方向。"""
    def __init__(self, arrow) -> None:
        super().__init__()
        self._arrow = arrow

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Show:
            self._arrow.set_open(True)
        elif event.type() == QEvent.Type.Hide:
            self._arrow.set_open(False)
        return False


def attach_text_arrow(combo, width: int = 24) -> QLabel:
    """在 QComboBox 末尾右对齐叠加文字「▼」，点击弹出列表。
    解决 QSS 下（尤其可编辑 QComboBox）原生下拉箭头不显示的问题。"""
    arrow = _ArrowLabel(combo)
    arrow.setStyleSheet("background: transparent; border: none;")
    filt = _ArrowReposition(combo, arrow, width)
    combo.installEventFilter(filt)
    arrow._filt = filt  # 保持过滤器引用，防止被回收
    # 监听下拉弹出 / 收起，切换 ▼ / ▲
    watcher = _PopupWatcher(arrow)
    combo.view().installEventFilter(watcher)
    arrow._watcher = watcher
    arrow.setGeometry(combo.width() - width - 2, 0, width, combo.height())
    arrow.raise_()
    combo._text_arrow = arrow
    return arrow
