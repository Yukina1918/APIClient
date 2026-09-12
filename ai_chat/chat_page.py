# ai_chat/chat_page.py
"""聊天页：工具栏 + 聊天区 + 输入区 + 状态栏。"""
from __future__ import annotations

import threading
import time
import tkinter as tk

from .chat_settings import ChatSettingsDialog
from .client import APIError, ChatClient, NetworkError
from .formatting import soften_markdown
from .history import (ChatLog, DEFAULT_NAME, list_logs, load_log, make_title_from,
                      new_id, save_log)
from .i18n import tr
from .keys import get_ai_key, get_search_key
from .providers import get_provider
from .search import (SearchError, build_search_prompt, format_sources,
                     run_search)
from .widgets import (Divider, FlatButton, FlatCheck, FlatText,
                      apply_theme_to_tree)


class ChatPage(tk.Frame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, bg=app.theme["bg"])
        self.app = app
        self.theme = app.theme
        self.cfg = app.cfg
        self.keys = app.keys

        self.history: list[dict] = []
        self.current_log: ChatLog | None = None
        self.busy = False
        self.stop_event = threading.Event()
        self.client: ChatClient | None = None
        self._stream_start: str | None = None

        self._build()
        self._install_placeholder()
        self._poll_queue()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self._build_toolbar()
        self._build_chat_area()
        self._build_input_area()
        self._build_status_bar()

    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self, bg=self.theme["bg"])
        bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))

        self.btn_chat_settings = FlatButton(
            bar, text=tr("toolbar.chat_settings"),
            command=self.open_chat_settings, theme=self.theme)
        self.btn_chat_settings.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_new = FlatButton(bar, text=tr("toolbar.new"),
                                  command=self.new_session, theme=self.theme)
        self.btn_new.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_test = FlatButton(bar, text=tr("toolbar.test"),
                                   command=self.test_connection, theme=self.theme)
        self.btn_test.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_clear = FlatButton(bar, text=tr("toolbar.clear"),
                                    command=self.clear_display, theme=self.theme)
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 6))

        self.v_search = tk.BooleanVar(
            value=bool(self.app.cfg.get("search", {}).get("enabled")))
        self.chk_search = FlatCheck(
            bar, self.theme, text=tr("toolbar.search"),
            variable=self.v_search, command=self._on_search_toggle)
        self.chk_search.pack(side=tk.LEFT, padx=(8, 0))

        self.history_bar = FlatButton(
            bar, text=tr("toolbar.history"),
            command=self._show_history_menu, theme=self.theme)
        self.history_bar.pack(side=tk.RIGHT, padx=(8, 0))

        self.lbl_model = tk.Label(bar, text="", bg=self.theme["bg"],
                                  fg=self.theme["hint_color"], font=("", 9))
        self.lbl_model._theme_role = "hint"
        self.lbl_model.pack(side=tk.RIGHT, padx=(0, 12))

    def _build_chat_area(self) -> None:
        wrap = tk.Frame(self, bg=self.theme["bg"])
        wrap.grid(row=1, column=0, sticky="nsew", padx=10)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        self.chat = FlatText(wrap, self.theme, wrap=tk.WORD, state=tk.DISABLED,
                             font=self.app.f_base, padx=12, pady=10,
                             spacing1=1, spacing3=2)
        self.chat.grid(row=0, column=0, sticky="nsew")

        sb = tk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.chat.yview,
                          bd=0, width=10, relief=tk.FLAT,
                          troughcolor=self.theme["bg"],
                          bg=self.theme["scrollbar"],
                          activebackground=self.theme["scrollbar_hl"])
        self.chat.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")
        self._scrollbar = sb

        for tag, color_key, weight in (
            ("user", "user_color", "bold"),
            ("ai", "ai_color", "bold"),
            ("sys", "sys_color", "normal"),
            ("err", "err_color", "bold"),
            ("src", "src_color", "normal"),
        ):
            self.chat.tag_configure(
                tag, foreground=self.theme[color_key],
                font=(self.app.font_family, self.app.font_size, weight),
            )

    def _build_input_area(self) -> None:
        wrap = tk.Frame(self, bg=self.theme["bg"])
        wrap.grid(row=2, column=0, sticky="ew", padx=10, pady=(6, 4))
        wrap.columnconfigure(0, weight=1)

        self.input = FlatText(wrap, self.theme, height=4, wrap=tk.WORD,
                              font=self.app.f_input, padx=10, pady=8)
        self.input.grid(row=0, column=0, sticky="ew")
        self.input.bind("<Return>", self._on_enter)
        self.input.bind("<KP_Enter>", self._on_enter)

        btns = tk.Frame(wrap, bg=self.theme["bg"])
        btns.grid(row=0, column=1, sticky="ns", padx=(8, 0))

        self.btn_send = FlatButton(btns, text=tr("input.send"),
                                   command=self.on_send, theme=self.theme,
                                   kind="accent", padx=18, pady=8)
        self.btn_send.pack(side=tk.TOP, fill=tk.X)

        self.btn_stop = FlatButton(btns, text=tr("input.stop"),
                                   command=self.on_stop, theme=self.theme,
                                   padx=18, pady=8)
        self.btn_stop.pack(side=tk.TOP, fill=tk.X, pady=(6, 0))
        self.btn_stop.set_enabled(False)

        self.lbl_hint = tk.Label(wrap, text=tr("input.hint"),
                                 bg=self.theme["bg"],
                                 fg=self.theme["hint_color"],
                                 font=("", 9), anchor="w")
        self.lbl_hint._theme_role = "hint"
        self.lbl_hint.grid(row=1, column=0, columnspan=2, sticky="w",
                           pady=(2, 0))

    def _build_status_bar(self) -> None:
        Divider(self, self.theme).grid(row=3, column=0, sticky="ew",
                                       padx=10, pady=(4, 0))
        bar = tk.Frame(self, bg=self.theme["bg"])
        bar.grid(row=4, column=0, sticky="ew")
        self.lbl_status = tk.Label(bar, text="", bg=self.theme["bg"],
                                   fg=self.theme["hint_color"],
                                   font=("", 9), anchor="w", padx=12, pady=4)
        self.lbl_status._theme_role = "hint"
        self.lbl_status.pack(side=tk.LEFT)

    # --------------------------------------------------------- placeholder

    def _install_placeholder(self) -> None:
        self.input.insert("1.0", tr("input.placeholder"))
        self.input._is_placeholder = True
        self.input.configure(fg=self.theme["placeholder"])

        def on_focus_in(_e):
            if getattr(self.input, "_is_placeholder", False):
                self.input.delete("1.0", "end")
                self.input.configure(fg=self.theme["input_fg"])
                self.input._is_placeholder = False

        def on_focus_out(_e):
            if not self.input.get("1.0", "end-1c").strip():
                self.input.delete("1.0", "end")
                self.input.insert("1.0", tr("input.placeholder"))
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

    # --------------------------------------------------------- 输入事件

    def _on_enter(self, event):
        if event.state & 0x0001:  # Shift
            return None
        text = self._get_input_text()
        if not text:
            return "break"
        self.on_send()
        return "break"

    # --------------------------------------------------------- 发送

    def on_send(self) -> None:
        if self.busy:
            return
        text = self._get_input_text()
        if not text:
            return

        pid = self.cfg.get("provider", "")
        if not get_ai_key(self.keys, pid):
            self.append_message(tr("chat.system"), tr("chat.need_key"), "err")
            self.app.open_tutorial()
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
        threading.Thread(target=self._worker, args=(user_text, use_search),
                         daemon=True).start()

    def _make_client(self, cfg=None, keys=None) -> ChatClient:
        return self.app.make_client(cfg, keys)

    def _compose_messages(self, user_text: str, use_search: bool) -> list[dict]:
        messages: list[dict] = []
        prompt = (self.cfg.get("system_prompt") or "").strip()
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
            self.app.q.put(("status", tr("status.searching")))
            search_cfg = dict(self.cfg.get("search", {}))
            search_cfg["api_key"] = get_search_key(
                self.keys, search_cfg.get("provider", ""))
            try:
                results = run_search(search_cfg, user_text)
            except SearchError as exc:
                self.app.q.put(("notice",
                                tr("search.failed",
                                   error=self._search_error_text(exc))))
                results = []
            if results:
                self.app.q.put(("sources", results))
                self.history.append({
                    "role": "system",
                    "content": "联网搜索：" + " | ".join(
                        r.title for r in results[:5]),
                    "meta": "search",
                })
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
                on_chunk=lambda piece: self.app.q.put(("chunk", piece)),
                stop_event=self.stop_event,
            )
            if self.stop_event.is_set():
                self.app.q.put(("stopped", answer))
            else:
                self.app.q.put(("done", answer))
        except NetworkError as exc:
            if str(exc) == "TIMEOUT":
                self.app.q.put(("error", "请求超时：请检查网络或加大超时时间。"))
            else:
                self.app.q.put(("error", str(exc)))
        except APIError as exc:
            self.app.q.put(("error", str(exc)))
        except Exception as exc:
            self.app.q.put(("error", str(exc)))
        finally:
            self.client = None

    def on_stop(self) -> None:
        self.stop_event.set()
        client = self.client
        if client is not None:
            client.cancel()
        self._update_status(tr("status.stopped"))

    # --------------------------------------------------------- 队列轮询

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.app.q.get_nowait()
                if self._handle(kind, payload):
                    continue
                self.app.q.put((kind, payload))
                break
        except Exception:
            pass
        self.after(50, self._poll_queue)

    def _handle(self, kind: str, payload) -> bool:
        if kind == "chunk":
            self._on_chunk(payload)
            return True
        if kind == "sources":
            self.append_message(tr("chat.sources"),
                                format_sources(payload), "src")
            return True
        if kind == "notice":
            self.append_message(tr("chat.system"), payload, "sys")
            return True
        if kind == "status":
            self._update_status(payload)
            return True
        if kind in ("done", "stopped"):
            self._finalize(payload)
            if payload:
                self.history.append({"role": "assistant", "content": payload})
            self._trim_history()
            self._persist_current_log()
            self._set_busy_ui(False)
            self._update_status(
                tr("status.stopped") if kind == "stopped" else tr("status.done"))
            return True
        if kind == "error":
            self._finalize("")
            self.append_message(tr("chat.error"), payload, "err")
            self._set_busy_ui(False)
            self._update_status(tr("status.failed"))
            return True
        return False

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
        self.btn_send.set_enabled(not busy)
        self.btn_stop.set_enabled(busy)

    # --------------------------------------------------------- 显示

    def _chat_state(self, state: str) -> None:
        self.chat.config(state=state)

    def append_message(self, header: str, body: str, tag: str) -> None:
        self._chat_state(tk.NORMAL)
        stamp = time.strftime("%H:%M:%S")
        self.chat.insert(tk.END, "%s  %s\n" % (header, stamp), tag)
        if body:
            body_tag = "err" if tag == "err" else \
                ("src" if tag == "src" else "")
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

    # --------------------------------------------------------- 会话

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
        self.app.refresh_title()

    def _trim_history(self) -> None:
        if len(self.history) > 200:
            self.history = self.history[-200:]
            while self.history and self.history[0]["role"] != "user":
                self.history.pop(0)

    # --------------------------------------------------------- 聊天记录

    def _show_history_menu(self) -> None:
        menu = tk.Menu(self, tearoff=0,
                       bg=self.theme["panel_bg"], fg=self.theme["panel_fg"],
                       activebackground=self.theme["accent"],
                       activeforeground=self.theme["accent_fg"], bd=0)

        if self.current_log is not None or self.history:
            menu.add_command(label=tr("chat.rename"),
                             command=self._rename_current)
            menu.add_separator()

        logs = list_logs()
        if not logs:
            menu.add_command(label=tr("chat.empty"), state=tk.DISABLED)
        else:
            for log in logs[:30]:
                label = (log.name[:36] or DEFAULT_NAME)
                menu.add_command(label=label,
                                 command=lambda lid=log.id: self._load_log(lid))

        menu.add_separator()
        menu.add_command(label=tr("chat.new_topic"), command=self.new_session)

        try:
            x = self.history_bar.winfo_rootx()
            y = self.history_bar.winfo_rooty() + self.history_bar.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _rename_current(self) -> None:
        from tkinter import simpledialog
        current = ""
        if self.current_log is not None:
            current = self.current_log.name
        elif self.history:
            current = self._make_log_name()

        new_name = simpledialog.askstring(
            tr("chat.rename_title"), tr("chat.rename_prompt"),
            initialvalue=current, parent=self)
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            return

        if self.current_log is None:
            self.current_log = ChatLog(
                id=new_id(), name=new_name, messages=list(self.history))
            save_log(self.current_log)
        else:
            self.current_log.name = new_name
            save_log(self.current_log)
        self.app.refresh_title()

    def _make_log_name(self) -> str:
        for msg in self.history:
            if msg.get("role") == "user":
                return make_title_from(msg.get("content", ""))
        return tr("chat.new_topic").lstrip("＋ ")

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
        self.app.refresh_title()

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
            elif role == "system":
                self._display_plain(tr("chat.system"), content, "sys")

        self.append_message(tr("chat.system"),
                            tr("chat.loaded", name=log.name), "sys")
        self._set_busy_ui(False)
        self._update_status(tr("status.ready"))
        self.app.refresh_title()

    # --------------------------------------------------------- 状态

    def _update_status(self, note: str | None = None) -> None:
        model = self.cfg.get("model") or "-"
        pid = self.cfg.get("provider", "")
        key_state = tr("status.key_ok") if get_ai_key(self.keys, pid) \
            else tr("status.key_none")
        parts = ["%s: %s" % (tr("status.model"), model), key_state]
        if self.v_search.get():
            parts.append(tr("status.search_on"))
        self.lbl_model.configure(text="  |  ".join(parts))
        self.lbl_status.configure(
            text="%s: %s" % (tr("chat.system"), note or tr("status.ready")))

    def _on_search_toggle(self) -> None:
        enabled = bool(self.v_search.get())
        self.cfg.setdefault("search", {})["enabled"] = enabled
        if self.cfg.get("remember", True):
            from .config import save_config
            save_config(self.cfg)
        self._update_status()

    # --------------------------------------------------------- 设置

    def open_chat_settings(self) -> None:
        dlg = ChatSettingsDialog(self, self.app, on_saved=self.app.apply_settings)
        dlg.focus_set()
        self.app.chat_settings_dialog = dlg

    def test_connection(self) -> None:
        pid = self.cfg.get("provider", "")
        if not get_ai_key(self.keys, pid):
            self.append_message(tr("chat.system"), tr("chat.need_key"), "err")
            self.app.open_tutorial()
            return
        client = self._make_client()

        def run() -> None:
            try:
                self.app.q.put(("tb_test_ok", client.test()))
            except Exception as exc:
                self.app.q.put(("tb_test_err", str(exc)))

        threading.Thread(target=run, daemon=True).start()

    # --------------------------------------------------------- 主题

    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme
        self.configure(bg=theme["bg"])

        apply_theme_to_tree(self, theme)

        # 聊天区
        self.chat.configure(
            bg=theme["chat_bg"], fg=theme["chat_fg"],
            insertbackground=theme["chat_fg"],
            highlightbackground=theme["border"],
            selectbackground=theme["sel_bg"], selectforeground=theme["sel_fg"],
        )
        if getattr(self.input, "_is_placeholder", False):
            self.input.configure(fg=theme["placeholder"])

        # 滚动条
        self._scrollbar.configure(
            bg=theme["scrollbar"],
            troughcolor=theme["bg"],
            activebackground=theme["scrollbar_hl"],
        )

        # tag 颜色 + 字体
        for tag, key, weight in (
            ("user", "user_color", "bold"),
            ("ai", "ai_color", "bold"),
            ("sys", "sys_color", "normal"),
            ("err", "err_color", "bold"),
            ("src", "src_color", "normal"),
        ):
            self.chat.tag_configure(
                tag, foreground=theme[key],
                font=(self.app.font_family, self.app.font_size, weight),
            )

    def retranslate(self) -> None:
        self.btn_chat_settings.set_text(tr("toolbar.chat_settings"))
        self.btn_new.set_text(tr("toolbar.new"))
        self.btn_test.set_text(tr("toolbar.test"))
        self.btn_clear.set_text(tr("toolbar.clear"))
        self.chk_search.configure(text=tr("toolbar.search"))
        self.history_bar.set_text(tr("toolbar.history"))
        self.btn_send.set_text(tr("input.send"))
        self.btn_stop.set_text(tr("input.stop"))
        self.lbl_hint.configure(text=tr("input.hint"))
        if getattr(self.input, "_is_placeholder", False):
            self.input.delete("1.0", tk.END)
            self.input.insert("1.0", tr("input.placeholder"))
        self._update_status()