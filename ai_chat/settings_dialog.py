# ai_chat/settings_dialog.py
"""设置窗口（3 分页，跟随主题）。"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .i18n import tr
from .keys import get_ai_key, get_search_key, set_ai_key, set_search_key
from .providers import PROVIDERS, get_provider, guess_provider
from .search import SEARCH_PROVIDERS

SEARCH_LABELS = {
    "tavily": "Tavily",
    "serper": "Serper",
    "brave": "Brave Search",
    "bing": "Bing (Azure)",
    "searxng": "SearXNG",
    "duckduckgo": "DuckDuckGo",
}

THEME_IDS = ("light", "dark")


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, cfg, keys, fonts, theme_dict,
                 on_saved, make_client, queue) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.keys = keys
        self.fonts = fonts
        self.theme = theme_dict
        self.on_saved = on_saved
        self.make_client = make_client
        self.q = queue

        self.title(tr("settings.title"))
        self.transient(parent)
        self.resizable(False, False)
        self.configure(padx=14, pady=12, bg=theme_dict["bg"])
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._labels: list[tuple[ttk.Label, str]] = []

        self._build()
        self.retranslate()
        self._center(parent)
        self.grab_set()

    def _build(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_api = ttk.Frame(self.notebook, padding=14)
        self.tab_chat = ttk.Frame(self.notebook, padding=14)
        self.tab_search = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(self.tab_api, text="")
        self.notebook.add(self.tab_chat, text="")
        self.notebook.add(self.tab_search, text="")

        self._build_api_tab()
        self._build_chat_tab()
        self._build_search_tab()

        buttons = ttk.Frame(self, padding=(0, 12, 0, 0))
        buttons.pack(fill=tk.X)
        self.btn_test = ttk.Button(buttons, text=tr("settings.test"),
                                   command=self._do_test)
        self.btn_test.pack(side=tk.LEFT)
        self.btn_save = ttk.Button(buttons, text=tr("settings.save"),
                                   command=self._do_save)
        self.btn_save.pack(side=tk.RIGHT)
        self.btn_cancel = ttk.Button(buttons, text=tr("settings.cancel"),
                                     command=self.destroy)
        self.btn_cancel.pack(side=tk.RIGHT, padx=(0, 8))

    def _build_api_tab(self) -> None:
        grid = self.tab_api
        grid.columnconfigure(1, weight=1)

        self.v_provider = tk.StringVar()
        names = [p.name for p in PROVIDERS]
        self.cb_preset = ttk.Combobox(grid, textvariable=self.v_provider,
                                      values=names, state="readonly", width=32)
        self._add_row(grid, 0, "settings.preset", self.cb_preset)
        self.cb_preset.bind("<<ComboboxSelected>>", self._on_preset)

        self.v_url = tk.StringVar()
        self._add_row(grid, 1, "settings.base_url",
                      ttk.Entry(grid, textvariable=self.v_url, width=54))

        key_box = ttk.Frame(grid)
        self.v_key = tk.StringVar()
        self.e_key = ttk.Entry(key_box, textvariable=self.v_key, show="*", width=44)
        self.e_key.pack(side=tk.LEFT)
        self.v_show_key = tk.BooleanVar(value=False)
        self.chk_show_key = ttk.Checkbutton(
            key_box, text=tr("settings.show"), variable=self.v_show_key,
            command=lambda: self.e_key.configure(
                show="" if self.v_show_key.get() else "*"))
        self.chk_show_key.pack(side=tk.LEFT, padx=(8, 0))
        self._add_row(grid, 2, "settings.api_key", key_box)

        self.v_model = tk.StringVar()
        self.cb_model = ttk.Combobox(grid, textvariable=self.v_model, width=52)
        self._add_row(grid, 3, "settings.model", self.cb_model)

        self.v_temp = tk.StringVar()
        self._add_row(grid, 4, "settings.temperature", ttk.Spinbox(
            grid, from_=0.0, to=2.0, increment=0.1,
            textvariable=self.v_temp, width=10, format="%.1f"))

        self.v_timeout = tk.StringVar()
        self._add_row(grid, 5, "settings.timeout", ttk.Spinbox(
            grid, from_=10, to=600, increment=10,
            textvariable=self.v_timeout, width=10))

        self.v_proxy = tk.StringVar()
        self._add_row(grid, 6, "settings.proxy",
                      ttk.Entry(grid, textvariable=self.v_proxy, width=54))

    def _build_chat_tab(self) -> None:
        grid = self.tab_chat
        grid.columnconfigure(0, weight=1)

        self.lbl_sys = ttk.Label(grid, text="")
        self.lbl_sys.grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
        self.t_sys = tk.Text(grid, height=5, width=64, font=self.fonts["base"],
                             relief=tk.SOLID, borderwidth=1, wrap=tk.WORD,
                             bg=self.theme["input_bg"], fg=self.theme["input_fg"],
                             insertbackground=self.theme["input_fg"])
        self.t_sys.grid(row=1, column=0, sticky=tk.EW, pady=(0, 12))

        # 主题
        row_theme = ttk.Frame(grid)
        row_theme.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        self.lbl_theme = ttk.Label(row_theme, text="")
        self.lbl_theme.pack(side=tk.LEFT, padx=(0, 10))
        self.v_theme = tk.StringVar()
        self.cb_theme = ttk.Combobox(row_theme, textvariable=self.v_theme,
                                     state="readonly", width=12,
                                     values=self._theme_labels())
        self.cb_theme.pack(side=tk.LEFT)

        # 上下文条数
        row_ctx = ttk.Frame(grid)
        row_ctx.grid(row=3, column=0, sticky=tk.W, pady=(0, 10))
        self.lbl_ctx = ttk.Label(row_ctx, text="")
        self.lbl_ctx.pack(side=tk.LEFT, padx=(0, 10))
        self.v_ctx = tk.StringVar()
        ttk.Spinbox(row_ctx, from_=1, to=200, increment=1, width=6,
                    textvariable=self.v_ctx).pack(side=tk.LEFT)
        self.lbl_ctx_hint = ttk.Label(
            row_ctx, text="", font=self.fonts["small"],
            foreground=self.theme["hint_color"])
        self.lbl_ctx_hint.pack(side=tk.LEFT, padx=(10, 0))

        # 流式 / 记住
        opts = ttk.Frame(grid)
        opts.grid(row=4, column=0, sticky=tk.W, pady=(6, 10))
        self.v_stream = tk.BooleanVar()
        self.chk_stream = ttk.Checkbutton(
            opts, text=tr("settings.stream"), variable=self.v_stream)
        self.chk_stream.pack(anchor=tk.W)

        self.v_remember = tk.BooleanVar()
        self.chk_remember = ttk.Checkbutton(
            opts, text=tr("settings.remember"), variable=self.v_remember)
        self.chk_remember.pack(anchor=tk.W, pady=(6, 0))

        # Markdown 精简
        row_md = ttk.Frame(grid)
        row_md.grid(row=5, column=0, sticky=tk.W, pady=(6, 0))
        self.lbl_soften = ttk.Label(row_md, text="")
        self.lbl_soften.pack(side=tk.LEFT, padx=(0, 10))
        self.v_soften = tk.StringVar()
        self.cb_soften = ttk.Combobox(row_md, textvariable=self.v_soften,
                                      state="readonly", width=34,
                                      values=self._soften_labels())
        self.cb_soften.pack(side=tk.LEFT)

        # 字号
        row_font = ttk.Frame(grid)
        row_font.grid(row=6, column=0, sticky=tk.W, pady=(12, 0))
        self.lbl_font = ttk.Label(row_font, text="")
        self.lbl_font.pack(side=tk.LEFT, padx=(0, 10))
        self.v_font = tk.StringVar()
        ttk.Spinbox(row_font, from_=9, to=20, increment=1, width=6,
                    textvariable=self.v_font).pack(side=tk.LEFT)

    @staticmethod
    def _soften_labels() -> list[str]:
        return [tr("settings.soften.%d" % lv) for lv in (0, 1, 2, 3)]

    @staticmethod
    def _theme_labels() -> list[str]:
        return [tr("settings.theme.light"), tr("settings.theme.dark")]

    def _build_search_tab(self) -> None:
        grid = self.tab_search
        grid.columnconfigure(1, weight=1)

        self.v_search_on = tk.BooleanVar()
        self.chk_search_on = ttk.Checkbutton(
            grid, text=tr("settings.search_enable"), variable=self.v_search_on)
        self.chk_search_on.grid(row=0, column=0, columnspan=2,
                                sticky=tk.W, pady=(0, 10))

        self.v_sp = tk.StringVar()
        self.cb_sp = ttk.Combobox(
            grid, textvariable=self.v_sp, state="readonly", width=30,
            values=[SEARCH_LABELS[p] for p in SEARCH_PROVIDERS])
        self._add_row(grid, 1, "settings.search_provider", self.cb_sp)
        self.cb_sp.bind("<<ComboboxSelected>>", self._on_search_provider)

        self.v_skey = tk.StringVar()
        self._add_row(grid, 2, "settings.search_key",
                      ttk.Entry(grid, textvariable=self.v_skey, show="*", width=52))

        self.v_send = tk.StringVar()
        self._add_row(grid, 3, "settings.search_endpoint",
                      ttk.Entry(grid, textvariable=self.v_send, width=52))

        self.v_smax = tk.StringVar()
        self._add_row(grid, 4, "settings.search_max", ttk.Spinbox(
            grid, from_=1, to=10, increment=1, width=10,
            textvariable=self.v_smax))

        self.lbl_search_hint = ttk.Label(
            grid, text="", font=self.fonts["small"],
            foreground=self.theme["hint_color"],
            justify=tk.LEFT, wraplength=520)
        self.lbl_search_hint.grid(row=5, column=0, columnspan=2,
                                  sticky=tk.W, pady=(14, 0))

    def _add_row(self, parent, row: int, key: str, widget):
        label = ttk.Label(parent, text=tr(key))
        label.grid(row=row, column=0, sticky=tk.W, padx=(0, 12), pady=5)
        widget.grid(row=row, column=1, sticky=tk.EW, pady=5)
        self._labels.append((label, key))
        return widget

    def _on_preset(self, _event=None) -> None:
        name = self.v_provider.get()
        for p in PROVIDERS:
            if p.name == name:
                if p.base_url:
                    self.v_url.set(p.base_url)
                self.cb_model.configure(values=list(p.models))
                if p.models:
                    self.v_model.set(p.models[0])
                self.v_key.set(get_ai_key(self.keys, p.id))
                break

    def _on_search_provider(self, _event=None) -> None:
        label = self.v_sp.get()
        sid = "duckduckgo"
        for k, v in SEARCH_LABELS.items():
            if v == label:
                sid = k
                break
        self.v_skey.set(get_search_key(self.keys, sid))

    def retranslate(self) -> None:
        self.title(tr("settings.title"))

        self.notebook.tab(0, text="  " + tr("settings.tab.api") + "  ")
        self.notebook.tab(1, text="  " + tr("settings.tab.chat") + "  ")
        self.notebook.tab(2, text="  " + tr("settings.tab.search") + "  ")

        self.btn_test.configure(text=tr("settings.test"))
        self.btn_save.configure(text=tr("settings.save"))
        self.btn_cancel.configure(text=tr("settings.cancel"))

        self.chk_show_key.configure(text=tr("settings.show"))
        self.chk_stream.configure(text=tr("settings.stream"))
        self.chk_remember.configure(text=tr("settings.remember"))
        self.chk_search_on.configure(text=tr("settings.search_enable"))

        for label, key in self._labels:
            label.configure(text=tr(key))

        self.lbl_sys.configure(text=tr("settings.system_prompt"))
        self.lbl_theme.configure(text=tr("settings.theme"))
        self.lbl_ctx.configure(text=tr("settings.max_context"))
        self.lbl_ctx_hint.configure(text=tr("settings.max_context_hint"))
        self.lbl_soften.configure(text=tr("settings.soften"))
        self.lbl_font.configure(text=tr("settings.font_size"))
        self.lbl_search_hint.configure(text=tr("settings.search_hint"))

        new_labels = self._soften_labels()
        current = self.v_soften.get()
        self.cb_soften.configure(values=new_labels)
        if current not in new_labels:
            self.v_soften.set(new_labels[2])

        new_themes = self._theme_labels()
        cur_theme = self.v_theme.get()
        self.cb_theme.configure(values=new_themes)
        if cur_theme not in new_themes:
            self.v_theme.set(new_themes[0])

    def load_values(self) -> None:
        cfg = self.cfg

        pid = cfg.get("provider") or guess_provider(cfg.get("base_url", ""))
        provider = get_provider(pid)
        self.v_provider.set(provider.name)
        self.v_url.set(cfg.get("base_url", ""))
        self.v_key.set(get_ai_key(self.keys, provider.id))
        self.v_model.set(cfg.get("model", ""))
        self.cb_model.configure(values=list(provider.models))

        self.v_temp.set(str(cfg.get("temperature", 0.7)))
        self.v_timeout.set(str(cfg.get("timeout", 120)))
        self.v_proxy.set(cfg.get("proxy", ""))

        self.v_stream.set(bool(cfg.get("stream", True)))
        self.v_remember.set(bool(cfg.get("remember", True)))
        self.v_font.set(str(cfg.get("font_size", 11)))
        self.v_ctx.set(str(cfg.get("max_context", 20)))

        theme_id = cfg.get("theme", "light")
        labels = self._theme_labels()
        self.v_theme.set(labels[1] if theme_id == "dark" else labels[0])

        self.t_sys.delete("1.0", tk.END)
        self.t_sys.insert("1.0", cfg.get("system_prompt", ""))

        level = int(cfg.get("soften_level", 2))
        labels2 = self._soften_labels()
        self.v_soften.set(labels2[level] if 0 <= level < len(labels2) else labels2[2])

        search = cfg.get("search", {})
        self.v_search_on.set(bool(search.get("enabled", False)))
        sp = search.get("provider", "duckduckgo")
        self.v_sp.set(SEARCH_LABELS.get(sp, SEARCH_LABELS["duckduckgo"]))
        self.v_skey.set(get_search_key(self.keys, sp))
        self.v_send.set(search.get("endpoint", ""))
        self.v_smax.set(str(search.get("max_results", 5)))

    def _collect(self):
        try:
            temperature = float(self.v_temp.get())
            timeout = int(float(self.v_timeout.get()))
            font_size = int(float(self.v_font.get()))
            max_results = int(float(self.v_smax.get()))
            max_context = int(float(self.v_ctx.get()))
        except (TypeError, ValueError):
            messagebox.showwarning(tr("settings.title"), tr("settings.bad_number"),
                                   parent=self)
            return None

        temperature = max(0.0, min(2.0, temperature))
        timeout = max(10, min(600, timeout))
        font_size = max(9, min(20, font_size))
        max_results = max(1, min(10, max_results))
        max_context = max(1, min(200, max_context))

        provider_name = self.v_provider.get()
        pid = "custom"
        for p in PROVIDERS:
            if p.name == provider_name:
                pid = p.id
                break

        labels = self._soften_labels()
        try:
            soften = labels.index(self.v_soften.get())
        except ValueError:
            soften = 2

        sp_label = self.v_sp.get()
        sp_id = "duckduckgo"
        for key, label in SEARCH_LABELS.items():
            if label == sp_label:
                sp_id = key
                break

        theme_labels = self._theme_labels()
        theme_id = "dark" if self.v_theme.get() == theme_labels[1] else "light"

        new_keys = {
            "ai": dict(self.keys.get("ai", {})),
            "search": dict(self.keys.get("search", {})),
        }
        set_ai_key(new_keys, pid, self.v_key.get())
        set_search_key(new_keys, sp_id, self.v_skey.get())

        cfg = dict(self.cfg)
        cfg.update({
            "provider": pid,
            "base_url": self.v_url.get().strip(),
            "model": self.v_model.get().strip(),
            "temperature": temperature,
            "timeout": timeout,
            "proxy": self.v_proxy.get().strip(),
            "stream": bool(self.v_stream.get()),
            "remember": bool(self.v_remember.get()),
            "system_prompt": self.t_sys.get("1.0", tk.END).strip(),
            "soften_level": soften,
            "font_size": font_size,
            "max_context": max_context,
            "theme": theme_id,
            "search": {
                "enabled": bool(self.v_search_on.get()),
                "provider": sp_id,
                "endpoint": self.v_send.get().strip(),
                "max_results": max_results,
            },
        })
        return cfg, new_keys

    def _do_test(self) -> None:
        result = self._collect()
        if result is None:
            return
        cfg, keys = result
        provider = get_provider(cfg.get("provider", "custom"))
        ai_key = get_ai_key(keys, provider.id)

        if not ai_key:
            messagebox.showwarning(tr("settings.test"), tr("settings.need_key"),
                                   parent=self)
            return
        if not cfg["base_url"] or not cfg["model"]:
            messagebox.showwarning(tr("settings.test"), tr("settings.need_url_model"),
                                   parent=self)
            return

        self.btn_test.configure(state=tk.DISABLED, text=tr("settings.testing"))
        client = self.make_client(cfg, keys)

        def run() -> None:
            try:
                self.q.put(("test_ok", client.test()))
            except Exception as exc:
                self.q.put(("test_err", str(exc)))
            finally:
                self.q.put(("test_finished", None))

        threading.Thread(target=run, daemon=True).start()

    def restore_test_button(self) -> None:
        try:
            self.btn_test.configure(state=tk.NORMAL, text=tr("settings.test"))
        except tk.TclError:
            pass

    def _do_save(self) -> None:
        result = self._collect()
        if result is None:
            return
        cfg, keys = result
        self.on_saved(cfg, keys)
        self.destroy()

    def _center(self, parent) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        self.geometry("+%d+%d" % (
            px + max(0, (pw - w) // 2),
            py + max(0, (ph - h) // 3),
        ))