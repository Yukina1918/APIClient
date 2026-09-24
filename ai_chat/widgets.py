# ai_chat/widgets.py
"""轻量自绘控件（基于 tk，不依赖 ttk）。"""
from __future__ import annotations

import tkinter as tk


# --------------------------------------------------------------------- 按钮

class FlatButton(tk.Label):
    def __init__(self, parent, text="", command=None, theme=None,
                 kind="normal", padx=14, pady=6, anchor="center",
                 bg_key="bg", **kw):
        self._theme = theme or {}
        self._kind = kind
        self._command = command
        self._enabled = True
        self._bg_key = bg_key

        super().__init__(parent, text=text, bd=0, padx=padx, pady=pady,
                         anchor=anchor, cursor="hand2", **kw)
        self._apply_style()
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _palette(self):
        t = self._theme
        if self._kind == "accent":
            return (t.get("accent", "#2f6feb"),
                    t.get("accent_fg", "#ffffff"),
                    t.get("accent_hover", "#4a83f0"),
                    t.get("accent_active", "#1f5ed4"))
        if self._kind == "ghost":
            if self._bg_key == "nav_bg":
                return (t.get("nav_bg", t.get("bg", "#ffffff")),
                        t.get("nav_fg", t.get("fg", "#1f2329")),
                        t.get("nav_hover_bg", "#f0f3f7"),
                        t.get("nav_active_bg", "#eaf1ff"))
            bg = t.get(self._bg_key, t.get("bg", "#f7f8fa"))
            return (bg, t.get("fg", "#1f2329"),
                    t.get("btn_hover", "#eef1f5"),
                    t.get("btn_active", "#e1e5ea"))
        return (t.get("btn_bg", "#ffffff"),
                t.get("btn_fg", "#1f2329"),
                t.get("btn_hover", "#eef1f5"),
                t.get("btn_active", "#e1e5ea"))

    def _apply_style(self) -> None:
        bg, fg, hover, active = self._palette()
        self._normal_bg = bg
        self._normal_fg = fg
        self._hover_bg = hover
        self._active_bg = active
        self.configure(bg=bg, fg=fg)

    def refresh_theme(self, theme: dict) -> None:
        self._theme = theme
        self._apply_style()
        if not self._enabled:
            self.configure(fg=theme.get("btn_disabled", "#b0b4ba"),
                           cursor="")

    # ------------------------------------------------------------------

    def _on_enter(self, _e):
        if self._enabled:
            self.configure(bg=self._hover_bg)

    def _on_leave(self, _e):
        if self._enabled:
            self.configure(bg=self._normal_bg)

    def _on_press(self, _e):
        if self._enabled:
            self.configure(bg=self._active_bg)

    def _on_release(self, event):
        if not self._enabled:
            return
        self.configure(bg=self._hover_bg)
        x, y = event.x, event.y
        if 0 <= x < self.winfo_width() and 0 <= y < self.winfo_height():
            if self._command:
                try:
                    self._command()
                except Exception:
                    pass

    # ------------------------------------------------------------------

    def set_text(self, text: str) -> None:
        self.configure(text=text)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            self.configure(bg=self._normal_bg, fg=self._normal_fg,
                           cursor="hand2")
        else:
            self.configure(bg=self._normal_bg,
                           fg=self._theme.get("btn_disabled", "#b0b4ba"),
                           cursor="")


# --------------------------------------------------------------------- 分割线

class Divider(tk.Frame):
    def __init__(self, parent, theme, orient="horizontal", **kw):
        self._theme = theme
        if orient == "horizontal":
            super().__init__(parent, height=1, bd=0,
                             bg=theme.get("divider", "#eceef1"), **kw)
            self.pack_propagate(False)
        else:
            super().__init__(parent, width=1, bd=0,
                             bg=theme.get("divider", "#eceef1"), **kw)
            self.pack_propagate(False)

    def refresh_theme(self, theme) -> None:
        self._theme = theme
        self.configure(bg=theme.get("divider", "#eceef1"))


