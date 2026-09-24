# ai_chat/chat_settings.py
"""聊天设置弹窗：API / 对话参数 / 联网搜索 / 聊天优化（带滚动）。"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from .formatting import estimate_messages_tokens
from .i18n import tr
from .keys import get_ai_key, get_search_key, set_ai_key, set_search_key
from .providers import PROVIDERS, by_name, get_provider
from .search import SEARCH_PROVIDERS
from .widgets import (Card, Divider, FlatButton, FlatCheck, FlatCombo,
                      FlatEntry, FlatText, apply_theme_to_tree)

SEARCH_LABELS = {
    "tavily": "Tavily",
    "serper": "Serper",
    "brave": "Brave Search",
    "bing": "Bing (Azure)",
    "searxng": "SearXNG",
    "duckduckgo": "DuckDuckGo",
    "custom": "自定义 / Custom",
}


class ChatSettingsDialog(tk.Toplevel):
    def __init__(self, parent, app, on_saved) -> None:
        super().__init__(parent)
        self.app = app
        self.cfg = dict(app.cfg)
        self.keys = {
            "ai": dict(app.keys.get("ai", {})),
            "search": dict(app.keys.get("search", {})),
        }
        self.on_saved = on_saved
        self.theme = app.theme

        self.title(tr("cs.title"))
        self.transient(parent)
        self.configure(bg=self.theme["bg"], padx=0, pady=0)
        self.resizable(True, True)
        self.minsize(460, 420)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._build()
        self.load_values()
        self._center(parent)
        self.grab_set()

        # 鼠标滚轮：只在本窗口生效
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind("<Destroy>", self._on_destroy)

    # ------------------------------------------------------------------
    # 布局：外层 + 滚动区 + 固定按钮栏

    def _build(self) -> None:
        outer = tk.Frame(self, bg=self.theme["bg"])
        outer.pack(fill=tk.BOTH, expand=True)

        # ---------- 滚动区 ----------
        scroll_wrap = tk.Frame(outer, bg=self.theme["bg"])
        scroll_wrap.pack(fill=tk.BOTH, expand=True, padx=16, pady=(14, 0))

        self._canvas = tk.Canvas(
            scroll_wrap, bg=self.theme["bg"],
            highlightthickness=0, bd=0,
            width=540, height=520)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._scrollbar = tk.Scrollbar(
            scroll_wrap, orient=tk.VERTICAL, command=self._canvas.yview,
            bd=0, width=10, relief=tk.FLAT,
            troughcolor=self.theme["bg"],
            bg=self.theme["scrollbar"],
            activebackground=self.theme["scrollbar_hl"],
        )
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        # inner 里放所有可滚动内容
        self.inner = tk.Frame(self._canvas, bg=self.theme["bg"])
        self._inner_window = self._canvas.create_window(
            (0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        body = self.inner

        # ---------- API 选项 ----------
        self._add_section(body, "cs.group_api")
        self._build_api_section(body)

        # ---------- 对话参数 ----------
        self._add_section(body, "cs.group_dialog")
        self._build_dialog_section(body)

        # ---------- 联网搜索 ----------
        self._add_section(body, "cs.group_search")
        self._build_search_section(body)

        # ---------- 本地办公 ----------
        self._add_section(body, "cs.group_agent")
        self._build_agent_section(body)

        # ---------- AI 眼睛 ----------
        self._add_section(body, "cs.group_vision")
        self._build_vision_section(body)

        # ---------- 聊天优化 ----------
        self._add_section(body, "cs.group_opt")
        self._build_optimize_section(body)

        # ---------- 底部固定按钮栏 ----------
        bar_wrap = tk.Frame(outer, bg=self.theme["bg"])
        bar_wrap.pack(fill=tk.X, padx=16, pady=(6, 14))
        Divider(bar_wrap, self.theme).pack(fill=tk.X, pady=(0, 10))

        bar = tk.Frame(bar_wrap, bg=self.theme["bg"])
        bar.pack(fill=tk.X)

        self.btn_test = FlatButton(bar, text=tr("cs.test"),
                                   command=self._do_test, theme=self.theme)
        self.btn_test.pack(side=tk.LEFT)

        self.btn_save = FlatButton(bar, text=tr("cs.save"),
                                   command=self._do_save,
                                   theme=self.theme, kind="accent")
        self.btn_save.pack(side=tk.RIGHT)

        self.btn_cancel = FlatButton(bar, text=tr("cs.cancel"),
                                     command=self.destroy, theme=self.theme)
        self.btn_cancel.pack(side=tk.RIGHT, padx=(0, 8))

    # ------------------------------------------------------------------
    # 滚动相关

    def _on_inner_configure(self, _event=None) -> None:
        try:
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        except tk.TclError:
            pass

    def _on_canvas_configure(self, event) -> None:
        # inner 宽度跟随 canvas，这样各控件 stretch 正确
        try:
            self._canvas.itemconfigure(self._inner_window, width=event.width)
        except tk.TclError:
            pass

    def _on_destroy(self, event) -> None:
        if event.widget is self:
            try:
                self.unbind_all("<MouseWheel>")
            except tk.TclError:
                pass

    def _on_mousewheel(self, event) -> None:
        """只在鼠标位于本窗口时滚动本窗口。"""
        if not self.winfo_exists():
            return
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return
        if widget is None:
            return

        w = widget
        while w is not None:
            if w is self:
                try:
                    self._canvas.yview_scroll(
                        int(-1 * (event.delta / 120)), "units")
                except tk.TclError:
                    pass
                return
            try:
                w = w.master
            except Exception:
                return

    # ------------------------------------------------------------------
    # section 标题

    def _add_section(self, parent, key: str) -> None:
        lbl = tk.Label(parent, text=tr(key), font=("", 10, "bold"),
                       bg=self.theme["bg"], fg=self.theme["accent"],
                       anchor="w")
        lbl._theme_role = "section"
        lbl.pack(fill=tk.X, pady=(10, 4))
        Divider(parent, self.theme).pack(fill=tk.X, pady=(0, 8))

    # ------------------------------------------------------------------
    # API 选项

    def _build_api_section(self, parent) -> None:
        grid = tk.Frame(parent, bg=self.theme["bg"])
        grid.pack(fill=tk.X)
        grid.columnconfigure(1, weight=1)

        self.v_provider = tk.StringVar()
        row = self._row(grid, 0, "cs.preset")
        self.cb_preset = FlatCombo(row, self.theme,
                                   values=[p.name for p in PROVIDERS],
                                   variable=self.v_provider,
                                   command=self._on_preset, width=24)
        self.cb_preset.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.v_url = tk.StringVar()
        row = self._row(grid, 1, "cs.base_url")
        self.e_url = FlatEntry(row, self.theme, textvariable=self.v_url)
        self.e_url.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        self.v_key = tk.StringVar()
        row = self._row(grid, 2, "cs.api_key")
        self.e_key = FlatEntry(row, self.theme, textvariable=self.v_key,
                               show="*")
        self.e_key.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        self.v_show = tk.BooleanVar(value=False)
        chk = FlatCheck(row, self.theme, text=tr("cs.show"),
                        variable=self.v_show, command=self._toggle_show)
        chk.pack(side=tk.LEFT, padx=(8, 0))

        self.v_model = tk.StringVar()
        row = self._row(grid, 3, "cs.model")
        self.cb_model = FlatCombo(row, self.theme, values=[],
                                  variable=self.v_model, width=24)
        self.cb_model.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_dialog_section(self, parent) -> None:
        grid = tk.Frame(parent, bg=self.theme["bg"])
        grid.pack(fill=tk.X)
        grid.columnconfigure(1, weight=1)

        self.v_temp = tk.StringVar(value="0.7")
        row = self._row(grid, 0, "cs.temperature")
        self.e_temp = FlatEntry(row, self.theme, textvariable=self.v_temp,
                                width=8)
        self.e_temp.pack(side=tk.LEFT, ipady=3)

        self.v_ctx = tk.StringVar(value="20")
        row = self._row(grid, 1, "cs.context")
        self.e_ctx = FlatEntry(row, self.theme, textvariable=self.v_ctx,
                               width=8)
        self.e_ctx.pack(side=tk.LEFT, ipady=3)

        self.v_timeout = tk.StringVar(value="120")
        row = self._row(grid, 2, "cs.timeout")
        self.e_timeout = FlatEntry(row, self.theme,
                                   textvariable=self.v_timeout, width=8)
        self.e_timeout.pack(side=tk.LEFT, ipady=3)

        self.lbl_token = tk.Label(grid, text="", bg=self.theme["bg"],
                                  fg=self.theme["hint_color"],
                                  font=("", 9), anchor="w")
        self.lbl_token._theme_role = "hint"
        self.lbl_token.grid(row=3, column=0, columnspan=2,
                            sticky="w", pady=(6, 0))

        self.v_proxy = tk.StringVar()
        row = self._row(grid, 4, "cs.proxy")
        self.e_proxy = FlatEntry(row, self.theme, textvariable=self.v_proxy)
        self.e_proxy.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        lbl = tk.Label(grid, text=tr("cs.system_prompt"),
                       bg=self.theme["bg"], fg=self.theme["fg"],
                       anchor="w")
        lbl.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 2))

        self.t_sys = FlatText(grid, self.theme, height=3, width=50,
                              font=("", 10))
        self.t_sys.grid(row=6, column=0, columnspan=2,
                        sticky="ew", pady=(0, 4))

        self.v_stream = tk.BooleanVar(value=True)
        chk = FlatCheck(grid, self.theme, text=tr("cs.stream"),
                        variable=self.v_stream)
        chk.grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _build_search_section(self, parent) -> None:
        grid = tk.Frame(parent, bg=self.theme["bg"])
        grid.pack(fill=tk.X)
        grid.columnconfigure(1, weight=1)

        self.v_search_on = tk.BooleanVar(value=False)
        chk = FlatCheck(grid, self.theme, text=tr("cs.search_on"),
                        variable=self.v_search_on)
        chk.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.v_sp = tk.StringVar()
        row = self._row(grid, 1, "cs.search_prov")
        self.cb_sp = FlatCombo(row, self.theme,
                               values=[SEARCH_LABELS[p]
                                       for p in SEARCH_PROVIDERS],
                               variable=self.v_sp,
                               command=self._on_search_provider, width=22)
        self.cb_sp.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.v_skey = tk.StringVar()
        row = self._row(grid, 2, "cs.search_key")
        self.e_skey = FlatEntry(row, self.theme, textvariable=self.v_skey,
                                show="*")
        self.e_skey.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        self.v_send = tk.StringVar()
        row = self._row(grid, 3, "cs.search_ep")
        self.e_send = FlatEntry(row, self.theme, textvariable=self.v_send)
        self.e_send.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        self.v_smax = tk.StringVar(value="5")
        row = self._row(grid, 4, "cs.search_max")
        self.e_smax = FlatEntry(row, self.theme, textvariable=self.v_smax,
                                width=8)
        self.e_smax.pack(side=tk.LEFT, ipady=3)

    def _build_optimize_section(self, parent) -> None:
        grid = tk.Frame(parent, bg=self.theme["bg"])
        grid.pack(fill=tk.X)
        grid.columnconfigure(1, weight=1)

        self.v_soften = tk.StringVar()
        row = self._row(grid, 0, "cs.soften")
        self.cb_soften = FlatCombo(
            row, self.theme,
            values=[tr("cs.soften.%d" % lv) for lv in (0, 1, 2, 3)],
            variable=self.v_soften, width=24)
        self.cb_soften.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # ------------------------------------------------------------------
    # 本地办公（Agent）

    def _build_agent_section(self, parent) -> None:
        grid = tk.Frame(parent, bg=self.theme["bg"])
        grid.pack(fill=tk.X)

        self.v_agent_on = tk.BooleanVar(value=False)
        FlatCheck(grid, self.theme, text=tr("cs.agent_on"),
                  variable=self.v_agent_on).pack(fill=tk.X, pady=(0, 4))

        # 工作区路径（强制锁死）
        path_row = tk.Frame(grid, bg=self.theme["bg"])
        path_row.pack(fill=tk.X, pady=2)
        tk.Label(path_row, text=tr("cs.workspace"), bg=self.theme["bg"],
                 fg=self.theme["fg"], width=14, anchor="w").pack(side=tk.LEFT)
        self.v_workspace = tk.StringVar()
        FlatEntry(path_row, self.theme,
                  textvariable=self.v_workspace).pack(side=tk.LEFT,
                  fill=tk.X, expand=True)
        FlatButton(path_row, text=tr("cs.browse"), theme=self.theme,
                   command=self._browse_workspace,
                   padx=10).pack(side=tk.LEFT, padx=(6, 0))

        self.v_agent_files = tk.BooleanVar(value=True)
        FlatCheck(grid, self.theme, text=tr("cs.agent_files"),
                  variable=self.v_agent_files).pack(fill=tk.X, pady=(4, 0))
        self.v_agent_shell = tk.BooleanVar(value=False)
        FlatCheck(grid, self.theme, text=tr("cs.agent_shell"),
                  variable=self.v_agent_shell).pack(fill=tk.X)
        self.v_agent_confirm = tk.BooleanVar(value=True)
        FlatCheck(grid, self.theme, text=tr("cs.agent_confirm"),
                  variable=self.v_agent_confirm).pack(fill=tk.X)

        wl_row = tk.Frame(grid, bg=self.theme["bg"])
        wl_row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(wl_row, text=tr("cs.shell_wl"), bg=self.theme["bg"],
                 fg=self.theme["fg"], width=14, anchor="w").pack(side=tk.LEFT)
        self.v_shell_wl = tk.StringVar()
        FlatEntry(wl_row, self.theme,
                  textvariable=self.v_shell_wl).pack(side=tk.LEFT,
                  fill=tk.X, expand=True)

    def _browse_workspace(self) -> None:
        from tkinter import filedialog
        start = self.v_workspace.get() or None
        try:
            chosen = filedialog.askdirectory(parent=self, initialdir=start)
        except Exception:
            chosen = filedialog.askdirectory(parent=self)
        if chosen:
            self.v_workspace.set(chosen)

    # ------------------------------------------------------------------
    # AI 眼睛

    def _build_vision_section(self, parent) -> None:
        grid = tk.Frame(parent, bg=self.theme["bg"])
        grid.pack(fill=tk.X)

        self.v_vision_on = tk.BooleanVar(value=True)
        FlatCheck(grid, self.theme, text=tr("cs.vision_on"),
                  variable=self.v_vision_on).pack(fill=tk.X)
        tip = tk.Label(grid, text=tr("cs.vision_tip"), bg=self.theme["bg"],
                       fg=self.theme["hint_color"], font=("", 9),
                       anchor="w", justify=tk.LEFT, wraplength=480)
        tip._theme_role = "hint"
        tip.pack(fill=tk.X, pady=(4, 0))

    # ------------------------------------------------------------------

    def _row(self, grid, row_index: int, label_key: str) -> tk.Frame:
        lbl = tk.Label(grid, text=tr(label_key), bg=self.theme["bg"],
                       fg=self.theme["fg"], anchor="w")
        lbl.grid(row=row_index, column=0, sticky="w", padx=(0, 12), pady=4)
        holder = tk.Frame(grid, bg=self.theme["bg"])
        holder.grid(row=row_index, column=1, sticky="ew", pady=4)
        return holder

    # ------------------------------------------------------------------

    def _toggle_show(self) -> None:
        self.e_key.configure(show="" if self.v_show.get() else "*")
        self.e_skey.configure(show="" if self.v_show.get() else "*")

    def _on_preset(self, name: str) -> None:
        p = by_name(name)
        if p.base_url:
            self.v_url.set(p.base_url)
        self.cb_model.set_values(list(p.models))
        if p.models:
            self.v_model.set(p.models[0])
        self.v_key.set(get_ai_key(self.keys, p.id))

    def _on_search_provider(self, label: str) -> None:
        sid = "duckduckgo"
        for k, v in SEARCH_LABELS.items():
            if v == label:
                sid = k
                break
        self.v_skey.set(get_search_key(self.keys, sid))

    # ------------------------------------------------------------------

    def load_values(self) -> None:
        cfg = self.cfg
        pid = cfg.get("provider") or "custom"
        provider = get_provider(pid)
        self.v_provider.set(provider.name)
        self.v_url.set(cfg.get("base_url", ""))
        self.v_key.set(get_ai_key(self.keys, provider.id))

        # 模型兜底：cfg 里没有或为空时，用 provider 的第一个
        model = (cfg.get("model") or "").strip()
        if not model and provider.models:
            model = provider.models[0]
        self.v_model.set(model)
        self.cb_model.set_values(list(provider.models))

        self.v_temp.set(str(cfg.get("temperature", 0.7)))
        self.v_ctx.set(str(cfg.get("max_context", 20)))
        self.v_timeout.set(str(cfg.get("timeout", 120)))
        self.v_proxy.set(cfg.get("proxy", ""))
        self.v_stream.set(bool(cfg.get("stream", True)))

        self.t_sys.delete("1.0", tk.END)
        self.t_sys.insert("1.0", cfg.get("system_prompt", ""))

        search = cfg.get("search", {})
        self.v_search_on.set(bool(search.get("enabled", False)))
        sp = search.get("provider", "duckduckgo")
        if sp not in SEARCH_LABELS:
            sp = "duckduckgo"
        self.v_sp.set(SEARCH_LABELS.get(sp, SEARCH_LABELS["duckduckgo"]))
        self.v_skey.set(get_search_key(self.keys, sp))
        self.v_send.set(search.get("endpoint", ""))
        self.v_smax.set(str(search.get("max_results", 5)))

        level = int(cfg.get("soften_level", 2))
        self.v_soften.set(tr("cs.soften.%d" % level))

        # 本地办公
        agent = cfg.get("agent", {})
        self.v_agent_on.set(bool(agent.get("enabled", False)))
        self.v_workspace.set(agent.get("workspace_dir", ""))
        self.v_agent_files.set(bool(agent.get("enable_files", True)))
        self.v_agent_shell.set(bool(agent.get("enable_shell", False)))
        self.v_agent_confirm.set(bool(agent.get("require_confirm", True)))
        self.v_shell_wl.set(agent.get("shell_whitelist", ""))

        # AI 眼睛
        vision = cfg.get("vision", {})
        self.v_vision_on.set(bool(vision.get("enabled", True)))

        self._update_token_estimate()

    def _update_token_estimate(self) -> None:
        try:
            msgs = list(self.app.chat_page.history)
        except Exception:
            msgs = []
        n = estimate_messages_tokens(msgs)
        try:
            self.lbl_token.configure(text=tr("cs.token_est", n=n))
        except tk.TclError:
            pass

    # ------------------------------------------------------------------

    def _collect(self):
        try:
            temperature = float(self.v_temp.get())
            timeout = int(float(self.v_timeout.get()))
            max_context = int(float(self.v_ctx.get()))
            max_results = int(float(self.v_smax.get()))
        except (TypeError, ValueError):
            messagebox.showwarning(tr("cs.title"), tr("cs.bad_number"),
                                   parent=self)
            return None

        temperature = max(0.0, min(2.0, temperature))
        timeout = max(10, min(600, timeout))
        max_context = max(1, min(200, max_context))
        max_results = max(1, min(10, max_results))

        p = by_name(self.v_provider.get())
        sp_label = self.v_sp.get()
        sp_id = "duckduckgo"
        for k, v in SEARCH_LABELS.items():
            if v == sp_label:
                sp_id = k
                break

        soften = 2
        for lv in (0, 1, 2, 3):
            if self.v_soften.get() == tr("cs.soften.%d" % lv):
                soften = lv
                break

        new_keys = {
            "ai": dict(self.keys.get("ai", {})),
            "search": dict(self.keys.get("search", {})),
        }
        set_ai_key(new_keys, p.id, self.v_key.get())
        set_search_key(new_keys, sp_id, self.v_skey.get())

        cfg = dict(self.cfg)
        cfg.update({
            "provider": p.id,
            "base_url": self.v_url.get().strip(),
            "model": self.v_model.get().strip(),
            "temperature": temperature,
            "timeout": timeout,
            "max_context": max_context,
            "proxy": self.v_proxy.get().strip(),
            "stream": bool(self.v_stream.get()),
            "system_prompt": self.t_sys.get("1.0", tk.END).strip(),
            "soften_level": soften,
            "search": {
                "enabled": bool(self.v_search_on.get()),
                "provider": sp_id,
                "endpoint": self.v_send.get().strip(),
                "max_results": max_results,
            },
            "agent": {
                "enabled": bool(self.v_agent_on.get()),
                "workspace_dir": self.v_workspace.get().strip(),
                "enable_files": bool(self.v_agent_files.get()),
                "enable_shell": bool(self.v_agent_shell.get()),
                "shell_whitelist": self.v_shell_wl.get().strip(),
                "require_confirm": bool(self.v_agent_confirm.get()),
                "max_tool_turns": int(self.cfg.get("agent", {}).get(
                    "max_tool_turns", 8)),
            },
            "vision": {
                "enabled": bool(self.v_vision_on.get()),
            },
        })
        return cfg, new_keys

    # ------------------------------------------------------------------

    def _do_test(self) -> None:
        result = self._collect()
        if result is None:
            return
        cfg, keys = result
        provider = get_provider(cfg.get("provider", "custom"))
        ai_key = get_ai_key(keys, provider.id)
        if not ai_key:
            messagebox.showwarning(tr("cs.test"), tr("cs.need_key"),
                                   parent=self)
            return
        if not cfg["base_url"] or not cfg["model"]:
            messagebox.showwarning(tr("cs.test"), tr("cs.need_url"),
                                   parent=self)
            return

        self.btn_test.set_enabled(False)
        self.btn_test.set_text(tr("cs.testing"))

        client = self.app.make_client(cfg, keys)

        def run() -> None:
            try:
                reply = client.test()
                self.app.q.put(("cs_test_ok", reply))
            except Exception as exc:
                self.app.q.put(("cs_test_err", str(exc)))

        threading.Thread(target=run, daemon=True).start()

    def restore_test_button(self) -> None:
        try:
            self.btn_test.set_enabled(True)
            self.btn_test.set_text(tr("cs.test"))
        except tk.TclError:
            pass

    def _do_save(self) -> None:
        result = self._collect()
        if result is None:
            return
        cfg, keys = result
        self.on_saved(cfg, keys)
        self.destroy()

    # ------------------------------------------------------------------

    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme
        self.configure(bg=theme["bg"])
        apply_theme_to_tree(self, theme)

        # canvas 和 scrollbar 是特殊控件，额外刷一遍保证准确
        try:
            self._canvas.configure(bg=theme["bg"])
            self._scrollbar.configure(
                bg=theme["scrollbar"],
                troughcolor=theme["bg"],
                activebackground=theme["scrollbar_hl"],
            )
        except tk.TclError:
            pass

    # ------------------------------------------------------------------

    def _center(self, parent) -> None:
        self.update_idletasks()

        # 用可滚动内容（inner）的请求尺寸推算窗口大小
        inner_w = self.inner.winfo_reqwidth()
        inner_h = self.inner.winfo_reqheight()

        req_w = inner_w + 32 + 12        # 左右内边距 + 滚动条
        req_h = inner_h + 14 + 62 + 14   # 上内边距 + 底部按钮栏 + 下内边距

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        max_w = int(screen_w * 0.9)
        max_h = int(screen_h * 0.85)

        w = max(560, min(req_w, max_w))
        h = max(520, min(req_h, max_h))

        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()

        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 3)
        self.geometry("%dx%d+%d+%d" % (w, h, x, y))