# ai_chat/settings_page.py
"""设置页（PyQt6）：主题 / 语言 / 字号 / 数据 / 帮助。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QScrollArea, QVBoxLayout, QWidget)

from .config import data_dir, open_data_dir, reset_config, save_config
from .i18n import LANGUAGES, get_language, set_language, tr
from .keys import save_keys
from .widgets import Divider, FlatButton, attach_text_arrow, clear_layout


class SettingsPage(QWidget):
    def __init__(self, parent, app) -> None:
        super().__init__(parent)
        self.app = app
        self.theme = app.theme

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self._body = QWidget()
        self.body_layout = QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(32, 20, 32, 20)
        self.body_layout.setSpacing(4)
        self.scroll.setWidget(self._body)
        root.addWidget(self.scroll)

        self._populate()

    # ------------------------------------------------------------------

    def _section(self, key: str) -> None:
        lbl = QLabel(tr(key))
        lbl.setProperty("role", "section")
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        self.body_layout.addWidget(lbl)
        self.body_layout.addWidget(Divider(self._body, self.theme))

    def _row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 6, 0, 6)
        self.body_layout.addLayout(row)
        return row

    def _populate(self) -> None:
        clear_layout(self.body_layout)

        title = QLabel(tr("set.title"))
        f = title.font()
        f.setPointSize(max(12, self.app.font_size + 5))
        f.setBold(True)
        title.setFont(f)
        self.body_layout.addWidget(title)
        self.body_layout.addWidget(Divider(self._body, self.theme))

        # ---------- 外观 ----------
        self._section("set.appearance")
        self._row_theme()
        self._row_language()
        self._row_font()

        # ---------- 数据 ----------
        self._section("set.data")
        self._row_open_folder()
        self._row_reset()

        # ---------- 帮助 ----------
        self._section("set.help")
        self._row_tutorial()

        self.body_layout.addStretch(1)

        info = QLabel("AI Chat v%s\n%s: %s" % (
            self.app.version, tr("set.data"), data_dir()))
        info.setProperty("role", "hint")
        self.body_layout.addWidget(info)

    # ------------------------------------------------------------------

    def _row_theme(self) -> None:
        row = self._row()
        lbl = QLabel(tr("set.theme"))
        lbl.setFixedWidth(150)
        row.addWidget(lbl)

        self.btn_theme = FlatButton(
            self._body, text=self._theme_button_text(),
            command=self._toggle_theme, theme=self.theme)
        row.addWidget(self.btn_theme)
        row.addStretch(1)

    def _theme_button_text(self) -> str:
        # 按钮显示“当前主题 → 点击切换到的主题”
        if self.app.cfg.get("theme", "light") == "light":
            return "%s  →  %s" % (tr("set.theme.light"), tr("set.theme.dark"))
        return "%s  →  %s" % (tr("set.theme.dark"), tr("set.theme.light"))

    def _toggle_theme(self) -> None:
        current = self.app.cfg.get("theme", "light")
        new_theme = "dark" if current == "light" else "light"
        self.app.cfg["theme"] = new_theme
        if self.app.cfg.get("remember", True):
            save_config(self.app.cfg)
        self.app.apply_theme()
        self.btn_theme.set_text(self._theme_button_text())

    def _row_language(self) -> None:
        row = self._row()
        lbl = QLabel(tr("set.language"))
        lbl.setFixedWidth(150)
        row.addWidget(lbl)

        self.cb_lang = QComboBox()
        self.cb_lang.addItems(list(LANGUAGES.values()))
        self.cb_lang.setCurrentText(LANGUAGES.get(get_language(), "简体中文"))
        self.cb_lang.currentTextChanged.connect(self._on_language)
        row.addWidget(self.cb_lang)
        attach_text_arrow(self.cb_lang)
        row.addStretch(1)

    def _row_font(self) -> None:
        row = self._row()
        lbl = QLabel(tr("set.font_size"))
        lbl.setFixedWidth(150)
        row.addWidget(lbl)

        self.e_font = QLineEdit(str(self.app.cfg.get("font_size", 11)))
        self.e_font.setFixedWidth(80)
        row.addWidget(self.e_font)

        btn = FlatButton(self._body, text="OK", kind="accent",
                         command=self._on_font, theme=self.theme, padx=12)
        row.addWidget(btn)
        row.addStretch(1)

    def _row_open_folder(self) -> None:
        row = self._row()
        lbl = QLabel(tr("set.open_folder"))
        lbl.setFixedWidth(150)
        row.addWidget(lbl)
        btn = FlatButton(self._body, text=tr("set.open_folder"),
                         command=open_data_dir, theme=self.theme)
        row.addWidget(btn)
        row.addStretch(1)

    def _row_reset(self) -> None:
        row = self._row()
        lbl = QLabel(tr("set.reset_config"))
        lbl.setFixedWidth(150)
        row.addWidget(lbl)
        btn = FlatButton(self._body, text=tr("set.reset_config"),
                         command=self._on_reset, theme=self.theme)
        row.addWidget(btn)
        row.addStretch(1)

    def _row_tutorial(self) -> None:
        row = self._row()
        lbl = QLabel(tr("set.about_help"))
        lbl.setFixedWidth(150)
        row.addWidget(lbl)
        btn = FlatButton(self._body, text=tr("set.about_help"),
                         command=self.app.open_tutorial, theme=self.theme)
        row.addWidget(btn)
        row.addStretch(1)

    # ------------------------------------------------------------------

    def _on_language(self, native_name: str) -> None:
        for code, name in LANGUAGES.items():
            if name == native_name:
                if code == get_language():
                    return
                set_language(code)
                self.app.cfg["language"] = code
                if self.app.cfg.get("remember", True):
                    save_config(self.app.cfg)
                self.app.retranslate()
                break

    def _on_font(self) -> None:
        try:
            size = int(self.e_font.text())
        except ValueError:
            return
        size = max(9, min(20, size))
        self.e_font.setText(str(size))
        self.app.cfg["font_size"] = size
        if self.app.cfg.get("remember", True):
            save_config(self.app.cfg)
        self.app.apply_fonts()

    def _on_reset(self) -> None:
        ans = QMessageBox.question(
            self, tr("set.title"), tr("set.reset_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        new_cfg = reset_config()
        self.app.cfg.clear()
        self.app.cfg.update(new_cfg)
        save_keys(self.app.keys)
        self.app.apply_theme()
        self.app.apply_fonts()
        self.app.retranslate()
        QMessageBox.information(self, tr("set.title"), tr("set.reset_done"))

    # ------------------------------------------------------------------

    def refresh_theme(self, theme: dict) -> None:
        self.theme = theme

    def retranslate(self) -> None:
        self._populate()
