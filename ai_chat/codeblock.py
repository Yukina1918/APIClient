# ai_chat/codeblock.py
"""独立代码 / 文本区块组件。

在聊天流里把 fenced code block（```lang ... ```）渲染成一个带边框的区块：
  · 顶部条：语言名 + 图标按钮（预览 ▶ / 复制 ⧉ / 展开 ⛶）
  · 正文：等宽字体、深色（跟随主题）、横竖滚动、超长不自动换行
用 tk.Text.window_create 嵌入聊天 Text。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

MONO_CANDIDATES = (
    "Cascadia Code", "Cascadia Mono", "JetBrains Mono", "Consolas",
    "Source Code Pro", "Menlo", "DejaVu Sans Mono", "Courier New",
    "TkFixedFont",
)

# 图标（BMP，常见字体可显示）
ICON_COPY = "⧉"
ICON_EXPAND = "⛶"
ICON_PREVIEW = "▶"
ICON_DONE = "✓"

MAX_BODY_ROWS = 18
MIN_BODY_ROWS = 2


def pick_mono(master: tk.Misc) -> str:
    try:
        available = set(tkfont.families(master))
    except tk.TclError:
        return "TkFixedFont"
    for name in MONO_CANDIDATES:
        if name in available:
            return name
    return "TkFixedFont"


# ---------------------------------------------------------------- ToolTip

class _ToolTip:
    def __init__(self, widget: tk.Widget, text_getter) -> None:
        self.widget = widget
        self.text_getter = text_getter
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def _show(self, _e=None) -> None:
        text = self.text_getter()
        if not text:
            return
        self.hide()
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        tip.wm_geometry("+%d+%d" % (x, y))
        lbl = tk.Label(tip, text=text, justify=tk.LEFT, padx=6, pady=3,
                       bg="#2b2f36", fg="#ffffff", font=("", 9), bd=0)
        lbl.pack()
        self.tip = tip

    def hide(self, _e=None) -> None:
        if self.tip is not None:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None


# ---------------------------------------------------------------- 图标按钮

class _IconBtn(tk.Label):
    def __init__(self, parent, glyph: str, command, theme: dict,
                 tip: str = "") -> None:
        super().__init__(parent, text=glyph, bd=0, padx=6, pady=2,
                         cursor="hand2")
        self._command = command
        self._tip_text = tip
        self._glyph = glyph
        self.refresh_theme(theme)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        if tip:
            _ToolTip(self, lambda: self._tip_text)

    def set_glyph(self, glyph: str) -> None:
        self._glyph = glyph
        self.configure(text=glyph)

    def refresh_theme(self, theme: dict) -> None:
        self._theme = theme
        self._normal_bg = theme["code_header_bg"]
        self._hover_bg = theme["code_btn_hover"]
        self.configure(bg=self._normal_bg, fg=theme["code_btn"])

    def _on_enter(self, _e) -> None:
        self.configure(bg=self._hover_bg)

    def _on_leave(self, _e) -> None:
        self.configure(bg=self._normal_bg)

    def _on_click(self, _e) -> None:
        try:
            self._command()
        except Exception:
            pass


# ---------------------------------------------------------------- 展开窗口

class CodeViewer(tk.Toplevel):
    def __init__(self, parent, theme, mono: str, size: int,
                 lang: str, code: str) -> None:
        super().__init__(parent)
        self.theme = theme
        self.title(lang or "code")
        self.configure(bg=theme["code_border"])
        self.geometry("820x600")
        self.minsize(420, 300)

        body = tk.Frame(self, bg=theme["code_bg"])
        body.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        head = tk.Frame(body, bg=theme["code_header_bg"])
        head.pack(fill=tk.X)
        tk.Label(head, text=lang or "text", bg=theme["code_header_bg"],
                 fg=theme["code_header_fg"], padx=10, pady=4,
                 anchor="w").pack(side=tk.LEFT)
        _IconBtn(head, ICON_COPY, self._copy, theme, "复制").pack(side=tk.RIGHT)

        tw = tk.Frame(body, bg=theme["code_bg"])
        tw.pack(fill=tk.BOTH, expand=True)
        tw.rowconfigure(0, weight=1)
        tw.columnconfigure(0, weight=1)

        txt = tk.Text(tw, wrap=tk.NONE, bg=theme["code_bg"],
                      fg=theme["code_fg"], bd=0, highlightthickness=0,
                      font=(mono, size), padx=10, pady=10)
        txt.grid(row=0, column=0, sticky="nsew")
        txt.insert("1.0", code)
        txt.configure(state=tk.DISABLED)

        vsb = tk.Scrollbar(tw, orient=tk.VERTICAL, command=txt.yview,
                           bd=0, width=10, relief=tk.FLAT,
                           bg=theme["code_header_bg"])
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = tk.Scrollbar(tw, orient=tk.HORIZONTAL, command=txt.xview,
                           bd=0, width=10, relief=tk.FLAT,
                           bg=theme["code_header_bg"])
        hsb.grid(row=1, column=0, sticky="ew")
        txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._txt = txt
        self._code = code

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._code)


# ---------------------------------------------------------------- 代码块

class CodeBlock(tk.Frame):
    def __init__(self, parent, theme: dict, lang: str = "", code: str = "",
                 mono: str = "TkFixedFont", size: int = 11) -> None:
        super().__init__(parent, bd=0, bg=theme["code_border"])
        self.theme = theme
        self.mono = mono
        self.size = size
        self.lang = (lang or "").strip() or "text"
        self.code = (code or "").rstrip("\n")

        self._build()
        self._measure = tkfont.Font(self, family=self.mono, size=self.size)

    # ----------------------------------------------------------------

    def _build(self) -> None:
        inner = tk.Frame(self, bg=self.theme["code_bg"])
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # 顶部条
        header = tk.Frame(inner, bg=self.theme["code_header_bg"])
        header.pack(fill=tk.X)
        self.lbl_lang = tk.Label(
            header, text=self.lang, bg=self.theme["code_header_bg"],
            fg=self.theme["code_header_fg"], padx=10, pady=4,
            font=("", max(8, self.size - 2)), anchor="w")
        self.lbl_lang.pack(side=tk.LEFT)

        self.btn_expand = _IconBtn(header, ICON_EXPAND, self.expand,
                                   self.theme, "全屏展开")
        self.btn_expand.pack(side=tk.RIGHT)
        self.btn_copy = _IconBtn(header, ICON_COPY, self.copy,
                                 self.theme, "一键复制")
        self.btn_copy.pack(side=tk.RIGHT)

        is_html = self.lang.lower() in ("html", "htm", "xml", "svg")
        if is_html:
            self.btn_preview = _IconBtn(header, ICON_PREVIEW, self.preview,
                                        self.theme, "在浏览器中预览")
            self.btn_preview.pack(side=tk.RIGHT)

        # 正文网格
        tw = tk.Frame(inner, bg=self.theme["code_bg"])
        tw.pack(fill=tk.BOTH)
        tw.rowconfigure(0, weight=1)
        tw.columnconfigure(0, weight=1)

        rows = self.code.count("\n") + 1
        height = max(MIN_BODY_ROWS, min(rows, MAX_BODY_ROWS))

        self.body = tk.Text(
            tw, wrap=tk.NONE, height=height, width=72,
            bg=self.theme["code_bg"], fg=self.theme["code_fg"],
            bd=0, highlightthickness=0, font=(self.mono, self.size),
            padx=10, pady=8, spacing1=1, spacing3=1)
        self.body.grid(row=0, column=0, sticky="nsew")
        self.body.insert("1.0", self.code)
        self.body.configure(state=tk.DISABLED)

        self.vsb = tk.Scrollbar(tw, orient=tk.VERTICAL,
                                command=self.body.yview, bd=0, width=10,
                                relief=tk.FLAT, bg=self.theme["code_header_bg"])
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb = tk.Scrollbar(tw, orient=tk.HORIZONTAL,
                                command=self.body.xview, bd=0, width=10,
                                relief=tk.FLAT, bg=self.theme["code_header_bg"])
        self.hsb.grid(row=1, column=0, sticky="ew")
        self.body.configure(yscrollcommand=self.vsb.set,
                            xscrollcommand=self.hsb.set)

    # ---------------------------------------------------------------- 动作

    def copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.code)
        self.btn_copy.set_glyph(ICON_DONE)
        self.after(1200, lambda: self.btn_copy.set_glyph(ICON_COPY))

    def expand(self) -> None:
        CodeViewer(self.winfo_toplevel(), self.theme, self.mono, self.size,
                   self.lang, self.code)

    def preview(self) -> None:
        import os
        import tempfile
        import webbrowser
        ext = ".html" if self.lang.lower() in ("html", "htm") else \
            (".svg" if self.lang.lower() == "svg" else ".xml")
        fd, path = tempfile.mkstemp(suffix=ext)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(self.code)
            webbrowser.open("file://" + path.replace("\\", "/"))
        except Exception:
            pass

    # ---------------------------------------------------------------- 宽度

    def set_width(self, px: int) -> None:
        """按可用像素宽度换算正文列数，让区块横向填满聊天区。"""
        try:
            char_w = self._measure.measure("M") or 7
        except (tk.TclError, AttributeError):
            char_w = 7
        usable = max(80, px - 2 - 12 - 12)   # 边框 + 内边距 + 滚动条
        cols = int(usable / char_w)
        try:
            self.body.configure(width=max(20, cols))
        except tk.TclError:
            pass

    # ---------------------------------------------------------------- 主题

    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme
        self.configure(bg=theme["code_border"])
        for w in self.winfo_children():
            try:
                self._refresh_one(w, theme)
            except tk.TclError:
                pass

    def _refresh_one(self, w, theme) -> None:
        rt = getattr(w, "refresh_theme", None)
        if callable(rt):
            rt(theme)
            return
        try:
            cls = w.winfo_class()
        except tk.TclError:
            return
        if cls == "Frame":
            w.configure(bg=theme["code_bg"])
            for child in w.winfo_children():
                self._refresh_one(child, theme)
        elif cls == "Label":
            w.configure(bg=theme["code_header_bg"], fg=theme["code_header_fg"])
        elif cls == "Text":
            w.configure(bg=theme["code_bg"], fg=theme["code_fg"])
        elif cls == "Scrollbar":
            w.configure(bg=theme["code_header_bg"])
