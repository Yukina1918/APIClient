"""聊天页：工具栏 + 聊天区 + 输入区 + 状态栏（PyQt6）。
能力：
  · 富文本渲染：AI 回复里的 fenced code block 显示为独立 CodeBlock（带复制）
  · 本地办公（Agent）：模型通过 Function Calling 读写工作区 / 执行白名单命令
  · 图灵识别：直接粘贴剪贴板图片 / 选本地图片，以真实图像（多模态）发给模型
"""
from __future__ import annotations
import html as _html
import io
import json
import os
import queue
import re
import threading
import time
from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QHBoxLayout,
                             QInputDialog, QLabel, QMenu, QMessageBox,
                             QScrollArea, QSizePolicy, QTextEdit, QVBoxLayout,
                             QWidget)
from .chat_settings import ChatSettingsDialog
from .client import APIError, ChatClient, NetworkError
from .codeblock import CodeBlock
from .config import save_config
from .formatting import soften_markdown
from .history import (ChatLog, DEFAULT_NAME, list_logs, load_log, make_title_from,
                      new_id, save_artifact, save_log)
from .i18n import tr
from .keys import get_ai_key, get_search_key
from .providers import get_provider
from .search import (SearchError, build_search_prompt, format_sources,
                     run_search)
from .tools import ToolResult, build_registry
from .vision import (IMAGE_EXTS, VisionError, build_multimodal_content,
                     read_clipboard_image, read_image_file)
from .widgets import Divider, FlatButton, clear_layout

# 围栏代码块：```lang\n code ``` 或 ~~~ ... ~~~
_FENCE_RE = re.compile(
    r"```([^\n`]*)\n?(.*?)```|~~~([^\n~]*)\n?(.*?)~~~", re.S)


# ------------------------------------------------- Markdown 表格渲染
def _looks_like_table_start(lines) -> bool:
    """判断 lines[0:2] 是否构成 Markdown 表格起始（表头 + 分隔行）。"""
    if len(lines) < 2:
        return False
    if "|" not in lines[0]:
        return False
    sep = lines[1].strip()
    return "-" in sep and "|" in sep


def _table_block_html(block_lines) -> str:
    rows = []
    for ln in block_lines:
        if "|" not in ln:
            break
        cells = [_html.escape(c.strip())
                 for c in ln.strip().strip("|").split("|")]
        rows.append(cells)
    out = ['<table border="1" cellspacing="0" cellpadding="5" '
           'style="border-collapse:collapse; margin:4px 0;">']
    for i, cells in enumerate(rows):
        tag = "th" if i == 0 else "td"
        out.append("<tr>" + "".join(
            "<%s>%s</%s>" % (tag, c, tag) for c in cells) + "</tr>")
    out.append("</table>")
    return "".join(out)


def md_prose_to_html(text: str) -> str:
    """把一段不含代码块的 Markdown 文本转成 QLabel 富文本 HTML。
    自动把 Markdown 表格转成 <table>，其余行转义后用 <br> 连接。"""
    lines = text.split("\n")
    out = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if "|" in line and i + 1 < n and _looks_like_table_start(lines[i:i + 2]):
            block = []
            j = i
            while j < n and "|" in lines[j]:
                block.append(lines[j])
                j += 1
            out.append(_table_block_html(block))
            i = j
            continue
        out.append(_html.escape(line))
        i += 1
    return "<br>".join(out)


