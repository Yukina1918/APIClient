"""聊天设置弹窗（PyQt6）：API / 对话参数 / 联网搜索 / 本地办公 / 图灵识别 / 优化。"""
from __future__ import annotations
import threading
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog,
                             QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QLineEdit, QMessageBox, QPushButton, QScrollArea,
                             QTextEdit, QVBoxLayout, QWidget)
from .formatting import estimate_messages_tokens
from .i18n import tr
from .keys import get_ai_key, get_search_key, set_ai_key, set_search_key
from .providers import PROVIDERS, by_name, get_provider
from .search import SEARCH_PROVIDERS
from .widgets import Divider, FlatButton, attach_text_arrow

SEARCH_LABELS = {
    "tavily": "Tavily",
    "serper": "Serper",
    "brave": "Brave Search",
    "bing": "Bing (Azure)",
    "searxng": "SearXNG",
    "duckduckgo": "DuckDuckGo",
    "custom": "自定义 / Custom",
}


class ChatSettingsDialog(QDialog):
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
        self._ready = False
        self.setWindowTitle(tr("cs.title"))
        self.setMinimumSize(560, 520)
        self._build()
        self.load_values()
        self._center(parent)
        # 预设 / 搜索服务的联动信号在控件全部建好后再连接
        self.cb_preset.currentIndexChanged.connect(self._on_preset)
        self.cb_sp.currentIndexChanged.connect(self._on_search_provider)
        # 用文字「▼」右对齐替代不显示的原生下拉箭头
        attach_text_arrow(self.cb_preset)
        attach_text_arrow(self.cb_model)
        attach_text_arrow(self.cb_sp)
        self._ready = True

    # ------------------------------------------------------------------
    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)
        # ---------- 滚动内容 ----------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self.body_layout = QVBoxLayout(inner)
        self.body_layout.setContentsMargins(4, 2, 8, 2)
        self.body_layout.setSpacing(4)

        self._add_section("cs.group_api")
        self._build_api_section()
        self._add_section("cs.group_dialog")
        self._build_dialog_section()
        self._add_section("cs.group_search")
        self._build_search_section()
        self._add_section("cs.group_agent")
        self._build_agent_section()
        self._add_section("cs.group_vision")
        self._build_vision_section()
        self._add_section("cs.group_opt")
        self._build_optimize_section()

        self.body_layout.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        # ---------- 底部按钮 ----------
        outer.addWidget(Divider(self, self.theme))
        bar = QHBoxLayout()
        self.btn_test = FlatButton(self, text=tr("cs.test"),
                                   command=self._do_test, theme=self.theme)
        bar.addWidget(self.btn_test)
        bar.addStretch(1)
        self.btn_cancel = FlatButton(self, text=tr("cs.cancel"),
                                     command=self.reject, theme=self.theme)
        bar.addWidget(self.btn_cancel)
        self.btn_save = FlatButton(self, text=tr("cs.save"),
                                   command=self._do_save, theme=self.theme,
                                   kind="accent")
        bar.addWidget(self.btn_save)
        outer.addLayout(bar)

    # ------------------------------------------------------------------
    def _add_section(self, key: str) -> None:
        lbl = QLabel(tr(key))
        lbl.setProperty("role", "section")
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        self.body_layout.addWidget(lbl)
        self.body_layout.addWidget(Divider(self, self.theme))

    def _grid(self) -> QGridLayout:
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.setColumnStretch(1, 1)
        self.body_layout.addLayout(g)
        return g

    @staticmethod
    def _grid_label(g: QGridLayout, r: int, key: str) -> None:
        lbl = QLabel(tr(key))
        g.addWidget(lbl, r, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    # ------------------------------------------------------------------ API
    def _build_api_section(self) -> None:
        g = self._grid()
        self.cb_preset = QComboBox()
        self.cb_preset.addItems([p.name for p in PROVIDERS])
        self._grid_label(g, 0, "cs.preset")
        g.addWidget(self.cb_preset, 0, 1)

        self.e_url = QLineEdit()
        self._grid_label(g, 1, "cs.base_url")
        g.addWidget(self.e_url, 1, 1)

        self.e_key = QLineEdit()
        self.e_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._grid_label(g, 2, "cs.api_key")
        key_row = QHBoxLayout()
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.addWidget(self.e_key, 1)
        self.chk_show = QCheckBox(tr("cs.show"))
        self.chk_show.toggled.connect(self._toggle_show)
        key_row.addWidget(self.chk_show)
        holder = QWidget()
        holder.setLayout(key_row)
        g.addWidget(holder, 2, 1)

        self.cb_model = QComboBox()
        self.cb_model.setEditable(True)
        self.cb_model.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._grid_label(g, 3, "cs.model")
        g.addWidget(self.cb_model, 3, 1)

    # ------------------------------------------------------------------ 对话
    def _build_dialog_section(self) -> None:
        g = self._grid()
        self.e_temp = QLineEdit("0.7")
        self.e_temp.setFixedWidth(90)
        self._grid_label(g, 0, "cs.temperature")
        g.addWidget(self.e_temp, 0, 1)

        self.e_ctx = QLineEdit("20")
        self.e_ctx.setFixedWidth(90)
        self._grid_label(g, 1, "cs.context")
        g.addWidget(self.e_ctx, 1, 1)

        self.e_timeout = QLineEdit("120")
        self.e_timeout.setFixedWidth(90)
        self._grid_label(g, 2, "cs.timeout")
        g.addWidget(self.e_timeout, 2, 1)

        self.e_proxy = QLineEdit()
        self._grid_label(g, 3, "cs.proxy")
        g.addWidget(self.e_proxy, 3, 1)

        sys_lbl = QLabel(tr("cs.system_prompt"))
        g.addWidget(sys_lbl, 4, 0, Qt.AlignmentFlag.AlignTop)
        self.t_sys = QTextEdit()
        self.t_sys.setAcceptRichText(False)
        self.t_sys.setFixedHeight(72)
        g.addWidget(self.t_sys, 4, 1)

        self.chk_stream = QCheckBox(tr("cs.stream"))
        self.chk_stream.setChecked(True)
        g.addWidget(self.chk_stream, 5, 0, 1, 2)

        self.lbl_token = QLabel("")
        self.lbl_token.setProperty("role", "hint")
        g.addWidget(self.lbl_token, 6, 0, 1, 2)

    # ------------------------------------------------------------------ 联网搜索
    def _build_search_section(self) -> None:
        g = self._grid()
        self.chk_search_enable = QCheckBox(tr("cs.search_enable"))
        g.addWidget(self.chk_search_enable, 0, 0, 1, 2)

        self.cb_sp = QComboBox()
        self.cb_sp.addItems(list(SEARCH_LABELS.values()))
        self._grid_label(g, 1, "cs.search_provider")
        g.addWidget(self.cb_sp, 1, 1)

        self.e_search_key = QLineEdit()
        self.e_search_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._grid_label(g, 2, "cs.search_key")
        g.addWidget(self.e_search_key, 2, 1)

        self.e_searx = QLineEdit()
        self._grid_label(g, 3, "cs.searxng_url")
        g.addWidget(self.e_searx, 3, 1)

    # ------------------------------------------------------------------ Agent本地办公
    def _build_agent_section(self) -> None:
        g = self._grid()
        self.chk_agent_enable = QCheckBox(tr("cs.agent_enable"))
        g.addWidget(self.chk_agent_enable, 0, 0, 1, 2)

        self.e_workspace = QLineEdit()
        self.btn_browse_ws = FlatButton(self, text="…", command=self._browse_workspace, theme=self.theme)
        ws_row = QHBoxLayout()
        ws_row.addWidget(self.e_workspace, 1)
        ws_row.addWidget(self.btn_browse_ws)
        ws_holder = QWidget()
        ws_holder.setLayout(ws_row)
        self._grid_label(g, 1, "cs.workspace")
        g.addWidget(ws_holder, 1, 1)

        self.chk_file = QCheckBox(tr("cs.agent_file"))
        g.addWidget(self.chk_file, 2, 0, 1, 2)

        self.chk_shell = QCheckBox(tr("cs.agent_shell"))
        g.addWidget(self.chk_shell, 3, 0, 1, 2)

        self.e_whitelist = QLineEdit()
        self._grid_label(g, 4, "cs.shell_whitelist")
        g.addWidget(self.e_whitelist, 4, 1)

        self.chk_confirm = QCheckBox(tr("cs.agent_confirm"))
        g.addWidget(self.chk_confirm, 5, 0, 1, 2)

        self.e_max_turn = QLineEdit("8")
        self.e_max_turn.setFixedWidth(90)
        self._grid_label(g, 6, "cs.max_tool_turns")
        g.addWidget(self.e_max_turn, 6, 1)

    # ------------------------------------------------------------------ 图灵识别
    def _build_vision_section(self) -> None:
        g = self._grid()
        self.chk_vision = QCheckBox(tr("cs.vision_enable"))
        g.addWidget(self.chk_vision, 0, 0, 1, 2)

    # ------------------------------------------------------------------ 聊天优化
    def _build_optimize_section(self) -> None:
        g = self._grid()
        self.cb_soften = QComboBox()
        self.cb_soften.addItems([
            tr("cs.soften_0"),
            tr("cs.soften_1"),
            tr("cs.soften_2"),
            tr("cs.soften_3"),
        ])
        self._grid_label(g, 0, "cs.soften")
        g.addWidget(self.cb_soften, 0, 1)

    # ------------------------------------------------------------------ 回调函数
    def _toggle_show(self, checked: bool):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.e_key.setEchoMode(mode)

    def _on_preset(self):
        if not self._ready:
            return
        name = self.cb_preset.currentText()
        prov = by_name(name)
        if prov is None:
            return
        self.e_url.setText(prov.base_url)
        self.cb_model.clear()
        self.cb_model.addItems(prov.models)

    def _on_search_provider(self):
        pass

    def _browse_workspace(self):
        path = QFileDialog.getExistingDirectory(self, tr("cs.select_workspace"))
        if path:
            self.e_workspace.setText(path)

    def load_values(self):
        # API预设
        prov_id = self.cfg.get("provider", "")
        p = get_provider(prov_id)
        idx = 0
        for i, pr in enumerate(PROVIDERS):
            if pr.id == p.id:
                idx = i
                break
        self.cb_preset.setCurrentIndex(idx)
        self.e_url.setText(self.cfg.get("base_url", ""))
        self.e_key.setText(get_ai_key(self.keys, p.id) or "")
        self.cb_model.setCurrentText(self.cfg.get("model", ""))

        # 对话参数
        self.e_temp.setText(str(self.cfg.get("temperature", 0.7)))
        self.e_ctx.setText(str(self.cfg.get("max_context", 20)))
        self.e_timeout.setText(str(self.cfg.get("timeout", 120)))
        self.e_proxy.setText(self.cfg.get("proxy", ""))
        self.t_sys.setPlainText(self.cfg.get("system_prompt", ""))
        self.chk_stream.setChecked(bool(self.cfg.get("stream", True)))

        # 搜索
        scfg = self.cfg.get("search", {})
        self.chk_search_enable.setChecked(bool(scfg.get("enabled", False)))
        sp = scfg.get("provider", "duckduckgo")
        for li, val in SEARCH_LABELS.items():
            if li == sp:
                self.cb_sp.setCurrentText(val)
                break
        self.e_search_key.setText(get_search_key(self.keys, sp) or "")
        self.e_searx.setText(scfg.get("endpoint", ""))

        # Agent
        acfg = self.cfg.get("agent", {})
        self.chk_agent_enable.setChecked(bool(acfg.get("enabled", False)))
        self.e_workspace.setText(acfg.get("workspace_dir", ""))
        self.chk_file.setChecked(bool(acfg.get("enable_files", True)))
        self.chk_shell.setChecked(bool(acfg.get("enable_shell", False)))
        self.e_whitelist.setText(acfg.get("shell_whitelist", ""))
        self.chk_confirm.setChecked(bool(acfg.get("require_confirm", True)))
        self.e_max_turn.setText(str(acfg.get("max_tool_turns", 8)))

        # 图灵识别
        vcfg = self.cfg.get("vision", {})
        self.chk_vision.setChecked(bool(vcfg.get("enabled", True)))

        # Markdown优化等级
        level = int(self.cfg.get("soften_level", 2))
        self.cb_soften.setCurrentIndex(level)

    def _do_save(self):
        # API
        preset_name = self.cb_preset.currentText()
        prov = by_name(preset_name)
        if prov:
            self.cfg["provider"] = prov.id
        self.cfg["base_url"] = self.e_url.text().strip()
        set_ai_key(self.keys, prov.id, self.e_key.text().strip())
        self.cfg["model"] = self.cb_model.currentText().strip()

        # 对话参数
        try:
            self.cfg["temperature"] = float(self.e_temp.text())
        except ValueError:
            self.cfg["temperature"] = 0.7
        try:
            self.cfg["max_context"] = int(self.e_ctx.text())
        except ValueError:
            self.cfg["max_context"] = 20
        try:
            self.cfg["timeout"] = int(self.e_timeout.text())
        except ValueError:
            self.cfg["timeout"] = 120
        self.cfg["proxy"] = self.e_proxy.text().strip()
        self.cfg["system_prompt"] = self.t_sys.toPlainText()
        self.cfg["stream"] = self.chk_stream.isChecked()

        # 搜索配置
        scfg = self.cfg.setdefault("search", {})
        scfg["enabled"] = self.chk_search_enable.isChecked()
        sp_text = self.cb_sp.currentText()
        real_sp = "duckduckgo"
        for k, v in SEARCH_LABELS.items():
            if v == sp_text:
                real_sp = k
                break
        scfg["provider"] = real_sp
        set_search_key(self.keys, real_sp, self.e_search_key.text().strip())
        scfg["endpoint"] = self.e_searx.text().strip()

        # Agent配置
        acfg = self.cfg.setdefault("agent", {})
        acfg["enabled"] = self.chk_agent_enable.isChecked()
        acfg["workspace_dir"] = self.e_workspace.text().strip()
        acfg["enable_files"] = self.chk_file.isChecked()
        acfg["enable_shell"] = self.chk_shell.isChecked()
        acfg["shell_whitelist"] = self.e_whitelist.text().strip()
        acfg["require_confirm"] = self.chk_confirm.isChecked()
        try:
            acfg["max_tool_turns"] = int(self.e_max_turn.text())
        except ValueError:
            acfg["max_tool_turns"] = 8

        # 图灵识别
        vcfg = self.cfg.setdefault("vision", {})
        vcfg["enabled"] = self.chk_vision.isChecked()

        # Markdown优化等级
        self.cfg["soften_level"] = self.cb_soften.currentIndex()

        self.on_saved(self.cfg, self.keys)
        self.accept()

    def _do_test(self):
        self.btn_test.set_enabled(False)
        cfg = dict(self.cfg)
        keys = dict(self.keys)

        def work():
            from .app import MainWindow
            win: MainWindow = self.parent().window()
            try:
                cli = win.make_client(cfg, keys)
                resp = cli.test()
                win.q.put(("cs_test_ok", resp))
            except Exception as e:
                win.q.put(("cs_test_err", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def restore_test_button(self):
        self.btn_test.set_enabled(True)

    def _center(self, parent):
        try:
            geo_p = parent.frameGeometry()
            x = geo_p.x() + max(0, (geo_p.width() - self.width()) // 2)
            y = geo_p.y() + max(0, (geo_p.height() - self.height()) // 3)
            self.move(x, y)
        except Exception:
            pass

    def refresh_theme(self, theme: dict):
        self.theme = theme

    def retranslate(self):
        pass
