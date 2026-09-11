# ai_chat/theme.py
"""亮色 / 暗色主题配色。"""
from __future__ import annotations

THEMES: dict[str, dict[str, str]] = {
    "light": {
        "bg":           "#f5f5f5",
        "fg":           "#1a1a1a",
        "panel_bg":     "#ffffff",
        "chat_bg":      "#ffffff",
        "chat_fg":      "#1a1a1a",
        "input_bg":     "#ffffff",
        "input_fg":     "#1a1a1a",
        "placeholder":  "#a0a0a0",
        "border":       "#d0d0d0",
        "user_color":   "#2f6feb",
        "ai_color":     "#1e874b",
        "sys_color":    "#8a8a8a",
        "err_color":    "#c62828",
        "src_color":    "#8a8a8a",
        "hint_color":   "#8a8a8a",
        "sel_bg":       "#cce4ff",
        "sel_fg":       "#1a1a1a",
    },
    "dark": {
        "bg":           "#1e1e1e",
        "fg":           "#e0e0e0",
        "panel_bg":     "#252525",
        "chat_bg":      "#1e1e1e",
        "chat_fg":      "#e0e0e0",
        "input_bg":     "#2a2a2a",
        "input_fg":     "#e0e0e0",
        "placeholder":  "#7a7a7a",
        "border":       "#3d3d3d",
        "user_color":   "#6ca4ff",
        "ai_color":     "#4ec97a",
        "sys_color":    "#909090",
        "err_color":    "#ff6b6b",
        "src_color":    "#909090",
        "hint_color":   "#909090",
        "sel_bg":       "#3d6ecc",
        "sel_fg":       "#ffffff",
    },
}

THEME_NAMES = ("light", "dark")


def get(name: str) -> dict:
    return THEMES.get(name, THEMES["light"])