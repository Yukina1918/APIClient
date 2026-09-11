# ai_chat/app.py
"""主窗口（grid 布局 + 主题 + 聊天记录）。"""
from __future__ import annotations

import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from .client import APIError, ChatClient, NetworkError
from .config import (APP_NAME, APP_VERSION, MAX_HISTORY, load_config,
                     remove_config, save_config)
from .formatting import soften_markdown
from .history import (DEFAULT_NAME, ChatLog, delete_log, list_logs,
                      load_log, new_id, save_log)
from .i18n import LANGUAGES, get_language, set_language, tr
from .keys import (get_ai_key, get_search_key, load_keys,
                   migrate_from_config, save_keys)
from .providers import get_provider
from .search import (SearchError, build_search_prompt, format_sources,
                     run_search)
from .settings_dialog import SettingsDialog
from .theme import get as get_theme
from .tutorial import TutorialWindow

_FONT_CANDIDATES = (
    "Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑",
    "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC",
    "Meiryo UI", "Malgun Gothic", "Segoe UI", "TkDefaultFont",
)

PLACEHOLDER_KEY = "input.placeholder"


def _pick_font(root: tk.Misc) -> str:
    available = set(tkfont.families(root))
    for name in _FONT_CANDIDATES:
        if name in available:
            return name
    return "TkDefaultFont"


class ChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.cfg = load_config()
        self.keys = load_keys()
        set_language(self.cfg.get("language", "zh_CN"))
        self.theme = get_theme(self.cfg.get("theme", "light"))

        self.cfg, self.keys, migrated = migrate_from_config(self.cfg, self.keys)
        if migrated:
            save_config(self.cfg)
            save_keys(self.keys)

        self.history: list[dict] = []
        self.current_log: ChatLog | None = None
        self.busy = False
        self.stop_event = threading.Event()
        self.client: ChatClient | None = None
        self.q: queue.Queue = queue.Queue()
        self._stream_start: str | None = None
        self._tutorial: TutorialWindow | None = None
        self._settings_dialog: SettingsDialog | None = None
        self._history_menu: tk.Menu | None = None

        # 会被 _apply_theme 遍历改色的 tk.Frame 容器列表
        self._themed_frames: list[tk.Frame] = []

        self._init_fonts()
        self._build_menu()
        self._build_layout()

        self._install_placeholder()
        self._apply_theme()

        self.new_session(clear=True, silent=True)
        self.retranslate()
        self._update_status()

        self.root.after(60, self._poll_queue)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        if not get_ai_key(self.keys, self.cfg.get("provider", "")):
            self.root.after(300, self.open_tutorial)

    # ------------------------------------------------------------------ 字体

    def _init_fonts(self) -> None:
        size = int(self.cfg.get("font_size", 11))
        size = max(9, min(20, size))
        family = _pick_font(self.root)
        self.fonts = {
            "base":  (family, size),
            "head":  (family, size, "bold"),
            "small": (family, max(8, size - 2)),
            "input": (family, size + 1),
        }
        self.f_base = self.fonts["base"]
        self.f_head = self.fonts["head"]
        self.f_small = self.fonts["small"]
        self.f_input = self.fonts["input"]

    # ------------------------------------------------------------------ 菜单

    def _build_menu(self) -> None:
        self.menubar = tk.Menu(self.root)

        self.m_file = tk.Menu(self.menubar, tearoff=0)
        self.m_file.add_command(label="", command=self.open_settings)
        self.m_file.add_separator()
        self.m_file.add_command(label="", command=self.on_close)
        self.menubar.add_cascade(label="", menu=self.m_file)

        self.m_session = tk.Menu(self.menubar, tearoff=0)
        self.m_session.add_command(label="", command=self.new_session)
        self.m_session.add_command(label="", command=self.clear_display)
        self.menubar.add_cascade(label="", menu=self.m_session)

        self.m_lang = tk.Menu(self.menubar, tearoff=0)
        self.lang_var = tk.StringVar(value=get_language())
        for code, native_name in LANGUAGES.items():
            self.m_lang.add_radiobutton(
                label=native_name, value=code, variable=self.lang_var,
                command=lambda c=code: self.set_language(c))
        self.menubar.add_cascade(label="", menu=self.m_lang)

        self.m_help = tk.Menu(self.menubar, tearoff=0)
        self.m_help.add_command(label="", command=self.open_tutorial)
        self.m_help.add_command(label="", command=self.show_about)
        self.menubar.add_cascade(label="", menu=self.m_help)

        self.root.config(menu=self.menubar)

    # ------------------------------------------------------------------ 布局

    def _build_layout(self) -> None:
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)
        self.root.rowconfigure(3, weight=0)
        self.root.columnconfigure(0, weight=1)

        self._build_toolbar()      # row=0
        self._build_chat_area()    # row=1
        self._build_input_area()   # row=2
        self._build_status_bar()   # row=3

    def _new_frame(self, parent, **kw) -> tk.Frame:
        """创建一个会自动跟随主题改色的 tk.Frame。"""
        frame = tk.Frame(parent, bg=self.theme["bg"], **kw)
        self._themed_frames.append(frame)
        return frame

    def _build_toolbar(self) -> None:
        bar = self._new_frame(self.root)
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        bar.columnconfigure(5, weight=1)

        self.btn_settings = ttk.Button(bar, command=self.open_settings)
        self.btn_settings.grid(row=0, column=0, padx=(0, 6))

        self.btn_new = ttk.Button(bar, command=self.new_session)
        self.btn_new.grid(row=0, column=1, padx=(0, 6))

        self.btn_test = ttk.Button(bar, command=self.test_connection)
        self.btn_test.grid(row=0, column=2, padx=(0, 6))

        self.btn_clear = ttk.Button(bar, command=self.clear_display)
        self.btn_clear.grid(row=0, column=3, padx=(0, 6))

        self.v_search = tk.BooleanVar(
            value=bool(self.cfg.get("search", {}).get("enabled")))
        self.chk_search = ttk.Checkbutton(
            bar, variable=self.v_search, command=self._on_search_toggle)
        self.chk_search.grid(row=0, column=4, padx=(8, 0))

        # column 5 是弹簧

        self.lbl_model = ttk.Label(bar, text="")
        self.lbl_model.grid(row=0, column=6, padx=(0, 12))

        # 聊天记录栏
        self.history_bar = tk.Label(
            bar, text="", padx=12, pady=4,
            highlightthickness=1,
            highlightbackground="#d0d0d0",
            cursor="hand2", font=self.f_base)
        self.history_bar.grid(row=0, column=7, sticky="e", padx=(8, 0))
        self.history_bar.bind("<Button-1>", self._show_history_menu)

    def _build_chat_area(self) -> None:
        frame = self._new_frame(self.root)
        frame.grid(row=1, column=0, sticky="nsew", padx=8)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.chat = tk.Text(
            frame, wrap=tk.WORD, state=tk.DISABLED, font=self.f_base,
            relief=tk.FLAT, padx=12, pady=10, highlightthickness=1,
            spacing1=1, spacing3=2,
        )
        self.chat.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.chat.yview)
        self.chat.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        self.scroll = scroll

        self.chat.tag_configure("user", font=self.f_head)
        self.chat.tag_configure("ai", font=self.f_head)
        self.chat.tag_configure("sys", font=self.f_small)
        self.chat.tag_configure("err", font=self.f_head)
        self.chat.tag_configure("src", font=self.f_small)

    def _build_input_area(self) -> None:
        frame = self._new_frame(self.root)
        frame.grid(row=2, column=0, sticky="ew", padx=8, pady=6)
        frame.columnconfigure(0, weight=1)

        self.input = tk.Text(
            frame, height=4, wrap=tk.WORD, font=self.f_input,
            relief=tk.FLAT, padx=10, pady=8, highlightthickness=1,
        )
        self.input.grid(row=0, column=0, sticky="ew")
        self.input.bind("<Return>", self._on_enter)

        btn_col = self._new_frame(frame)
        btn_col.grid(row=0, column=1, sticky="ns", padx=(8, 0))

        self.btn_send = ttk.Button(btn_col, command=self.on_send)
        self.btn_send.pack(side=tk.TOP, fill=tk.X, ipady=6)

        self.btn_stop = ttk.Button(btn_col, command=self.on_stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.TOP, fill=tk.X, ipady=6, pady=(6, 0))

        self.lbl_hint = ttk.Label(frame, text="", font=self.f_small)
        self.lbl_hint.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

    def _build_status_bar(self) -> None:
        bar = self._new_frame(self.root, relief=tk.SUNKEN, bd=1)
        bar.grid(row=3, column=0, sticky="ew")
        self.lbl_status = ttk.Label(bar, text="", padding=(10, 3))
        self.lbl_status.pack(side=tk.LEFT)
        self.status_bar = bar

    # --------------------------------------------------------- placeholder

    def _install_placeholder(self) -> None:
        self.input.insert("1.0", tr(PLACEHOLDER_KEY))
        self.input._is_placeholder = True

        def on_focus_in(_e):
            if getattr(self.input, "_is_placeholder", False):
                self.input.delete("1.0", "end")
                self.input.configure(fg=self.theme["input_fg"])
                self.input._is_placeholder = False

        def on_focus_out(_e):
            if not self.input.get("1.0", "end-1c").strip():
                self.input.delete("1.0", "end")
                self.input.insert("1.0", tr(PLACEHOLDER_KEY))
                self.input.configure(fg=self.theme["placeholder"])
                self.input._is_placeholder = True

        self.input.bind("<FocusIn>", on_focus_in, add="+")
        self.input.bind("<FocusOut>", on_focus_out, add="+")

    def _get_input_text(self) -> str:
        if getattr(self.input, "_is_placeholder", False):
            return ""
        return self.input.get("1.0", "end").strip()

    def _clear_input(self) -> None:
        self.input.delete("1.0", "end")
        self.input._is_placeholder = False

    def _reset_placeholder(self) -> None:
        if not self.input.get("1.0", "end-1c").strip():
            self.input.delete("1.0", "end")
            self.input.insert("1.0", tr(PLACEHOLDER_KEY))
            self.input.configure(fg=self.theme["placeholder"])
            self.input._is_placeholder = True

    # --------------------------------------------------------- 主题应用

    def _init_ttk_style(self) -> None:
        """把 ttk 主题切成 clam 并注入当前配色。"""
        t = self.theme
        style = ttk.Style(self.root)

        if "clam" in style.theme_names():
            style.theme_use("clam")

        bg = t["bg"]
        fg = t["fg"]
        panel = t["panel_bg"]
        border = t["border"]
        sel_bg = t["sel_bg"]
        sel_fg = t["sel_fg"]

        style.configure(".", background=bg, foreground=fg,
                        bordercolor=border, darkcolor=border, lightcolor=border,
                        troughcolor=panel, fieldbackground=t["input_bg"],
                        focuscolor=sel_bg)

        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)

        # Button
        style.configure("TButton",
                        background=panel, foreground=fg,
                        bordercolor=border,
                        lightcolor=panel, darkcolor=panel,
                        focuscolor=sel_bg,
                        relief="flat", padding=(10, 4))
        style.map("TButton",
                  background=[("active", sel_bg), ("pressed", sel_bg),
                              ("disabled", panel)],
                  foreground=[("active", sel_fg), ("pressed", sel_fg),
                              ("disabled", t["hint_color"])])

        # Checkbutton
        style.configure("TCheckbutton",
                        background=bg, foreground=fg,
                        indicatorcolor=panel,
                        focuscolor=sel_bg)
        style.map("TCheckbutton",
                  background=[("active", bg)],
                  foreground=[("active", fg)],
                  indicatorcolor=[("selected", sel_bg),
                                  ("pressed", sel_bg)])

        # Entry / Combobox / Spinbox
        style.configure("TEntry",
                        fieldbackground=t["input_bg"], foreground=fg,
                        bordercolor=border, lightcolor=border, darkcolor=border,
                        insertcolor=fg)
        style.configure("TCombobox",
                        fieldbackground=t["input_bg"], background=panel,
                        foreground=fg, bordercolor=border, arrowcolor=fg,
                        lightcolor=border, darkcolor=border,
                        selectbackground=sel_bg, selectforeground=sel_fg)
        style.map("TCombobox",
                  fieldbackground=[("readonly", t["input_bg"])],
                  foreground=[("readonly", fg)],
                  background=[("readonly", panel)])
        style.configure("TSpinbox",
                        fieldbackground=t["input_bg"], background=panel,
                        foreground=fg, bordercolor=border, arrowcolor=fg,
                        lightcolor=border, darkcolor=border)

        # Scrollbar
        style.configure("TScrollbar",
                        background=panel, troughcolor=bg,
                        bordercolor=border, arrowcolor=fg,
                        lightcolor=panel, darkcolor=panel)
        style.map("TScrollbar", background=[("active", sel_bg)])

        # Notebook（设置窗口的页签）
        style.configure("TNotebook", background=bg,
                        bordercolor=border, lightcolor=bg, darkcolor=bg)
        style.configure("TNotebook.Tab",
                        background=panel, foreground=fg, padding=(14, 6),
                        bordercolor=border,
                        lightcolor=panel, darkcolor=panel)
        style.map("TNotebook.Tab",
                  background=[("selected", sel_bg), ("active", panel)],
                  foreground=[("selected", sel_fg), ("active", fg)],
                  lightcolor=[("selected", sel_bg)],
                  darkcolor=[("selected", sel_bg)])

        # 下拉列表（Combobox 弹出的那个 Listbox）
        try:
            self.root.option_add("*TCombobox*Listbox*Background", t["input_bg"])
            self.root.option_add("*TCombobox*Listbox*Foreground", fg)
            self.root.option_add("*TCombobox*Listbox*selectBackground", sel_bg)
            self.root.option_add("*TCombobox*Listbox*selectForeground", sel_fg)
        except Exception:
            pass

    def _apply_theme(self) -> None:
        t = self.theme

        # 先切 ttk 样式
        self._init_ttk_style()

        self.root.configure(bg=t["bg"])

        # 所有 tk.Frame 容器统一改色
        for frame in self._themed_frames:
            try:
                frame.configure(bg=t["bg"])
            except tk.TclError:
                pass

        self.chat.configure(
            bg=t["chat_bg"], fg=t["chat_fg"],
            insertbackground=t["chat_fg"],
            highlightbackground=t["border"],
            highlightcolor=t["border"],
            selectbackground=t["sel_bg"], selectforeground=t["sel_fg"],
        )

        self.input.configure(
            bg=t["input_bg"], fg=t["input_fg"],
            insertbackground=t["input_fg"],
            highlightbackground=t["border"],
            highlightcolor=t["border"],
            selectbackground=t["sel_bg"], selectforeground=t["sel_fg"],
        )
        if getattr(self.input, "_is_placeholder", False):
            self.input.configure(fg=t["placeholder"])

        self.chat.tag_configure("user", foreground=t["user_color"])
        self.chat.tag_configure("ai", foreground=t["ai_color"])
        self.chat.tag_configure("sys", foreground=t["sys_color"])
        self.chat.tag_configure("err", foreground=t["err_color"])
        self.chat.tag_configure("src", foreground=t["src_color"])

        self.history_bar.configure(
            bg=t["panel_bg"], fg=t["fg"],
            highlightbackground=t["border"])

        self.lbl_hint.configure(foreground=t["hint_color"])

    # --------------------------------------------------------- 文案

    def retranslate(self) -> None:
        self.root.title(tr("app.title"))

        self.menubar.entryconfig(0, label=tr("menu.file"))
        self.m_file.entryconfig(0, label=tr("menu.settings"))
        self.m_file.entryconfig(2, label=tr("menu.exit"))

        self.menubar.entryconfig(1, label=tr("menu.session"))
        self.m_session.entryconfig(0, label=tr("menu.new_session"))
        self.m_session.entryconfig(1, label=tr("menu.clear"))

        self.menubar.entryconfig(2, label=tr("menu.language"))

        self.menubar.entryconfig(3, label=tr("menu.help"))
        self.m_help.entryconfig(0, label=tr("menu.tutorial"))
        self.m_help.entryconfig(1, label=tr("menu.about"))

        self.btn_settings.configure(text=tr("toolbar.settings"))
        self.btn_new.configure(text=tr("toolbar.new"))
        self.btn_test.configure(text=tr("toolbar.test"))
        self.btn_clear.configure(text=tr("toolbar.clear"))
        self.chk_search.configure(text=tr("toolbar.search"))
        self.history_bar.configure(text=tr("toolbar.history"))

        self.btn_send.configure(text=tr("input.send"))
        self.btn_stop.configure(text=tr("input.stop"))
        self.lbl_hint.configure(text=tr("input.hint"))

        if getattr(self.input, "_is_placeholder", False):
            self.input.delete("1.0", "end")
            self.input.insert("1.0", tr(PLACEHOLDER_KEY))

        if self._tutorial is not None and self._tutorial.winfo_exists():
            self._tutorial.retranslate()

        self._update_status()

    def set_language(self, code: str) -> None:
        if code == get_language():
            return
        set_language(code)
        self.cfg["language"] = code
        if self.cfg.get("remember", True):
            save_config(self.cfg)
        self.retranslate()

    # ------------------------------------------------------------ 会话

    def _chat_state(self, state: str) -> None:
        self.chat.config(state=state)

    def append_message(self, header: str, body: str, tag: str) -> None:
        self._chat_state(tk.NORMAL)
        stamp = time.strftime("%H:%M:%S")
        self.chat.insert(tk.END, "%s  %s\n" % (header, stamp), tag)
        if body:
            body_tag = "err" if tag == "err" else ("src" if tag == "src" else "")
            self.chat.insert(tk.END, body.rstrip() + "\n", body_tag)
        self.chat.insert(tk.END, "\n")
        self._chat_state(tk.DISABLED)
        self.chat.see(tk.END)

    def _display_plain(self, header: str, body: str, tag: str) -> None:
        self._chat_state(tk.NORMAL)
        self.chat.insert(tk.END, header + "\n", tag)
        if body:
            self.chat.insert(tk.END, body.rstrip() + "\n")
        self.chat.insert(tk.END, "\n")
        self._chat_state(tk.DISABLED)

    def clear_display(self) -> None:
        self._chat_state(tk.NORMAL)
        self.chat.delete("1.0", tk.END)
        self._chat_state(tk.DISABLED)

    def _system_prompt(self) -> str:
        return (self.cfg.get("system_prompt") or "").strip()

    def new_session(self, clear: bool = True, silent: bool = False) -> None:
        self.stop_event.set()
        self.stop_event = threading.Event()
        self.busy = False
        self._stream_start = None
        self.history = []
        self.current_log = None

        if clear:
            self.clear_display()
        if not silent:
            self.append_message(tr("chat.system"), tr("chat.new_session"), "sys")
        self._set_busy_ui(False)
        self._update_status(tr("status.ready"))
        self._refresh_title()

    def _trim_history(self) -> None:
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]
            while self.history and self.history[0]["role"] != "user":
                self.history.pop(0)

    def _refresh_title(self) -> None:
        base = tr("app.title")
        if self.current_log and self.current_log.name:
            self.root.title(f"{base}  ·  {self.current_log.name}")
        else:
            self.root.title(base)

    # ------------------------------------------------------------ 聊天记录

    def _show_history_menu(self, event=None) -> None:
        menu = tk.Menu(self.root, tearoff=0)

        if self.current_log is not None or self.history:
            menu.add_command(label=tr("history.rename"),
                             command=self._rename_current)
            menu.add_separator()

        logs = list_logs()
        if not logs:
            menu.add_command(label=tr("history.empty"), state=tk.DISABLED)
        else:
            for log in logs[:30]:
                label = log.name[:36] or DEFAULT_NAME
                menu.add_command(
                    label=label,
                    command=lambda lid=log.id: self._load_log(lid))

        menu.add_separator()
        menu.add_command(label=tr("history.new"), command=self.new_session)

        self._history_menu = menu
        try:
            x = self.history_bar.winfo_rootx()
            y = self.history_bar.winfo_rooty() + self.history_bar.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _rename_current(self) -> None:
        current = ""
        if self.current_log is not None:
            current = self.current_log.name
        elif self.history:
            current = self._make_log_name()

        from tkinter import simpledialog
        new_name = simpledialog.askstring(
            tr("history.rename_title"),
            tr("history.rename_prompt"),
            initialvalue=current, parent=self.root,
        )
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            return

        if self.current_log is None:
            if not self.history:
                self.current_log = ChatLog(id=new_id(), name=new_name, messages=[])
                save_log(self.current_log)
            else:
                self.current_log = ChatLog(
                    id=new_id(), name=new_name, messages=list(self.history))
                save_log(self.current_log)
        else:
            self.current_log.name = new_name
            save_log(self.current_log)

        self._refresh_title()

    def _make_log_name(self) -> str:
        for msg in self.history:
            if msg.get("role") == "user":
                text = (msg.get("content", "") or "").strip().replace("\n", " ")
                if text:
                    return text[:20] + ("…" if len(text) > 20 else "")
        return tr("history.default_name")

    def _persist_current_log(self) -> None:
        if not self.history:
            return
        if self.current_log is None:
            self.current_log = ChatLog(id=new_id(), name="", messages=[])
        self.current_log.messages = list(self.history)
        if not self.current_log.name or self.current_log.name in (
                DEFAULT_NAME, "新话题", "未命名"):
            self.current_log.name = self._make_log_name()
        save_log(self.current_log)
        self._refresh_title()

    def _load_log(self, log_id: str) -> None:
        log = load_log(log_id)
        if log is None:
            return

        self.stop_event.set()
        self.stop_event = threading.Event()
        self.busy = False
        self._stream_start = None
        self.history = list(log.messages)
        self.current_log = log

        self.clear_display()
        for msg in log.messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                self._display_plain(tr("chat.you"), content, "user")
            elif role == "assistant":
                self._display_plain(tr("chat.ai"), content, "ai")

        self.append_message(tr("chat.system"),
                            tr("history.loaded", name=log.name), "sys")
        self._set_busy_ui(False)
        self._update_status(tr("status.ready"))
        self._refresh_title()

    # ------------------------------------------------------------ 发送

    def _on_enter(self, event) -> str | None:
        if event.state & 0x0001:
            return None
        text = self._get_input_text()
        if not text:
            return "break"
        self.on_send()
        return "break"

    def on_send(self) -> None:
        if self.busy:
            return
        text = self._get_input_text()
        if not text:
            return

        pid = self.cfg.get("provider", "")
        if not get_ai_key(self.keys, pid):
            self.append_message(tr("chat.system"), tr("chat.need_key"), "err")
            self.open_tutorial()
            return

        self._clear_input()
        self.history.append({"role": "user", "content": text})
        self.append_message(tr("chat.you"), text, "user")
        self._persist_current_log()
        self._start_request(text)

    def _start_request(self, user_text: str) -> None:
        self.busy = True
        self.stop_event = threading.Event()
        self._stream_start = None
        self._set_busy_ui(True)
        self._update_status(tr("status.requesting"))

        use_search = bool(self.v_search.get())
        threading.Thread(
            target=self._worker, args=(user_text, use_search), daemon=True,
        ).start()

    def _make_client(self, cfg: dict | None = None,
                     keys: dict | None = None) -> ChatClient:
        cfg = cfg or self.cfg
        keys = keys or self.keys
        provider = get_provider(cfg.get("provider", "custom"))
        try:
            temperature = float(cfg.get("temperature", 0.7))
        except (TypeError, ValueError):
            temperature = 0.7
        try:
            timeout = int(float(cfg.get("timeout", 120)))
        except (TypeError, ValueError):
            timeout = 120
        return ChatClient(
            base_url=cfg.get("base_url", ""),
            api_key=get_ai_key(keys, provider.id),
            model=cfg.get("model", ""),
            temperature=temperature,
            timeout=timeout,
            proxy=cfg.get("proxy", ""),
            auth_style=provider.auth_style,
        )

    def _compose_messages(self, user_text: str, use_search: bool) -> list[dict]:
        messages: list[dict] = []
        prompt = self._system_prompt()
        if prompt:
            messages.append({"role": "system", "content": prompt})

        try:
            max_ctx = int(self.cfg.get("max_context", 20))
        except (TypeError, ValueError):
            max_ctx = 20
        max_ctx = max(1, min(200, max_ctx))

        recent = self.history[-max_ctx:] if len(self.history) > max_ctx \
            else list(self.history)
        if recent and recent[-1].get("role") == "user":
            recent = recent[:-1]
        messages.extend(recent)

        content = user_text
        if use_search:
            self.q.put(("status", tr("status.searching")))
            search_cfg = dict(self.cfg.get("search", {}))
            search_cfg["api_key"] = get_search_key(
                self.keys, search_cfg.get("provider", ""))
            results = []
            try:
                results = run_search(search_cfg, user_text)
            except SearchError as exc:
                self.q.put(("notice", tr("search.failed",
                                          error=self._search_error_text(exc))))
                results = []
            if results:
                self.q.put(("sources", results))
                content = build_search_prompt(user_text, results)

        messages.append({"role": "user", "content": content})
        return messages

    @staticmethod
    def _search_error_text(exc: SearchError) -> str:
        code = str(exc)
        if code == "SEARCH_KEY_MISSING":
            return tr("search.key_missing")
        if code == "SEARXNG_ENDPOINT_MISSING":
            return tr("search.endpoint_missing")
        if code == "TIMEOUT":
            return tr("search.timeout")
        if code == "NETWORK":
            return tr("search.network")
        if code.startswith("HTTP_"):
            return tr("search.http_error", code=code[5:])
        return code

    def _worker(self, user_text: str, use_search: bool) -> None:
        try:
            messages = self._compose_messages(user_text, use_search)
            client = self._make_client()
            self.client = client
            answer = client.chat(
                messages,
                stream=bool(self.cfg.get("stream", True)),
                on_chunk=lambda piece: self.q.put(("chunk", piece)),
                stop_event=self.stop_event,
            )
            if self.stop_event.is_set():
                self.q.put(("stopped", answer))
            else:
                self.q.put(("done", answer))
        except NetworkError as exc:
            if str(exc) == "TIMEOUT":
                self.q.put(("error", "请求超时：请检查网络或在设置里加大超时时间。"))
            else:
                self.q.put(("error", str(exc)))
        except (APIError, Exception) as exc:
            self.q.put(("error", str(exc)))
        finally:
            self.client = None

    def on_stop(self) -> None:
        self.stop_event.set()
        client = self.client
        if client is not None:
            client.cancel()
        self._update_status(tr("status.stopped"))

    # ------------------------------------------------------------ 队列

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                self._handle(kind, payload)
        except queue.Empty:
            pass
        self.root.after(60, self._poll_queue)

    def _handle(self, kind: str, payload) -> None:
        if kind == "chunk":
            self._on_chunk(payload)
        elif kind == "sources":
            self.append_message(tr("chat.sources"), format_sources(payload), "src")
        elif kind == "notice":
            self.append_message(tr("chat.system"), payload, "sys")
        elif kind == "status":
            self._update_status(payload)
        elif kind in ("done", "stopped"):
            self._finalize(payload)
            if payload:
                self.history.append({"role": "assistant", "content": payload})
                self._trim_history()
            self._persist_current_log()
            self._set_busy_ui(False)
            self._update_status(
                tr("status.stopped") if kind == "stopped" else tr("status.done"))
        elif kind == "error":
            self._finalize("")
            self.append_message(tr("chat.error"), payload, "err")
            self._set_busy_ui(False)
            self._update_status(tr("status.failed"))
        elif kind == "test_ok":
            self._restore_test_button()
            messagebox.showinfo(
                tr("settings.test_ok_title"),
                tr("settings.test_ok_body", reply=str(payload)),
                parent=self.root)
        elif kind == "test_err":
            self._restore_test_button()
            messagebox.showerror(
                tr("settings.test_fail_title"),
                tr("settings.test_fail_body", error=str(payload)),
                parent=self.root)
        elif kind == "test_finished":
            self._restore_test_button()

    def _restore_test_button(self) -> None:
        d = self._settings_dialog
        if d is None:
            return
        try:
            if d.winfo_exists():
                d.restore_test_button()
        except tk.TclError:
            pass

    def _on_chunk(self, piece: str) -> None:
        if self._stream_start is None:
            self._chat_state(tk.NORMAL)
            stamp = time.strftime("%H:%M:%S")
            self.chat.insert(tk.END, "%s  %s\n" % (tr("chat.ai"), stamp), "ai")
            self._stream_start = self.chat.index("end-1c")
            self._chat_state(tk.DISABLED)

        self._chat_state(tk.NORMAL)
        self.chat.insert(tk.END, piece)
        self._chat_state(tk.DISABLED)
        self.chat.see(tk.END)

    def _finalize(self, answer: str) -> None:
        level = int(self.cfg.get("soften_level", 2))
        cleaned = soften_markdown(answer, level)

        if self._stream_start is not None:
            self._chat_state(tk.NORMAL)
            start = self._stream_start
            end = self.chat.index("end-1c")
            self.chat.delete(start, end)
            self.chat.insert(start, cleaned)
            self.chat.insert(tk.END, "\n\n")
            self._chat_state(tk.DISABLED)
            self.chat.see(tk.END)
            self._stream_start = None
        elif cleaned:
            self.append_message(tr("chat.ai"), cleaned, "ai")

    def _set_busy_ui(self, busy: bool) -> None:
        self.busy = busy
        self.btn_send.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.btn_stop.configure(state=tk.NORMAL if busy else tk.DISABLED)

    # ------------------------------------------------------------ 设置

    def open_settings(self) -> None:
        d = SettingsDialog(
            self.root, self.cfg, self.keys, self.fonts, self.theme,
            on_saved=self._apply_settings,
            make_client=self._make_client,
            queue=self.q,
        )
        self._settings_dialog = d
        d.load_values()

    def _apply_settings(self, new_cfg: dict, new_keys: dict) -> None:
        old_font = self.cfg.get("font_size")
        old_theme = self.cfg.get("theme", "light")
        self.cfg = new_cfg
        self.keys = new_keys

        if new_cfg.get("remember", True):
            if not save_config(new_cfg):
                messagebox.showwarning(
                    tr("settings.title"), tr("settings.saved_fail"), parent=self.root)
        else:
            remove_config()
        save_keys(new_keys)

        self.v_search.set(bool(new_cfg.get("search", {}).get("enabled", False)))

        if old_theme != new_cfg.get("theme", "light"):
            self.theme = get_theme(new_cfg.get("theme", "light"))

        if old_font != new_cfg.get("font_size"):
            self._init_fonts()
            self._apply_fonts()

        self._apply_theme()
        self._update_status()

    def _apply_fonts(self) -> None:
        self.chat.configure(font=self.f_base)
        self.input.configure(font=self.f_input)
        self.lbl_hint.configure(font=self.f_small)
        self.history_bar.configure(font=self.f_base)
        self.chat.tag_configure("user", font=self.f_head)
        self.chat.tag_configure("ai", font=self.f_head)
        self.chat.tag_configure("sys", font=self.f_small)
        self.chat.tag_configure("err", font=self.f_head)
        self.chat.tag_configure("src", font=self.f_small)

    def _on_search_toggle(self) -> None:
        enabled = bool(self.v_search.get())
        self.cfg.setdefault("search", {})["enabled"] = enabled
        if self.cfg.get("remember", True):
            save_config(self.cfg)
        self._update_status()

    def test_connection(self) -> None:
        pid = self.cfg.get("provider", "")
        if not get_ai_key(self.keys, pid):
            self.append_message(tr("chat.system"), tr("settings.need_key"), "err")
            self.open_tutorial()
            return
        client = self._make_client()

        def run() -> None:
            try:
                self.q.put(("test_ok", client.test()))
            except Exception as exc:
                self.q.put(("test_err", str(exc)))

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------ 帮助

    def open_tutorial(self) -> None:
        if self._tutorial is not None and self._tutorial.winfo_exists():
            self._tutorial.lift()
            self._tutorial.focus_set()
            return
        self._tutorial = TutorialWindow(self.root, self.fonts, self.theme)

    def show_about(self) -> None:
        messagebox.showinfo(
            tr("about.title"),
            tr("about.body", version=APP_VERSION),
            parent=self.root,
        )

    # ------------------------------------------------------------ 状态

    def _update_status(self, note: str | None = None) -> None:
        model = self.cfg.get("model") or "-"
        endpoint = (self.cfg.get("base_url") or "-")
        endpoint = endpoint.replace("https://", "").replace("http://", "")
        pid = self.cfg.get("provider", "")
        key_state = tr("status.key_ok") if get_ai_key(self.keys, pid) \
            else tr("status.key_none")

        parts = [
            "%s: %s" % (tr("status.model"), model),
            "%s: %s" % (tr("status.endpoint"), endpoint),
            key_state,
        ]
        if self.v_search.get():
            parts.append(tr("status.search_on"))

        self.lbl_model.configure(text="  |  ".join(parts))
        self.lbl_status.configure(
            text="%s: %s" % (tr("chat.system"), note or tr("status.ready")))

    # ------------------------------------------------------------ 退出

    def on_close(self) -> None:
        self.stop_event.set()
        if self.client is not None:
            self.client.cancel()
        self.root.destroy()


# --------------------------------------------------------------------------- 启动

def _enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def main() -> None:
    _enable_dpi_awareness()
    root = tk.Tk()
    root.geometry("960x680")
    root.minsize(600, 480)
    ChatApp(root)
    root.mainloop()