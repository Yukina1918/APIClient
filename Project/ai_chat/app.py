"""主窗口（PyQt6）：菜单栏 + 顶部导航 + 4 个页面（聊天/设置/线索/关于）。"""
from __future__ import annotations
import os
import queue
import sys
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (QAction, QActionGroup, QFont, QFontDatabase, QIcon)
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout,
                             QMainWindow, QMenu, QMessageBox, QStackedWidget,
                             QVBoxLayout, QWidget)
from .about_page import AboutPage
from .chat_page import ChatPage
from .client import ChatClient
from .codeblock import pick_mono
from .config import (APP_NAME, APP_VERSION, load_config, remove_config,
                     save_config)
from .i18n import LANGUAGES, get_language, set_language, tr
from .keys import (get_ai_key, load_keys, migrate_from_config, save_keys)
from .leads_page import LeadsPage
from .providers import get_provider
from .settings_page import SettingsPage
from .theme import build_palette, build_qss, ensure_icons, get as get_theme
from .tutorial import TutorialWindow
from .widgets import Divider, FlatButton

_FONT_CANDIDATES = (
    "Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑",
    "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC",
    "Meiryo UI", "Malgun Gothic", "Segoe UI",
)


def _app_icon_path() -> str:
    """定位随程序打包的图标，兼容源码运行与 PyInstaller 打包。"""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "app_icon.png")