# ----------------------------------------------------------------- 输入框
class InputBox(QTextEdit):
    """输入框：Enter 发送 / Shift+Enter 换行 / Ctrl+V 粘贴图片。"""
    def __init__(self, page: "ChatPage", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.page = page
        self.setAcceptRichText(False)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        modifiers = event.modifiers()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
                return
            self.page.on_send()
            return
        if key == Qt.Key.Key_V and modifiers & Qt.KeyboardModifier.ControlModifier:
            if self.page.paste_from_clipboard(silent=True):
                return
        super().keyPressEvent(event)


class ChatPage(QWidget):
    def __init__(self, parent, app) -> None:
        super().__init__(parent)
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
        # 图灵识别：待发送的真实图片 [(bytes, mime)]
        self.pending_images: list[tuple[bytes, str]] = []
        # 已嵌入的代码块（字号调整时刷新）
        self._code_blocks: list[CodeBlock] = []
        # 流式输出的临时控件
        self._stream_box: QWidget | None = None
        self._stream_content: QVBoxLayout | None = None
        self._stream_text = ""
        self._stream_label: QLabel | None = None
        # 需要主线程响应的 UI 请求（确认 / 申请权限 / 选图）
        self.ui_q: queue.Queue = queue.Queue()
        self._all_img_labels: list[QLabel] = []  # 视口剔除跟踪图片label
        self._build()
        self._q_timer = QTimer(self)
        self._q_timer.timeout.connect(self._poll_queue)
        self._q_timer.start(50)
        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._poll_ui)
        self._ui_timer.start(60)
        # 绑定滚动视口剔除
        self.chat_scroll.verticalScrollBar().valueChanged.connect(self._viewport_prune_images)

    # ------------------------------------------------------------------
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        self._build_toolbar(root)
        self._build_chat_area(root)
        self._build_input_area(root)
        self._build_status_bar(root)

    # ------------------------------------------------------------------
    def _build_toolbar(self, root) -> None:
        bar = QFrame()
        bar.setObjectName("toolBar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(10, 8, 10, 4)
        h.setSpacing(6)
        self.btn_chat_settings = FlatButton(
            bar, text=tr("toolbar.chat_settings"),
            command=self.open_chat_settings, theme=self.theme)
        h.addWidget(self.btn_chat_settings)
        self.btn_new = FlatButton(bar, text=tr("toolbar.new"),
                                  command=self.new_session, theme=self.theme)
        h.addWidget(self.btn_new)
        self.btn_test = FlatButton(bar, text=tr("toolbar.test"),
                                   command=self.test_connection,
                                   theme=self.theme)
        h.addWidget(self.btn_test)
        self.btn_clear = FlatButton(bar, text=tr("toolbar.clear"),
                                    command=self.clear_display,
                                    theme=self.theme)
        h.addWidget(self.btn_clear)
        self.chk_search = QCheckBox(tr("toolbar.search"))
        self.chk_search.setChecked(
            bool(self.app.cfg.get("search", {}).get("enabled")))
        self.chk_search.stateChanged.connect(self._on_search_toggle)
        h.addSpacing(8)
        h.addWidget(self.chk_search)
        h.addStretch(1)
        self.lbl_model = QLabel("")
        self.lbl_model.setProperty("role", "hint")
        h.addWidget(self.lbl_model)
        self.history_bar = FlatButton(
            bar, text=tr("toolbar.history"),
            command=self._show_history_menu, theme=self.theme)
        h.addWidget(self.history_bar)
        self.btn_vision = FlatButton(
            bar, text=tr("toolbar.vision"),
            command=self._vision_menu, theme=self.theme)
        h.addWidget(self.btn_vision)
        if not self.cfg.get("vision", {}).get("enabled", True):
            self.btn_vision.setVisible(False)
        root.addWidget(bar)

    def _build_chat_area(self, root) -> None:
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_holder = QWidget()
        self.msg_layout = QVBoxLayout(self.chat_holder)
        self.msg_layout.setContentsMargins(10, 8, 10, 8)
        self.msg_layout.setSpacing(3)
        self.msg_layout.addStretch(1)
        self.chat_scroll.setWidget(self.chat_holder)
        root.addWidget(self.chat_scroll, 1)

    def _build_input_area(self, root) -> None:
        wrap = QFrame()
        wrap.setObjectName("inputBar")
        v = QVBoxLayout(wrap)
        v.setContentsMargins(10, 4, 10, 4)
        v.setSpacing(2)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.input = InputBox(self)
        self.input.setPlaceholderText(tr("input.placeholder"))
        self.input.setFixedHeight(96)
        row.addWidget(self.input, 1)
        btns = QVBoxLayout()
        btns.setSpacing(6)
        self.btn_send = FlatButton(wrap, text=tr("input.send"),
                                   command=self.on_send, theme=self.theme,
                                   kind="accent", padx=18, pady=8)
        btns.addWidget(self.btn_send)
        self.btn_stop = FlatButton(wrap, text=tr("input.stop"),
                                   command=self.on_stop, theme=self.theme,
                                   padx=18, pady=8)
        btns.addWidget(self.btn_stop)
        self.btn_stop.set_enabled(False)
        row.addLayout(btns)
        v.addLayout(row)
        self.lbl_hint = QLabel(tr("input.hint"))
        self.lbl_hint.setProperty("role", "hint")
        v.addWidget(self.lbl_hint)
        root.addWidget(wrap)

    def _build_status_bar(self, root) -> None:
        root.addWidget(Divider(self, self.theme))
        bar = QFrame()
        bar.setObjectName("statusBar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 3, 12, 4)
        self.lbl_status = QLabel("")
        self.lbl_status.setProperty("role", "hint")
        h.addWidget(self.lbl_status)
        root.addWidget(bar)

    # --------------------------------------------------------- 输入/发送
    def _get_input_text(self) -> str:
        return self.input.toPlainText().strip()

    def _clear_input(self) -> None:
        self.input.clear()

    def _display_user_with_attach(self, header: str, body: str, tag: str, image_bytes_list: list[tuple[bytes, str]]):
        """渲染用户消息：文字 + [图片]标签 + 图片预览"""
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(4, 3, 4, 2)
        v.setSpacing(4)
        stamp = time.strftime("%H:%M:%S")
        h = QLabel(f"{header}  {stamp}")
        h.setProperty("role", tag)
        f = h.font()
        f.setBold(True)
        h.setFont(f)
        v.addWidget(h)

        if body.strip():
            txt_label = QLabel(body.rstrip())
            txt_label.setWordWrap(True)
            txt_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
            v.addWidget(txt_label)

        if image_bytes_list:
            attach_text = "用户文件：" + "".join(["[图片]"] * len(image_bytes_list))
            attach_lbl = QLabel(attach_text)
            attach_lbl.setProperty("role", "hint")
            v.addWidget(attach_lbl)
            for data, _mime in image_bytes_list:
                pm = QPixmap()
                pm.loadFromData(data)
                lbl_img = QLabel()
                lbl_img._raw_bytes = data
                lbl_img.setPixmap(pm.scaledToWidth(420, Qt.TransformationMode.SmoothTransformation))
                lbl_img.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                v.addWidget(lbl_img)
                self._all_img_labels.append(lbl_img)

        self.msg_layout.insertWidget(self.msg_layout.count() - 1, box)
        self._scroll_bottom()

    def _viewport_prune_images(self):
        viewport = self.chat_scroll.viewport()
        view_rect = viewport.rect()
        for lbl in self._all_img_labels:
            if not lbl.isVisible():
                continue
            lbl_geo = lbl.geometry()
            mapped = lbl.mapTo(viewport, lbl_geo.topLeft())
            lbl_rect = lbl_geo
            lbl_rect.moveTopLeft(mapped)
            intersect = view_rect.intersects(lbl_rect)
            if intersect:
                if lbl.pixmap() is None or lbl.pixmap().isNull():
                    pm = QPixmap()
                    pm.loadFromData(lbl._raw_bytes)
                    lbl.setPixmap(pm.scaledToWidth(420, Qt.TransformationMode.SmoothTransformation))
            else:
                if not (lbl.pixmap() is None or lbl.pixmap().isNull()):
                    lbl.setPixmap(QPixmap())

    def on_stop(self) -> None:
        """用户点了「停止」：通知后台线程尽快收尾。"""
        if not self.busy:
            return
        self.stop_event.set()
        self.btn_stop.set_enabled(False)
        self._update_status(tr("status.stopping"))

    def on_send(self) -> None:
        if self.busy:
            return
        text = self._get_input_text()
        if not text and not self.pending_images:
            return
        pid = self.cfg.get("provider", "")
        if not get_ai_key(self.keys, pid):
            self.append_message(tr("chat.system"), tr("chat.need_key"), "err")
            self.app.open_tutorial()
            return
        images = list(self.pending_images)
        self.pending_images = []
        self._clear_input()
        self.history.append({"role": "user", "content": text, "attach_count": len(images)})
        self._display_user_with_attach(tr("chat.you"), text, "user", images)
        self._persist_current_log()
        if images:
            self._save_attached_images(images)
        self._start_request(text, images)

    def _save_attached_images(self, images) -> None:
        if self.current_log is None:
            return
        for idx, (data, _mime) in enumerate(images):
            save_path = self.current_log.get_image_path(idx)
            with open(save_path, "wb") as fh:
                fh.write(data)

    def _start_request(self, user_text: str, images) -> None:
        self.busy = True
        self.stop_event = threading.Event()
        self._stream_start = None
        self._set_busy_ui(True)
        self._update_status(tr("status.requesting"))
        use_search = self.chk_search.isChecked()
        use_agent = bool(self.cfg.get("agent", {}).get("enabled", False))
        target = self._worker_agent if use_agent else self._worker
        threading.Thread(target=target,
                         args=(user_text, use_search, images),
                         daemon=True).start()

    def _make_client(self, cfg=None, keys=None) -> ChatClient:
        return self.app.make_client(cfg, keys)

    def _compose_messages(self, user_text: str, use_search: bool,
                          images) -> list[dict]:
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
        if images:
            messages[-1]["content"] = build_multimodal_content(
                content if isinstance(content, str) else user_text, images)
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

    # --------------------------------------------------------- 普通流式
    def _worker(self, user_text: str, use_search: bool, images) -> None:
        try:
            messages = self._compose_messages(user_text, use_search, images)
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

    # --------------------------------------------------------- Agent 循环
    def _worker_agent(self, user_text: str, use_search: bool, images) -> None:
        try:
            agent_cfg = self.cfg.get("agent", {})
            registry, _sandbox = build_registry(agent_cfg)
        except Exception as exc:
            self.app.q.put(("error", tr("agent.init_failed", error=exc)))
            return
        schemas = registry.schemas()
        try:
            base_messages = self._compose_messages(user_text, use_search,
                                                   images)
        except Exception as exc:
            self.app.q.put(("error", str(exc)))
            return
        max_turns = max(1, min(20, int(agent_cfg.get("max_tool_turns", 8))))
        require_confirm = bool(agent_cfg.get("require_confirm", True))
        try:
            client = self._make_client()
            self.client = client
            working = list(base_messages)
            answer = ""
            for _turn in range(max_turns):
                if self.stop_event.is_set():
                    break
                self.app.q.put(("status", tr("status.thinking")))
                answer = client.chat(working, stream=False,
                                     stop_event=self.stop_event,
                                     tools=schemas)
                msg = client.last_message or {}
                tool_calls = msg.get("tool_calls")
                if not tool_calls:
                    break
                working.append(msg)
                for tc in tool_calls:
                    fn = tc.get("function") or {}
                    fname = fn.get("name", "")
                    try:
                        fargs = json.loads(fn.get("arguments", "") or "{}")
                    except (json.JSONDecodeError, TypeError):
                        fargs = {}
                    tcid = tc.get("id", "")
                    # 命令权限：不在白名单 → 向管理员申请
                    if fname == "run_command":
                        if not self._ensure_shell_permission(registry, fargs):
                            result = ToolResult.failure(
                                tr("agent.shell_denied"))
                            working.append(self._tool_msg(tcid, result))
                            self._record_tool(fname, fargs, result)
                            continue
                    # 危险操作人工确认
                    if require_confirm and registry.is_dangerous(fname):
                        desc = registry.describe(fname, fargs)
                        allowed = self.ui_request("confirm", {
                            "title": tr("agent.confirm_title"),
                            "body": tr("agent.confirm_body", desc=desc),
                        })
                        if not allowed:
                            result = ToolResult.failure(
                                tr("agent.user_denied"))
                            working.append(self._tool_msg(tcid, result))
                            self._record_tool(fname, fargs, result)
                            continue
                    result = registry.execute(fname, fargs)
                    if fname == "write_file" and result.ok:
                        self._archive_artifact(fargs)
                    working.append(self._tool_msg(tcid, result))
                    self._record_tool(fname, fargs, result)
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

    @staticmethod
    def _tool_msg(tcid: str, result: ToolResult) -> dict:
        return {"role": "tool", "tool_call_id": tcid,
                "content": result.content}

    def _record_tool(self, fname, fargs, result) -> None:
        state = tr("agent.tool_ok") if result.ok else tr("agent.tool_fail")
        brief = "%s %s" % (fname, fargs)
        if len(brief) > 80:
            brief = brief[:80] + "…"
        line = "[%s] %s → %s" % (tr("chat.system"), brief, state)
        self.history.append({"role": "system", "content": line,
                             "meta": "tool"})
        self.app.q.put(("notice", line))

    def _archive_artifact(self, fargs: dict) -> None:
        if self.current_log is None:
            return
        rel = str(fargs.get("path", ""))
        ext = os.path.splitext(rel)[1].lstrip(".") or "txt"
        try:
            save_artifact(self.current_log, ext,
                          str(fargs.get("content", "")))
        except Exception:
            pass

    # --------------------------------------------------------- 命令提权
    def _ensure_shell_permission(self, registry, fargs) -> bool:
        from .tools.shell import _parse_whitelist, _split_command
        command = str(fargs.get("command", ""))
        tokens = _split_command(command)
        if not tokens:
            return False
        prog = os.path.basename(tokens[0]).lower()
        if prog.endswith(".exe"):
            prog = prog[:-4]
        whitelist = _parse_whitelist(
            self.cfg.get("agent", {}).get("shell_whitelist", ""))
        if prog in whitelist:
            return True
        decision = self.ui_request("apply_permission", {
            "prog": prog, "command": command})
        if decision == "deny":
            return False
        whitelist.add(prog)
        new_wl = ", ".join(sorted(whitelist))
        tool = registry.get("run_command")
        if tool is not None:
            tool.config["shell_whitelist"] = new_wl
        if decision == "always":
            self.cfg.setdefault("agent", {})["shell_whitelist"] = new_wl
            try:
                save_config(self.cfg)
            except Exception:
                pass
        return True

    # --------------------------------------------------------- 主线程请求
    def ui_request(self, kind: str, payload: dict):
        resp_q: queue.Queue = queue.Queue()
        self.ui_q.put((kind, payload, resp_q))
        return resp_q.get()

    def _poll_ui(self) -> None:
        try:
            while True:
                kind, payload, resp_q = self.ui_q.get_nowait()
                if kind == "confirm":
                    ans = QMessageBox.question(
                        self, payload["title"], payload["body"],
                        QMessageBox.StandardButton.Yes
                        | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes)
                    resp_q.put(ans == QMessageBox.StandardButton.Yes)
                elif kind == "apply_permission":
                    resp_q.put(self._apply_permission_dialog(payload))
                elif kind == "alert":
                    QMessageBox.information(self, payload["title"],
                                            payload["body"])
                    resp_q.put(True)
        except queue.Empty:
            pass

    def _apply_permission_dialog(self, payload: dict) -> str:
        box = QMessageBox(self)
        box.setWindowTitle(tr("agent.apply_title"))
        box.setText(
            tr("agent.apply_body", prog=payload["prog"],
               command=payload["command"]) + "\n\n" + tr("agent.apply_choices"))
        yes = box.addButton(QMessageBox.StandardButton.Yes)
        no = box.addButton(QMessageBox.StandardButton.No)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        btn = box.clickedButton()
        if btn is yes:
            return "always"
        if btn is no:
            return "once"
        return "deny"

    # --------------------------------------------------------- 图灵识别
    def _vision_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction(tr("vision.paste"), self.paste_from_clipboard)
        menu.addAction(tr("vision.pick"), self._pick_and_attach)
        n = len(self.pending_images)
        clear_act = menu.addAction(
            tr("vision.clear", n=n), self._clear_pending)
        clear_act.setEnabled(bool(n))
        menu.exec(self.btn_vision.mapToGlobal(
            QPoint(0, self.btn_vision.height())))

    def paste_from_clipboard(self, silent: bool = False) -> bool:
        """从剪贴板粘贴图片（支持直接图片与复制的图片文件），返回是否成功。
        silent=True 时（Ctrl+V 粘贴纯文本），剪贴板无图片则不提示、直接放行默认粘贴。"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        # 1) 剪贴板里是位图（截图工具 / 聊天软件复制）
        if mime is not None and mime.hasImage():
            try:
                data, mtype = read_clipboard_image()
            except VisionError as exc:
                self.append_message(tr("chat.system"),
                                    tr("vision.paste_failed", error=exc),
                                    "err")
                return False
            self.pending_images.append((data, mtype))
            self._update_status()
            return True
        # 2) 剪贴板里是文件（资源管理器复制的图片）
        if mime is not None and mime.hasUrls():
            attached = 0
            for url in mime.urls():
                path = url.toLocalFile()
                if not path or not os.path.splitext(path)[1].lower() in IMAGE_EXTS:
                    continue
                try:
                    data, mtype = read_image_file(path)
                except VisionError as exc:
                    self.append_message(tr("chat.system"),
                                        tr("vision.paste_failed", error=exc),
                                        "err")
                    continue
                self.pending_images.append((data, mtype))
                attached += 1
            if attached:
                self._update_status()
                return True
        # 剪贴板里既无位图也无图片文件：Ctrl+V 粘贴文本时静默放行，
        # 只有从「图灵识别」菜单主动调起时才提示。
        if not silent:
            self.append_message(tr("chat.system"),
                                tr("vision.no_clipboard"), "sys")
        return False

    def _pick_and_attach(self) -> None:
        flt = "%s (%s);;%s (*.*)" % (
            tr("vision.images"),
            " ".join("*" + e for e in IMAGE_EXTS),
            tr("vision.all"))
        path, _chosen = QFileDialog.getOpenFileName(
            self, tr("vision.title"), "", flt)
        if not path:
            return
        try:
            data, mtype = read_image_file(path)
        except VisionError as exc:
            QMessageBox.critical(self, tr("vision.title"), str(exc))
            return
        self.pending_images.append((data, mtype))
        self._update_status()

    def _clear_pending(self) -> None:
        self.pending_images = []
        self._update_status()

    # --------------------------------------------------------- 队列轮询
    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.app.q.get_nowait()
                kind, payload = item[0], item[1]
                if self._handle(kind, payload):
                    continue
                self.app.q.put(item)
                break
        except Exception:
            pass

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
        if kind == "vision_attached":
            self._update_status()
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
        if self._stream_box is None:
            box = QWidget()
            v = QVBoxLayout(box)
            v.setContentsMargins(4, 3, 4, 2)
            v.setSpacing(2)
            stamp = time.strftime("%H:%M:%S")
            header = QLabel("%s  %s" % (tr("chat.ai"), stamp))
            header.setProperty("role", "ai")
            f = header.font()
            f.setBold(True)
            header.setFont(f)
            v.addWidget(header)
            content = QVBoxLayout()
            content.setContentsMargins(0, 0, 0, 0)
            content.setSpacing(3)
            v.addLayout(content)
            self.msg_layout.insertWidget(
                self.msg_layout.count() - 1, box)
            self._stream_box = box
            self._stream_content = content
        self._stream_text += piece
        # 流式正文放进一个 QLabel（随到随更新）
        if self._stream_label is None:
            self._stream_label = QLabel()
            self._stream_label.setWordWrap(True)
            self._stream_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
            self._stream_content.addWidget(self._stream_label)
        self._stream_label.setText(self._stream_text)
        self._scroll_bottom()

    def _finalize(self, answer: str) -> None:
        level = int(self.cfg.get("soften_level", 2))
        cleaned = soften_markdown(answer, level)
        if self._stream_box is not None:
            content = self._stream_content
            if self._stream_label is not None:
                self._stream_label.setParent(None)
                self._stream_label.deleteLater()
                self._stream_label = None
            if cleaned:
                self._fill_rich(content, cleaned)
            else:
                ph = QLabel("")
                content.addWidget(ph)
            self._stream_box = None
            self._stream_content = None
            self._stream_text = ""
            self._scroll_bottom()
        elif cleaned:
            self._display_rich(tr("chat.ai"), cleaned, "ai", stamp=True)

    def _set_busy_ui(self, busy: bool) -> None:
        self.busy = busy
        self.btn_send.set_enabled(not busy)
        self.btn_stop.set_enabled(busy)

    # --------------------------------------------------------- 富文本
    def _fill_rich(self, layout, text: str) -> None:
        pos = 0
        for m in _FENCE_RE.finditer(text):
            pre = text[pos:m.start()]
            if pre:
                layout.addWidget(self._text_label(pre))
            if m.group(2) is not None:
                lang, code = m.group(1), m.group(2)
            else:
                lang, code = m.group(3), m.group(4)
            code = code or ""
            first = code.strip().split("\n")[0] if code.strip() else ""
            # 代码块内容其实是 Markdown 表格 → 渲染成真表格，而非代码块
            if first.lstrip().startswith("|") and "|" in first:
                layout.addWidget(self._html_table_label(code))
            else:
                self._add_codeblock(layout, (lang or "").strip(), code)
            pos = m.end()
        rest = text[pos:]
        if rest:
            layout.addWidget(self._text_label(rest))

    def _html_table_label(self, text: str) -> QLabel:
        lbl = QLabel()
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setText(md_prose_to_html(text))
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding,
                          QSizePolicy.Policy.Preferred)
        return lbl

    def _text_label(self, text: str) -> QLabel:
        lbl = QLabel()
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding,
                          QSizePolicy.Policy.Preferred)
        # 含 Markdown 表格 → 转成 HTML 真表格；否则纯文本
        stripped = text.lstrip()
        if stripped.startswith("|") or "\n|" in text:
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setText(md_prose_to_html(text))
        else:
            lbl.setText(text.rstrip())
        return lbl

    def _add_codeblock(self, layout, lang: str, code: str) -> None:
        cb = CodeBlock(None, self.theme, lang, code,
                       mono=self.app.mono_font, size=self.app.font_size)
        layout.addWidget(cb)
        self._code_blocks.append(cb)

    def _scroll_bottom(self) -> None:
        bar = self.chat_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

    # --------------------------------------------------------- 显示
    def append_message(self, header: str, body: str, tag: str) -> None:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(4, 3, 4, 2)
        v.setSpacing(2)
        stamp = time.strftime("%H:%M:%S")
        h = QLabel("%s  %s" % (header, stamp))
        h.setProperty("role", tag)
        f = h.font()
        f.setBold(True)
        h.setFont(f)
        v.addWidget(h)
        if body:
            b = QLabel(body.rstrip())
            if tag in ("err", "src"):
                b.setProperty("role", tag)
            b.setWordWrap(True)
            b.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse |
                Qt.TextInteractionFlag.TextSelectableByKeyboard)
            v.addWidget(b)
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, box)
        self._scroll_bottom()

    def _display_rich(self, header: str, body: str, tag: str,
                      stamp: bool = False) -> None:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(4, 3, 4, 2)
        v.setSpacing(2)
        head_text = "%s  %s" % (header, time.strftime("%H:%M:%S")) if stamp \
            else header
        h = QLabel(head_text)
        h.setProperty("role", tag)
        f = h.font()
        f.setBold(True)
        h.setFont(f)
        v.addWidget(h)
        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(3)
        self._fill_rich(content, body)
        v.addLayout(content)
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, box)
        self._scroll_bottom()

    def _display_plain(self, header: str, body: str, tag: str) -> None:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(4, 3, 4, 2)
        v.setSpacing(2)
        h = QLabel(header)
        h.setProperty("role", tag)
        f = h.font()
        f.setBold(True)
        h.setFont(f)
        v.addWidget(h)
        if body:
            b = QLabel(body.rstrip())
            if tag in ("err", "src"):
                b.setProperty("role", tag)
            b.setWordWrap(True)
            b.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse |
                Qt.TextInteractionFlag.TextSelectableByKeyboard)
            v.addWidget(b)
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, box)

    def clear_display(self) -> None:
        clear_layout(self.msg_layout)
        self.msg_layout.addStretch(1)
        self._code_blocks = []
        self._stream_box = None
        self._stream_content = None
        self._stream_label = None
        self._stream_text = ""
        self._all_img_labels.clear()

    # --------------------------------------------------------- 会话
    def new_session(self, clear: bool = True, silent: bool = False) -> None:
        self.stop_event.set()
        self.stop_event = threading.Event()
        self.busy = False
        self._stream_start = None
        self.history = []
        self.current_log = None
        self.pending_images = []
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
        menu = QMenu(self)
        if self.current_log is not None or self.history:
            menu.addAction(tr("chat.rename"), self._rename_current)
            menu.addSeparator()
        logs = list_logs()
        if not logs:
            act = menu.addAction(tr("chat.empty"))
            act.setEnabled(False)
        else:
            for log in logs[:30]:
                label = (log.name[:36] or DEFAULT_NAME)
                menu.addAction(label,
                               lambda lid=log.id: self._load_log(lid))
        menu.addSeparator()
        menu.addAction(tr("chat.new_topic"), self.new_session)
        menu.exec(self.history_bar.mapToGlobal(
            QPoint(0, self.history_bar.height())))

    def _rename_current(self) -> None:
        current = ""
        if self.current_log is not None:
            current = self.current_log.name
        elif self.history:
            current = self._make_log_name()
        new_name, ok = QInputDialog.getText(
            self, tr("chat.rename_title"), tr("chat.rename_prompt"),
            text=current)
        if not ok:
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
            attach_cnt = msg.get("attach_count", 0)
            if role == "user":
                image_list = []
                for i in range(attach_cnt):
                    img_path = log.get_image_path(i)
                    if os.path.exists(img_path):
                        try:
                            with open(img_path, "rb") as f:
                                img_bytes = f.read()
                            image_list.append((img_bytes, "image/png"))
                        except Exception:
                            pass
                self._display_user_with_attach(tr("chat.you"), content, "user", image_list)
            elif role == "assistant":
                self._display_rich(tr("chat.ai"), content, "ai")
            elif role == "system":
                self.append_message(tr("chat.system"), content, "sys")

        self.append_message(tr("chat.system"),
                            tr("chat.loaded", name=log.name), "sys")
        self._set_busy_ui(False)
        self._update_status(tr("status.ready"))
        self.app.refresh_title()

    # --------------------------------------------------------- 设置
    def open_chat_settings(self) -> None:
        dlg = ChatSettingsDialog(self, self.app,
                                 on_saved=self.app.apply_settings)
        self.app.chat_settings_dialog = dlg
        dlg.exec()
        self.app.chat_settings_dialog = None

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

    # --------------------------------------------------------- 主题/多语言
    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme
        for cb in list(self._code_blocks):
            cb.refresh_theme(theme)

    def retranslate(self) -> None:
        self.btn_chat_settings.set_text(tr("toolbar.chat_settings"))
        self.btn_new.set_text(tr("toolbar.new"))
        self.btn_test.set_text(tr("toolbar.test"))
        self.btn_clear.set_text(tr("toolbar.clear"))
        self.chk_search.setText(tr("toolbar.search"))
        self.btn_vision.set_text(tr("toolbar.vision"))
        self.history_bar.set_text(tr("toolbar.history"))
        self.btn_send.set_text(tr("input.send"))
        self.btn_stop.set_text(tr("input.stop"))
        self.lbl_hint.setText(tr("input.hint"))
        self.input.setPlaceholderText(tr("input.placeholder"))
        self._update_status()

    # --------------------------------------------------------- 状态/搜索开关
    def _update_status(self, note: str | None = None) -> None:
        model = self.cfg.get("model") or "-"
        pid = self.cfg.get("provider", "")
        key_state = tr("status.key_ok") if get_ai_key(self.keys, pid) \
            else tr("status.key_none")
        parts = ["%s: %s" % (tr("status.model"), model), key_state]
        if self.chk_search.isChecked():
            parts.append(tr("status.search_on"))
        if self.cfg.get("agent", {}).get("enabled"):
            parts.append(tr("status.agent_on"))
        if self.pending_images:
            parts.append(tr("status.images", n=len(self.pending_images)))
        self.lbl_model.setText("  |  ".join(parts))
        self.lbl_status.setText(
            "%s: %s" % (tr("chat.system"), note or tr("status.ready")))

    def _on_search_toggle(self, *_args) -> None:
        enabled = bool(self.chk_search.isChecked())
        self.cfg.setdefault("search", {})["enabled"] = enabled
        if self.cfg.get("remember", True):
            save_config(self.cfg)
        self._update_status()
