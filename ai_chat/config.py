# ai_chat/config.py
"""配置读写：所有文件统一放在 data/ 目录下。"""
from __future__ import annotations

import copy
import json
import os
import sys

APP_NAME = "AI Chat"
APP_VERSION = "3.0"
DATA_DIR_NAME = "data"
CONFIG_NAME = "config.json"
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
}

MAX_HISTORY = 200


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


def logs_dir() -> str:
    return _ensure_dir(os.path.join(data_dir(), "logs"))


def config_path() -> str:
    return os.path.join(data_dir(), CONFIG_NAME)


def _merge(base: dict, data: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in data.items():
        if isinstance(out.get(key), dict) and isinstance(value, dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _migrate_legacy() -> None:
    """旧 ai_chat_config.json → data/config.json（去掉 api_key 字段）"""
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