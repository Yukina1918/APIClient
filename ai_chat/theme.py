# ai_chat/theme.py
"""亮色 / 暗色主题配色表（纯 tk，可直接套用到 widget）。"""
from __future__ import annotations

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
    },
}

THEME_NAMES = ("light", "dark")


def get(name: str) -> dict[str, str]:
    return THEMES.get(name, THEMES["light"])


def ids() -> tuple[str, ...]:
    return THEME_NAMES