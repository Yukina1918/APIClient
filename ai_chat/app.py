# ai_chat/app.py
"""主窗口：顶部导航 + 4 个页面（聊天/设置/线索/关于）。"""
from __future__ import annotations

import queue
import sys
import tkinter as tk
from tkinter import font as tkfont

from .about_page import AboutPage
from .chat_page import ChatPage
from .client import ChatClient
from .config import (APP_NAME, APP_VERSION, load_config, remove_config,
                     save_config)
from .i18n import LANGUAGES, get_language, set_language, tr
from .keys import (get_ai_key, load_keys, migrate_from_config, save_keys)
from .leads_page import LeadsPage
from .providers import get_provider
from .settings_page import SettingsPage
from .theme import get as get_theme
from .tutorial import TutorialWindow
from .widgets import Divider, FlatButton


_FONT_CANDIDATES = (
    "Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑",
    "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC",
    "Meiryo UI", "Malgun Gothic", "Segoe UI", "TkDefaultFont",
)


def _pick_font(root: tk.Misc) -> str:
    available = set(tkfont.families(root))
    for name in _FONT_CANDIDATES:
        if name in available:
            return name
    return "TkDefaultFont"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.cfg = load_config()
        self.keys = load_keys()
        set_language(self.cfg.get("language", "zh_CN"))
        self.theme = get_theme(self.cfg.get("theme", "light"))
        self.version = APP_VERSION

        self.cfg, self.keys, migrated = migrate_from_config(self.cfg, self.keys)
        if migrated:
            save_config(self.cfg)
            save_keys(self.keys)

        self._init_fonts()
        self.q: queue.Queue = queue.Queue()

        self._tutorial: TutorialWindow | None = None
        self.chat_settings_dialog = None

        self._nav_buttons: dict[str, FlatButton] = {}
        self._pages: dict[str, tk.Frame] = {}
        self._current_page = "chat"

        self._build_menu()
        self._build_layout()
        self.apply_theme()
        self.retranslate()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self._poll_global_queue)

        if not get_ai_key(self.keys, self.cfg.get("provider", "")):
            self.root.after(400, self.open_tutorial)

    # ------------------------------------------------------------------

    def _init_fonts(self) -> None:
        size = int(self.cfg.get("font_size", 11))
        size = max(9, min(20, size))
        family = _pick_font(self.root)
        self.font_family = family
        self.font_size = size
        self.f_base = (family, size)
        self.f_head = (family, size, "bold")
        self.f_small = (family, max(8, size - 2))
        self.f_input = (family, size + 1)

        from .codeblock import pick_mono
        self.mono_font = pick_mono(self.root)

    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        self.menubar = tk.Menu(self.root)

        self.m_file = tk.Menu(self.menubar, tearoff=0)
        self.m_file.add_command(label="", command=self.open_settings)
        self.m_file.add_separator()
        self.m_file.add_command(label="", command=self.on_close)
        self.menubar.add_cascade(label="", menu=self.m_file)

        self.m_session = tk.Menu(self.menubar, tearoff=0)
        self.m_session.add_command(label="", command=self._new_session)
        self.m_session.add_command(label="", command=self._clear_view)
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
        self.m_help.add_command(label="", command=self.open_about)
        self.menubar.add_cascade(label="", menu=self.m_help)

        self.root.config(menu=self.menubar)

    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)

        nav = tk.Frame(self.root, bg=self.theme["nav_bg"])
        nav.grid(row=0, column=0, sticky="ew")
        self._nav_bar = nav

        inner = tk.Frame(nav, bg=self.theme["nav_bg"])
        inner.pack(fill=tk.X, padx=8, pady=6)
        self._nav_inner = inner

        for key in ("chat", "settings", "leads", "about"):
            btn = FlatButton(inner, text=tr(f"nav.{key}"), theme=self.theme,
                             command=lambda k=key: self.show_page(k),
                             kind="ghost", padx=18, pady=6,
                             bg_key="nav_bg")
            btn.pack(side=tk.LEFT, padx=(0, 4))
            self._nav_buttons[key] = btn

        Divider(self.root, self.theme).grid(row=0, column=0,
                                            sticky="sew", pady=(48, 0))

        container = tk.Frame(self.root, bg=self.theme["bg"])
        container.grid(row=1, column=0, sticky="nsew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self._container = container

        self.chat_page = ChatPage(container, self)
        self.settings_page = SettingsPage(container, self)
        self.leads_page = LeadsPage(container, self)
        self.about_page = AboutPage(container, self)

        self._pages = {
            "chat": self.chat_page,
            "settings": self.settings_page,
            "leads": self.leads_page,
            "about": self.about_page,
        }
        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()

        self.show_page("chat")

    # ------------------------------------------------------------------

    def show_page(self, key: str) -> None:
        if key not in self._pages:
            return
        self._current_page = key
        for k, page in self._pages.items():
            if k == key:
                page.grid()
            else:
                page.grid_remove()

        for k, btn in self._nav_buttons.items():
            btn._kind = "accent" if k == key else "ghost"
            btn.refresh_theme(self.theme)

        self.refresh_title()

    # ------------------------------------------------------------------

    def make_client(self, cfg=None, keys=None) -> ChatClient:
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

    # ------------------------------------------------------------------

    def apply_settings(self, new_cfg: dict, new_keys: dict) -> None:
        old_font = self.cfg.get("font_size")

        self.cfg = new_cfg
        self.keys = new_keys
        self.chat_page.cfg = new_cfg
        self.chat_page.keys = new_keys

        if new_cfg.get("remember", True):
            save_config(new_cfg)
        else:
            remove_config()
        save_keys(new_keys)

        self.chat_page.v_search.set(
            bool(new_cfg.get("search", {}).get("enabled", False)))

        self.apply_theme()

        if old_font != new_cfg.get("font_size"):
            self._init_fonts()
            self.apply_fonts()

        self.chat_page._update_status()

    # ------------------------------------------------------------------
    # ⭐ 关键修复：每次从 cfg 重新取 theme，然后递归刷新整棵树

    def apply_theme(self) -> None:
        self.theme = get_theme(self.cfg.get("theme", "light"))
        t = self.theme

        self.root.configure(bg=t["bg"])
        self._nav_bar.configure(bg=t["nav_bg"])
        self._nav_inner.configure(bg=t["nav_bg"])
        self._container.configure(bg=t["bg"])

        for k, btn in self._nav_buttons.items():
            btn._kind = "accent" if k == self._current_page else "ghost"
            btn.refresh_theme(t)

        self._apply_menu_theme(t)

        for page in self._pages.values():
            try:
                page.refresh_theme(t)
            except Exception:
                pass

        if self._tutorial is not None and self._tutorial.winfo_exists():
            try:
                self._tutorial.refresh_theme(t)
            except tk.TclError:
                pass

        dlg = self.chat_settings_dialog
        if dlg is not None:
            try:
                if dlg.winfo_exists():
                    dlg.refresh_theme(t)
            except (tk.TclError, AttributeError):
                pass

    def _apply_menu_theme(self, theme: dict) -> None:
        for m in (self.menubar, self.m_file, self.m_session,
                  self.m_lang, self.m_help):
            try:
                m.configure(
                    bg=theme["panel_bg"], fg=theme["panel_fg"],
                    activebackground=theme["accent"],
                    activeforeground=theme["accent_fg"],
                    bd=0,
                )
            except tk.TclError:
                pass

    def apply_fonts(self) -> None:
        self.chat_page.chat.configure(font=self.f_base)
        self.chat_page.input.configure(font=self.f_input)
        self.chat_page.lbl_hint.configure(font=("", 9))
        try:
            self.settings_page.retranslate()
        except Exception:
            pass

    # ------------------------------------------------------------------

    def retranslate(self) -> None:
        self.root.title(tr("app.title"))

        self.menubar.entryconfig(0, label=tr("menu.file"))
        self.m_file.entryconfig(0, label=tr("nav.settings"))
        self.m_file.entryconfig(2, label=tr("menu.exit"))

        self.menubar.entryconfig(1, label=tr("menu.session"))
        self.m_session.entryconfig(0, label=tr("menu.new"))
        self.m_session.entryconfig(1, label=tr("menu.clear"))

        self.menubar.entryconfig(2, label=tr("menu.lang"))

        self.menubar.entryconfig(3, label=tr("menu.help"))
        self.m_help.entryconfig(0, label=tr("tut.title"))
        self.m_help.entryconfig(1, label=tr("about.title"))

        for key, btn in self._nav_buttons.items():
            btn.set_text(tr(f"nav.{key}"))

        for page in self._pages.values():
            try:
                page.retranslate()
            except Exception:
                pass

        if self._tutorial is not None and self._tutorial.winfo_exists():
            self._tutorial.retranslate()

        self.refresh_title()

    def set_language(self, code: str) -> None:
        if code == get_language():
            return
        set_language(code)
        self.cfg["language"] = code
        if self.cfg.get("remember", True):
            save_config(self.cfg)
        self.retranslate()

    def refresh_title(self) -> None:
        base = tr("app.title")
        log = self.chat_page.current_log
        if log and log.name:
            self.root.title(f"{base}  ·  {log.name}")
        else:
            self.root.title(base)

    # ------------------------------------------------------------------

    def _new_session(self) -> None:
        self.chat_page.new_session()

    def _clear_view(self) -> None:
        self.chat_page.clear_display()

    def open_settings(self) -> None:
        self.show_page("settings")

    def open_about(self) -> None:
        self.show_page("about")

    def open_tutorial(self) -> None:
        if self._tutorial is not None and self._tutorial.winfo_exists():
            self._tutorial.lift()
            self._tutorial.focus_set()
            return
        self._tutorial = TutorialWindow(self.root, self)
        self._tutorial.refresh_theme(self.theme)

    # ------------------------------------------------------------------

    def _poll_global_queue(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "tb_test_ok":
                    from tkinter import messagebox
                    messagebox.showinfo(
                        tr("cs.test_ok"),
                        tr("cs.test_ok_body", reply=str(payload)),
                        parent=self.root)
                elif kind == "tb_test_err":
                    from tkinter import messagebox
                    messagebox.showerror(
                        tr("cs.test_fail"),
                        tr("cs.test_fail_body", error=str(payload)),
                        parent=self.root)
                elif kind == "cs_test_ok":
                    dlg = self.chat_settings_dialog
                    if dlg is not None:
                        try:
                            dlg.restore_test_button()
                            from tkinter import messagebox
                            messagebox.showinfo(
                                tr("cs.test_ok"),
                                tr("cs.test_ok_body", reply=str(payload)),
                                parent=dlg)
                        except Exception:
                            pass
                elif kind == "cs_test_err":
                    dlg = self.chat_settings_dialog
                    if dlg is not None:
                        try:
                            dlg.restore_test_button()
                            from tkinter import messagebox
                            messagebox.showerror(
                                tr("cs.test_fail"),
                                tr("cs.test_fail_body", error=str(payload)),
                                parent=dlg)
                        except Exception:
                            pass
                else:
                    self.q.put((kind, payload))
                    break
        except queue.Empty:
            pass
        self.root.after(100, self._poll_global_queue)

    # ------------------------------------------------------------------

    def on_close(self) -> None:
        try:
            self.chat_page.stop_event.set()
            if self.chat_page.client is not None:
                self.chat_page.client.cancel()
        except Exception:
            pass
        self.root.destroy()


# --------------------------------------------------------------------- 启动

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
    root.geometry("1000x700")
    root.minsize(680, 520)
    App(root)
    root.mainloop()