def load_app_icon() -> QIcon:
    path = _app_icon_path()
    if os.path.exists(path):
        return QIcon(path)
    return QIcon()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
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
        self._pages: dict[str, QWidget] = {}
        self._current_page = "chat"
        self._build_menu()
        self._build_layout()
        self.apply_theme()
        self.retranslate()
        self._global_timer = QTimer(self)
        self._global_timer.timeout.connect(self._poll_global_queue)
        self._global_timer.start(100)
        if not get_ai_key(self.keys, self.cfg.get("provider", "")):
            QTimer.singleShot(400, self.open_tutorial)

    # ------------------------------------------------------------------ 字体
    def _pick_font_family(self) -> str:
        available = QFontDatabase.families()
        for name in _FONT_CANDIDATES:
            if name in available:
                return name
        return QFontDatabase.systemFont(
            QFontDatabase.SystemFont.GeneralFont).family()

    def _init_fonts(self) -> None:
        """字体初始化，Windows自动使用Segoe UI Emoji彩色emoji，跟随Win10/Win11系统表情"""
        size = int(self.cfg.get("font_size", 11))
        size = max(9, min(20, size))
        self.font_family = self._pick_font_family()
        self.font_size = size
        self.mono_font = pick_mono(size)
        app = QApplication.instance()
        if app is not None:
            main_font = QFont(self.font_family, size)
            # 设置回退表情字体，优先系统自带彩色emoji
            main_font.setFamilies([self.font_family, "Segoe UI Emoji"])
            app.setFont(main_font)

    def apply_fonts(self) -> None:
        self._init_fonts()
        for cb in getattr(self.chat_page, "_code_blocks", []):
            cb.apply_font(self.mono_font, self.font_size)

    # ------------------------------------------------------------------ 菜单
    def _build_menu(self) -> None:
        mb = self.menuBar()
        self.m_file = mb.addMenu("")
        self.act_settings = QAction(self)
        self.act_settings.triggered.connect(self.open_settings)
        self.m_file.addAction(self.act_settings)
        self.m_file.addSeparator()
        self.act_exit = QAction(self)
        self.act_exit.triggered.connect(self.close)
        self.m_file.addAction(self.act_exit)

        self.m_session = mb.addMenu("")
        self.act_new = QAction(self)
        self.act_new.triggered.connect(self._new_session)
        self.m_session.addAction(self.act_new)
        self.act_clear = QAction(self)
        self.act_clear.triggered.connect(self._clear_view)
        self.m_session.addAction(self.act_clear)

        self.m_lang = mb.addMenu("")
        self._lang_group = QActionGroup(self)
        self._lang_group.setExclusive(True)
        self._lang_actions: dict[str, QAction] = {}
        for code, native_name in LANGUAGES.items():
            act = QAction(native_name, self, checkable=True)
            act.triggered.connect(lambda _checked=False, c=code: self.set_language(c))
            self._lang_group.addAction(act)
            self.m_lang.addAction(act)
            self._lang_actions[code] = act

        self.m_help = mb.addMenu("")
        self.act_tutorial = QAction(self)
        self.act_tutorial.triggered.connect(self.open_tutorial)
        self.m_help.addAction(self.act_tutorial)
        self.act_about = QAction(self)
        self.act_about.triggered.connect(self.open_about)
        self.m_help.addAction(self.act_about)

    # ------------------------------------------------------------------ 布局
    def _build_layout(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        nav = QFrame()
        nav.setObjectName("navBar")
        nav_inner = QHBoxLayout(nav)
        nav_inner.setContentsMargins(10, 6, 10, 6)
        nav_inner.setSpacing(4)
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for key in ("chat", "settings", "leads", "about"):
            btn = FlatButton(nav, text=tr(f"nav.{key}"),
                             command=lambda k=key: self.show_page(k),
                             theme=self.theme, kind="ghost",
                             padx=18, pady=6, checkable=True)
            nav_inner.addWidget(btn)
            self._nav_group.addButton(btn)
            self._nav_buttons[key] = btn
        nav_inner.addStretch(1)
        root.addWidget(nav)
        root.addWidget(Divider(central, self.theme))

        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)
        self.chat_page = ChatPage(self._stack, self)
        self.settings_page = SettingsPage(self._stack, self)
        self.leads_page = LeadsPage(self._stack, self)
        self.about_page = AboutPage(self._stack, self)

        self._pages = {
            "chat": self.chat_page,
            "settings": self.settings_page,
            "leads": self.leads_page,
            "about": self.about_page,
        }
        for page in self._pages.values():
            self._stack.addWidget(page)
        self.setCentralWidget(central)
        self.show_page("chat")

    # ------------------------------------------------------------------ 页面切换
    def show_page(self, key: str) -> None:
        if key not in self._pages:
            return
        self._current_page = key
        self._stack.setCurrentWidget(self._pages[key])
        self._nav_buttons[key].setChecked(True)
        self.refresh_title()

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
        self.chk = self.chat_page.chk_search
        self.chk.setChecked(bool(new_cfg.get("search", {}).get("enabled", False)))
        self.apply_theme()
        if old_font != new_cfg.get("font_size"):
            self.apply_fonts()
        self.chat_page._update_status()

    # ------------------------------------------------------------------ 主题
    def apply_theme(self) -> None:
        theme_name = self.cfg.get("theme", "light")
        self.theme = get_theme(theme_name)
        t = self.theme
        icons = ensure_icons(t, theme_name)
        qapp = QApplication.instance()
        qapp.setStyleSheet(build_qss(t, theme_name, icons))
        qapp.setPalette(build_palette(t))
        for page in self._pages.values():
            try:
                page.refresh_theme(t)
            except Exception:
                pass
        if self._tutorial is not None:
            try:
                self._tutorial.refresh_theme(t)
            except Exception:
                pass
        dlg = self.chat_settings_dialog
        if dlg is not None:
            try:
                dlg.refresh_theme(t)
            except Exception:
                pass

    # ------------------------------------------------------------------ 多语言
    def retranslate(self) -> None:
        self.setWindowTitle(tr("app.title"))
        self.m_file.setTitle(tr("menu.file"))
        self.act_settings.setText(tr("nav.settings"))
        self.act_exit.setText(tr("menu.exit"))
        self.m_session.setTitle(tr("menu.session"))
        self.act_new.setText(tr("menu.new"))
        self.act_clear.setText(tr("menu.clear"))
        self.m_lang.setTitle(tr("menu.lang"))
        code = get_language()
        if code in self._lang_actions:
            self._lang_actions[code].setChecked(True)
        self.m_help.setTitle(tr("menu.help"))
        self.act_tutorial.setText(tr("tut.title"))
        self.act_about.setText(tr("about.title"))
        for key, btn in self._nav_buttons.items():
            btn.set_text(tr(f"nav.{key}"))
        for page in self._pages.values():
            try:
                page.retranslate()
            except Exception:
                pass
        if self._tutorial is not None:
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
            self.setWindowTitle(f"{base}  ·  {log.name}")
        else:
            self.setWindowTitle(base)

    # ------------------------------------------------------------------ 会话操作
    def _new_session(self) -> None:
        self.chat_page.new_session()

    def _clear_view(self) -> None:
        self.chat_page.clear_display()

    def open_settings(self) -> None:
        self.show_page("settings")

    def open_about(self) -> None:
        self.show_page("about")

    def open_tutorial(self) -> None:
        if self._tutorial is not None:
            self._tutorial.raise_()
            self._tutorial.activateWindow()
            return
        self._tutorial = TutorialWindow(self, self)
        self._tutorial.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._tutorial.show()
        self._tutorial.finished.connect(self._on_tutorial_closed)

    def _on_tutorial_closed(self, *_args) -> None:
        self._tutorial = None

    # ------------------------------------------------------------------ 全局消息队列
    def _poll_global_queue(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "tb_test_ok":
                    QMessageBox.information(self, tr("cs.test_ok"), tr("cs.test_ok_body", reply=str(payload)))
                elif kind == "tb_test_err":
                    QMessageBox.critical(self, tr("cs.test_fail"), tr("cs.test_fail_body", error=str(payload)))
                elif kind == "cs_test_ok":
                    dlg = self.chat_settings_dialog
                    if dlg is not None:
                        dlg.restore_test_button()
                        QMessageBox.information(dlg, tr("cs.test_ok"), tr("cs.test_ok_body", reply=str(payload)))
                    else:
                        self.q.put((kind, payload))
                        break
                elif kind == "cs_test_err":
                    dlg = self.chat_settings_dialog
                    if dlg is not None:
                        dlg.restore_test_button()
                        QMessageBox.critical(dlg, tr("cs.test_fail"), tr("cs.test_fail_body", error=str(payload)))
                    else:
                        self.q.put((kind, payload))
                        break
                else:
                    self.q.put((kind, payload))
                    break
        except queue.Empty:
            pass

    # ------------------------------------------------------------------ 关闭事件
    def closeEvent(self, event) -> None:
        try:
            self.chat_page.stop_event.set()
            if self.chat_page.client is not None:
                self.chat_page.client.cancel()
        except Exception:
            pass
        event.accept()


def main() -> None:
    # Windows：设置 AppUserModelID，让任务栏显示自定义图标而非 Python 默认图标
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "AITools.Turing.Client.5.2")
        except Exception:
            pass
    qapp = QApplication(sys.argv)
    qapp.setStyle("Fusion")
    icon = load_app_icon()
    if not icon.isNull():
        qapp.setWindowIcon(icon)
    win = MainWindow()
    win.resize(1000, 700)
    win.setMinimumSize(680, 520)
    win.show()
    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
