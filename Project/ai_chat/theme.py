# ai_chat/theme.py
"""亮色 / 暗色主题配色表 + PyQt6 样式生成。

THEMES 是唯一的颜色来源；build_qss() 把它翻译成 QSS，
build_palette() 同步生成 QPalette（让下拉箭头 / 勾选等原生绘制元素也跟随主题），
ensure_icons() 按当前主题色生成勾选 / 下拉箭头小图标。
切换主题时整套界面（含代码块、图灵识别）都会自动跟随。
"""
from __future__ import annotations

import os
import tempfile
from string import Template

THEMES: dict[str, dict[str, str]] = {
    "light": {
        "bg":            "#f7f8fa",
        "fg":            "#1f2329",
        "panel_bg":      "#ffffff",
        "panel_fg":      "#1f2329",
        "chat_bg":       "#ffffff",
        "chat_fg":       "#1f2329",
        "input_bg":      "#ffffff",
        "input_fg":      "#1f2329",
        "placeholder":   "#9aa0a6",
        "border":        "#e4e6eb",
        "divider":       "#eceef1",
        "user_color":    "#2f6feb",
        "ai_color":      "#1e874b",
        "sys_color":     "#8a8f99",
        "err_color":     "#d93025",
        "src_color":     "#8a8f99",
        "hint_color":    "#8a8f99",
        "btn_bg":        "#ffffff",
        "btn_fg":        "#1f2329",
        "btn_hover":     "#eef1f5",
        "btn_active":    "#e1e5ea",
        "btn_disabled":  "#b0b4ba",
        "accent":        "#2f6feb",
        "accent_fg":     "#ffffff",
        "accent_hover":  "#4a83f0",
        "accent_active": "#1f5ed4",
        "nav_bg":        "#ffffff",
        "nav_fg":        "#4b5058",
        "nav_active_bg": "#eaf1ff",
        "nav_active_fg": "#2f6feb",
        "nav_hover_bg":  "#f0f3f7",
        "sel_bg":        "#cce4ff",
        "sel_fg":        "#1f2329",
        "scrollbar":     "#c8ccd2",
        "scrollbar_hl":  "#a8adb5",
        "link":          "#2f6feb",
        # 代码块（CodeBlock）
        "code_bg":         "#f4f5f7",
        "code_fg":         "#24292f",
        "code_header_bg":  "#e9ebee",
        "code_header_fg":  "#57606a",
        "code_border":     "#d6dae0",
        "code_btn":        "#57606a",
        "code_btn_hover":  "#d6dae0",
    },
    "dark": {
        "bg":            "#1a1d21",
        "fg":            "#e4e6eb",
        "panel_bg":      "#242830",
        "panel_fg":      "#e4e6eb",
        "chat_bg":       "#1f2328",
        "chat_fg":       "#e4e6eb",
        "input_bg":      "#2a2f36",
        "input_fg":      "#e4e6eb",
        "placeholder":   "#7a8089",
        "border":        "#363b43",
        "divider":       "#2c3138",
        "user_color":    "#6ca4ff",
        "ai_color":      "#4ec97a",
        "sys_color":     "#8f96a0",
        "err_color":     "#ff6b6b",
        "src_color":     "#8f96a0",
        "hint_color":    "#8f96a0",
        "btn_bg":        "#2a2f36",
        "btn_fg":        "#e4e6eb",
        "btn_hover":     "#343a43",
        "btn_active":    "#3d444e",
        "btn_disabled":  "#5a6068",
        "accent":        "#3d7dff",
        "accent_fg":     "#ffffff",
        "accent_hover":  "#558eff",
        "accent_active": "#2f6ae0",
        "nav_bg":        "#242830",
        "nav_fg":        "#a8aeb8",
        "nav_active_bg": "#2f3a4d",
        "nav_active_fg": "#6ca4ff",
        "nav_hover_bg":  "#2a2f36",
        "sel_bg":        "#3d6ecc",
        "sel_fg":        "#ffffff",
        "scrollbar":     "#3d444e",
        "scrollbar_hl":  "#4d545e",
        "link":          "#6ca4ff",
        # 代码块（CodeBlock）
        "code_bg":         "#15181c",
        "code_fg":         "#d6dde6",
        "code_header_bg":  "#21262d",
        "code_header_fg":  "#9aa4af",
        "code_border":     "#30363d",
        "code_btn":        "#9aa4af",
        "code_btn_hover":  "#30363d",
    },
}

THEME_NAMES = ("light", "dark")


def get(name: str) -> dict[str, str]:
    return THEMES.get(name, THEMES["light"])


def ids() -> tuple[str, ...]:
    return THEME_NAMES


# ----------------------------------------------------------------- QPalette

def _qcolor(hexstr: str):
    from PyQt6.QtGui import QColor
    return QColor(hexstr)