# --------------------------------------------------------------------- 输入框

class FlatEntry(tk.Entry):
    def __init__(self, parent, theme, **kw):
        self._theme = theme
        kw.setdefault("bd", 0)
        kw.setdefault("highlightthickness", 1)
        super().__init__(parent, **kw)
        self.refresh_theme(theme)

    def refresh_theme(self, theme) -> None:
        self._theme = theme
        self.configure(
            bg=theme.get("input_bg", "#ffffff"),
            fg=theme.get("input_fg", "#1f2329"),
            insertbackground=theme.get("input_fg", "#1f2329"),
            highlightbackground=theme.get("border", "#e4e6eb"),
            highlightcolor=theme.get("accent", "#2f6feb"),
            selectbackground=theme.get("sel_bg", "#cce4ff"),
            selectforeground=theme.get("sel_fg", "#1f2329"),
        )


class FlatText(tk.Text):
    def __init__(self, parent, theme, **kw):
        self._theme = theme
        kw.setdefault("bd", 0)
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("wrap", tk.WORD)
        super().__init__(parent, **kw)
        self.refresh_theme(theme)

    def refresh_theme(self, theme) -> None:
        self._theme = theme
        self.configure(
            bg=theme.get("input_bg", "#ffffff"),
            fg=theme.get("input_fg", "#1f2329"),
            insertbackground=theme.get("input_fg", "#1f2329"),
            highlightbackground=theme.get("border", "#e4e6eb"),
            highlightcolor=theme.get("accent", "#2f6feb"),
            selectbackground=theme.get("sel_bg", "#cce4ff"),
            selectforeground=theme.get("sel_fg", "#1f2329"),
        )


# --------------------------------------------------------------------- 下拉

class FlatCombo(tk.Menubutton):
    def __init__(self, parent, theme, values=(), variable=None,
                 width=22, command=None, **kw):
        self._theme = theme
        self._values = list(values)
        self._variable = variable or tk.StringVar()
        self._user_command = command

        super().__init__(parent, textvariable=self._variable,
                         width=width, bd=0, anchor="w",
                         padx=10, pady=5, cursor="hand2",
                         highlightthickness=1, **kw)
        self._menu = tk.Menu(self, tearoff=0)
        self.configure(menu=self._menu)
        self._rebuild_menu()
        self.refresh_theme(theme)

    def _rebuild_menu(self) -> None:
        self._menu.delete(0, "end")
        for v in self._values:
            self._menu.add_command(label=str(v),
                                   command=lambda val=v: self._select(val))

    def _select(self, value) -> None:
        self._variable.set(value)
        if self._user_command:
            try:
                self._user_command(value)
            except Exception:
                pass

    def set_values(self, values) -> None:
        self._values = list(values)
        self._rebuild_menu()

    def get(self) -> str:
        return self._variable.get()

    def set(self, value) -> None:
        self._variable.set(value)

    def refresh_theme(self, theme) -> None:
        self._theme = theme
        self.configure(
            bg=theme.get("input_bg", "#ffffff"),
            fg=theme.get("input_fg", "#1f2329"),
            activebackground=theme.get("btn_hover", "#eef1f5"),
            activeforeground=theme.get("input_fg", "#1f2329"),
            highlightbackground=theme.get("border", "#e4e6eb"),
            highlightcolor=theme.get("accent", "#2f6feb"),
        )
        self._menu.configure(
            bg=theme.get("panel_bg", "#ffffff"),
            fg=theme.get("panel_fg", "#1f2329"),
            activebackground=theme.get("accent", "#2f6feb"),
            activeforeground=theme.get("accent_fg", "#ffffff"),
            bd=0,
        )


# --------------------------------------------------------------------- 复选

