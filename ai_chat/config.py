# ai_chat/config.py
"""配置读写：所有文件统一放在 data/ 目录下。"""
from __future__ import annotations

import copy
import json
import os
import sys

APP_NAME = "AI Chat"
APP_VERSION = "4.0"
DATA_DIR_NAME = "data"
CONFIG_NAME = "config.json"
CHAT_DIR_NAME = "chat"
LEGACY_CONFIG_NAME = "ai_chat_config.json"

DEFAULTS: dict = {
    "language": "zh_CN",
    "theme": "light",
    "provider": "openai",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "timeout": 120,
    "proxy": "",
    "stream": True,
    "remember": True,
    "system_prompt": "",
    "soften_level": 2,
    "font_size": 11,
    "max_context": 20,
    "search": {
        "enabled": False,
        "provider": "duckduckgo",
        "endpoint": "",
        "max_results": 5,
    },
    # 本地办公（Agent）：所有文件 / 命令操作都被强制锁在 workspace_dir 内
    "agent": {
        "enabled": False,           # 总开关：是否允许模型调用本地工具
        "workspace_dir": "",        # 本地办公路径（留空则用 data/sandbox）
        "enable_files": True,       # 文件工具：列 / 读 / 写 / 删
        "enable_shell": False,      # 受限命令工具（白名单）
        "shell_whitelist": "python, py, dir, type, where, echo, hostname, whoami",
        "require_confirm": True,    # 写 / 删 / 执行命令前弹窗确认
        "max_tool_turns": 8,        # 一轮问答最多连续工具调用次数
    },
    # AI 眼睛：把真实截图 / 图片交给多模态模型（不是 OCR 文本提取）
    "vision": {
        "enabled": True,            # 是否显示「AI 眼睛」入口
    },
}

MAX_HISTORY = 200


# ---------------------------------------------------------------- 目录

def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _ensure_dir(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def data_dir() -> str:
    return _ensure_dir(os.path.join(app_dir(), DATA_DIR_NAME))


def chat_dir() -> str:
    return _ensure_dir(os.path.join(data_dir(), CHAT_DIR_NAME))


def config_path() -> str:
    return os.path.join(data_dir(), CONFIG_NAME)


# ---------------------------------------------------------------- 合并

def _merge(base: dict, data: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in data.items():
        if isinstance(out.get(key), dict) and isinstance(value, dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _migrate_legacy() -> None:
    """旧 ai_chat_config.json → data/config.json（去掉 api_key 字段）。"""
    legacy = os.path.join(app_dir(), LEGACY_CONFIG_NAME)
    if not os.path.exists(legacy):
        return
    if os.path.exists(config_path()):
        return
    try:
        with open(legacy, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return
        data.pop("api_key", None)
        if isinstance(data.get("search"), dict):
            data["search"].pop("api_key", None)
        with open(config_path(), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except (OSError, json.JSONDecodeError):
        pass


# ---------------------------------------------------------------- 读写

def load_config() -> dict:
    _migrate_legacy()
    try:
        with open(config_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return copy.deepcopy(DEFAULTS)
    if not isinstance(data, dict):
        return copy.deepcopy(DEFAULTS)
    return _merge(DEFAULTS, data)


def save_config(cfg: dict) -> bool:
    try:
        with open(config_path(), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def remove_config() -> None:
    try:
        os.remove(config_path())
    except OSError:
        pass


def reset_config() -> dict:
    """彻底重置配置到默认值并写盘。"""
    cfg = copy.deepcopy(DEFAULTS)
    save_config(cfg)
    return cfg


def open_data_dir() -> str:
    """在文件管理器中打开 data 目录。"""
    path = data_dir()
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception:
        pass
    return path