def build_palette(theme: dict):
    """按主题生成 QPalette，保证原生绘制元素（箭头/勾选/占位符等）也跟随。"""
    from PyQt6.QtGui import QPalette

    t = theme
    pal = QPalette()

    pal.setColor(QPalette.ColorRole.Window, _qcolor(t["bg"]))
    pal.setColor(QPalette.ColorRole.Base, _qcolor(t["input_bg"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, _qcolor(t["panel_bg"]))
    pal.setColor(QPalette.ColorRole.WindowText, _qcolor(t["fg"]))
    pal.setColor(QPalette.ColorRole.Text, _qcolor(t["input_fg"]))
    pal.setColor(QPalette.ColorRole.Button, _qcolor(t["btn_bg"]))
    pal.setColor(QPalette.ColorRole.ButtonText, _qcolor(t["btn_fg"]))
    pal.setColor(QPalette.ColorRole.Highlight, _qcolor(t["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, _qcolor(t["accent_fg"]))
    pal.setColor(QPalette.ColorRole.PlaceholderText, _qcolor(t["placeholder"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, _qcolor(t["panel_bg"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, _qcolor(t["panel_fg"]))
    pal.setColor(QPalette.ColorRole.Link, _qcolor(t["link"]))
    pal.setColor(QPalette.ColorRole.LinkVisited, _qcolor(t["accent_active"]))

    # 禁用态
    disabled = _qcolor(t["btn_disabled"])
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.WindowText, disabled)
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.Text, disabled)
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.ButtonText, disabled)
    return pal


# ----------------------------------------------------------------- 图标资源

def _icon_dir(theme_name: str) -> str:
    path = os.path.join(tempfile.gettempdir(), "aichat_icons", theme_name)
    os.makedirs(path, exist_ok=True)
    return path


def _qss_url(path: str) -> str:
    return "file:///" + path.replace("\\", "/").lstrip("/")


def ensure_icons(theme: dict, theme_name: str) -> dict[str, str]:
    """按当前主题色绘制勾选 / 下拉箭头 PNG，返回 QSS 可用的 url 字典。"""
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap

    folder = _icon_dir(theme_name)

    # ---- 勾选（accent_fg 色）----
    check_path = os.path.join(folder, "check.png")
    pm = QPixmap(20, 20)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(theme["accent_fg"]))
    pen.setWidthF(2.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawLine(QPointF(4, 10.5), QPointF(8.5, 15))
    p.drawLine(QPointF(8.5, 15), QPointF(16.5, 5.5))
    p.end()
    pm.save(check_path, "PNG")

    # ---- 下拉箭头（fg 色三角）----
    arrow_path = os.path.join(folder, "arrow.png")
    am = QPixmap(20, 20)
    am.fill(Qt.GlobalColor.transparent)
    p = QPainter(am)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(theme["btn_fg"]))
    tri = [QPointF(5, 7.5), QPointF(15, 7.5), QPointF(10, 14)]
    p.drawPolygon(*tri)
    p.end()
    am.save(arrow_path, "PNG")

    return {
        "check_icon": _qss_url(check_path),
        "arrow_icon": _qss_url(arrow_path),
    }


# ----------------------------------------------------------------- QSS

_QSS_TEMPLATE = Template("""
* { outline: none; }

QWidget {
    background-color: $bg;
    color: $fg;
}

QFrame#navBar { background-color: $nav_bg; }
QFrame#toolBar { background-color: $bg; }
QFrame#statusBar { background-color: $bg; }
QFrame#inputBar { background-color: $bg; }

QFrame[card="true"] {
    background-color: $panel_bg;
    border: 1px solid $border;
    border-radius: 8px;
}

/* ---- 标签 ---- */
QLabel { background-color: transparent; }
QLabel[role="section"] { color: $accent; }
QLabel[role="hint"]    { color: $hint_color; }
QLabel[role="link"]    { color: $link; }
QLabel[role="user"]    { color: $user_color; }
QLabel[role="ai"]      { color: $ai_color; }
QLabel[role="sys"]     { color: $sys_color; }
QLabel[role="err"]     { color: $err_color; }
QLabel[role="src"]     { color: $src_color; }

/* ---- 按钮 ---- */
QPushButton {
    background-color: $btn_bg;
    color: $btn_fg;
    border: 1px solid $border;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton:hover { background-color: $btn_hover; }
QPushButton:pressed { background-color: $btn_active; }
QPushButton:disabled { color: $btn_disabled; background-color: $btn_bg; }

QPushButton[kind="accent"] {
    background-color: $accent;
    color: $accent_fg;
    border: 1px solid $accent;
}
QPushButton[kind="accent"]:hover { background-color: $accent_hover; }
QPushButton[kind="accent"]:pressed { background-color: $accent_active; }
QPushButton[kind="accent"]:disabled {
    background-color: $btn_bg; color: $btn_disabled; border: 1px solid $border;
}

QPushButton[kind="ghost"] {
    background-color: transparent;
    color: $nav_fg;
    border: 1px solid transparent;
}
QPushButton[kind="ghost"]:hover { background-color: $nav_hover_bg; }
QPushButton[kind="ghost"]:pressed { background-color: $nav_active_bg; }
QPushButton[kind="ghost"]:checked {
    background-color: $nav_active_bg;
    color: $nav_active_fg;
    border: 1px solid transparent;
}

/* ---- 输入控件 ---- */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: $input_bg;
    color: $input_fg;
    border: 1px solid $border;
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: $sel_bg;
    selection-color: $sel_fg;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid $accent;
}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
    color: $btn_disabled;
}

/* ---- 下拉框 ---- */
QComboBox {
    background-color: $input_bg;
    color: $input_fg;
    border: 1px solid $border;
    border-radius: 6px;
    padding: 5px 8px;
    padding-right: 26px;
}
QComboBox:hover, QComboBox:focus { border: 1px solid $accent; }
QComboBox:disabled { color: $btn_disabled; }
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 24px;
    border: none;
    background: transparent;
}
QComboBox::down-arrow {
    image: url($arrow_icon);
    width: 12px;
    height: 12px;
}
/* 可编辑下拉框内部输入框：不要盖住右侧箭头 */
QComboBox QLineEdit {
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
    margin-right: 22px;
    color: $input_fg;
}
QComboBox QAbstractItemView {
    background-color: $panel_bg;
    color: $panel_fg;
    border: 1px solid $border;
    selection-background-color: $accent;
    selection-color: $accent_fg;
    outline: none;
}

/* ---- 复选框 ---- */
QCheckBox {
    background-color: transparent;
    color: $fg;
    spacing: 8px;
    padding: 2px;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border: 1px solid $border;
    border-radius: 4px;
    background-color: $input_bg;
}
QCheckBox::indicator:hover { border: 1px solid $accent; }
QCheckBox::indicator:checked {
    background-color: $accent;
    border: 1px solid $accent;
    image: url($check_icon);
}

/* ---- 菜单 ---- */
QMenuBar { background-color: $panel_bg; color: $panel_fg; }
QMenuBar::item { background: transparent; padding: 5px 10px; }
QMenuBar::item:selected {
    background-color: $accent; color: $accent_fg;
}
QMenu {
    background-color: $panel_bg;
    color: $panel_fg;
    border: 1px solid $border;
    padding: 4px;
}
QMenu::item { padding: 6px 22px 6px 18px; border-radius: 5px; }
QMenu::item:selected { background-color: $accent; color: $accent_fg; }
QMenu::item:disabled { color: $btn_disabled; }
QMenu::separator {
    height: 1px; background: $divider; margin: 5px 8px;
}
QMenu::icon { left: 8px; }

/* ---- 工具提示 ---- */
QToolTip {
    background-color: $panel_bg;
    color: $panel_fg;
    border: 1px solid $border;
    padding: 4px 6px;
}

/* ---- 滚动区域 ---- */
QScrollArea { border: none; background-color: transparent; }
QScrollArea > QWidget > QWidget { background-color: transparent; }

QStackedWidget { background-color: $bg; }

/* ---- 滚动条 ---- */
QScrollBar:vertical {
    background: transparent; width: 12px; margin: 2px;
}
QScrollBar:horizontal {
    background: transparent; height: 12px; margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: $scrollbar;
    min-height: 32px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: $scrollbar;
    min-width: 32px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover,
QScrollBar::handle:horizontal:hover { background-color: $scrollbar_hl; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ---- 代码块 ---- */
QFrame#codeCard {
    background-color: $code_border;
    border: 1px solid $code_border;
    border-radius: 7px;
}
QFrame#codeHeader { background-color: $code_header_bg; }
QLabel#codeLang {
    background-color: $code_header_bg;
    color: $code_header_fg;
}
QPushButton#codeIcon {
    background-color: $code_header_bg;
    color: $code_btn;
    border: none;
    border-radius: 4px;
    padding: 2px 7px;
}
QPushButton#codeIcon:hover { background-color: $code_btn_hover; }
QPlainTextEdit#codeBody {
    background-color: $code_bg;
    color: $code_fg;
    border: none;
    border-radius: 0;
    padding: 8px 10px;
    selection-background-color: $sel_bg;
    selection-color: $sel_fg;
}
""")


def build_qss(theme: dict, theme_name: str = "light",
              icons: dict | None = None) -> str:
    """根据配色表生成整套 QSS。"""
    icons = icons or ensure_icons(theme, theme_name)
    values = dict(theme)
    values.update(icons)
    return _QSS_TEMPLATE.safe_substitute(values)