class FlatCheck(tk.Checkbutton):
    def __init__(self, parent, theme, text="", variable=None,
                 command=None, **kw):
        self._theme = theme
        super().__init__(parent, text=text, variable=variable,
                         command=command, bd=0, anchor="w",
                         cursor="hand2",
                         activebackground=theme.get("bg", "#ffffff"),
                         highlightthickness=0, **kw)
        self.refresh_theme(theme)

    def refresh_theme(self, theme) -> None:
        self._theme = theme
        self.configure(
            bg=theme.get("bg", "#f7f8fa"),
            fg=theme.get("fg", "#1f2329"),
            selectcolor=theme.get("panel_bg", "#ffffff"),
            activebackground=theme.get("bg", "#f7f8fa"),
            activeforeground=theme.get("fg", "#1f2329"),
            highlightbackground=theme.get("bg", "#f7f8fa"),
        )


# --------------------------------------------------------------------- 卡片

class Card(tk.Frame):
    def __init__(self, parent, theme, padx=16, pady=14, **kw):
        self._theme = theme
        super().__init__(parent, bd=1, relief=tk.SOLID,
                         padx=padx, pady=pady, **kw)
        self.refresh_theme(theme)

    def refresh_theme(self, theme) -> None:
        self._theme = theme
        self.configure(
            bg=theme.get("panel_bg", "#ffffff"),
            highlightbackground=theme.get("border", "#e4e6eb"),
            highlightcolor=theme.get("border", "#e4e6eb"),
        )


# --------------------------------------------------------------------- 递归刷新

def walk_widgets(widget):
    """深度优先遍历控件树。"""
    yield widget
    try:
        children = widget.winfo_children()
    except tk.TclError:
        return
    for child in children:
        yield from walk_widgets(child)


def apply_theme_to_tree(root_widget, theme, skip_self: bool = True) -> None:
    """递归给整棵控件树上色。

    skip_self=True（默认）时跳过 root_widget 自身，
    避免与调用方 refresh_theme 形成无限递归。
    """
    first = True
    for w in walk_widgets(root_widget):
        if skip_self and first:
            first = False
            continue
        _apply_theme_one(w, theme)


def _apply_theme_one(w, theme) -> None:
    rt = getattr(w, "refresh_theme", None)
    if callable(rt):
        try:
            rt(theme)
            return
        except tk.TclError:
            pass
        except Exception:
            pass

    try:
        cls = w.winfo_class()
    except tk.TclError:
        return

    role = getattr(w, "_theme_role", None)

    try:
        if cls in ("Frame", "Toplevel", "Tk"):
            w.configure(bg=theme["bg"])
        elif cls == "Label":
            if role == "section":
                w.configure(bg=theme["bg"], fg=theme["accent"])
            elif role == "hint":
                w.configure(bg=theme["bg"], fg=theme["hint_color"])
            elif role == "link":
                w.configure(bg=theme["bg"], fg=theme["link"])
            else:
                w.configure(bg=theme["bg"], fg=theme["fg"])
        elif cls == "Canvas":
            w.configure(bg=theme["bg"])
        elif cls == "Text":
            w.configure(
                bg=theme["input_bg"], fg=theme["input_fg"],
                insertbackground=theme["input_fg"],
                selectbackground=theme["sel_bg"],
                selectforeground=theme["sel_fg"],
            )
        elif cls == "Entry":
            w.configure(
                bg=theme["input_bg"], fg=theme["input_fg"],
                insertbackground=theme["input_fg"],
                highlightbackground=theme["border"],
                highlightcolor=theme["accent"],
            )
        elif cls == "Scrollbar":
            w.configure(
                bg=theme["scrollbar"],
                troughcolor=theme["bg"],
                activebackground=theme["scrollbar_hl"],
            )
        elif cls == "Menu":
            w.configure(
                bg=theme["panel_bg"], fg=theme["panel_fg"],
                activebackground=theme["accent"],
                activeforeground=theme["accent_fg"],
            )
    except tk.TclError:
        pass