# ai_chat/keys.py
"""API Key 独立存储：data/keys.json"""
from __future__ import annotations

import json
import os

from .config import app_dir, data_dir

KEY_FILE = "keys.json"
LEGACY_KEY_FILE = "key-api.json"


def keys_path() -> str:
    return os.path.join(data_dir(), KEY_FILE)


def _ai_ids() -> list[str]:
    from .providers import PROVIDERS
    return [p.id for p in PROVIDERS if p.id != "ollama"]


def _search_ids() -> list[str]:
    from .search import NEEDS_KEY
    return sorted(NEEDS_KEY)


def _empty_skeleton() -> dict:
    return {
        "ai": {pid: "" for pid in _ai_ids()},
        "search": {sid: "" for sid in _search_ids()},
    }


def _normalize(data: dict) -> dict:
    out = _empty_skeleton()
    if not isinstance(data, dict):
        return out
    for section in ("ai", "search"):
        block = data.get(section)
        if isinstance(block, dict):
            for k, v in block.items():
                out[section][k] = "" if v is None else str(v)
    return out


def _migrate_legacy() -> None:
    legacy = os.path.join(app_dir(), LEGACY_KEY_FILE)
    if not os.path.exists(legacy):
        return
    if os.path.exists(keys_path()):
        return
    try:
        with open(legacy, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        with open(keys_path(), "w", encoding="utf-8") as fh:
            json.dump(_normalize(data), fh, ensure_ascii=False, indent=2)
    except (OSError, json.JSONDecodeError):
        pass


def load_keys() -> dict:
    _migrate_legacy()
    path = keys_path()
    if not os.path.exists(path):
        skeleton = _empty_skeleton()
        save_keys(skeleton)
        return skeleton
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return _empty_skeleton()
    return _normalize(data)


def save_keys(keys: dict) -> bool:
    try:
        with open(keys_path(), "w", encoding="utf-8") as fh:
            json.dump(_normalize(keys), fh, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def get_ai_key(keys: dict, provider_id: str) -> str:
    return (keys.get("ai", {}).get(provider_id) or "").strip()


def get_search_key(keys: dict, provider_id: str) -> str:
    return (keys.get("search", {}).get(provider_id) or "").strip()


def set_ai_key(keys: dict, provider_id: str, value: str) -> None:
    keys.setdefault("ai", {})[provider_id] = (value or "").strip()


def set_search_key(keys: dict, provider_id: str, value: str) -> None:
    keys.setdefault("search", {})[provider_id] = (value or "").strip()


def migrate_from_config(cfg: dict, keys: dict) -> tuple[dict, dict, bool]:
    """把旧 config 里的 api_key 迁移到 keys。"""
    changed = False

    old_ai = (cfg.get("api_key") or "").strip()
    if old_ai:
        pid = cfg.get("provider", "custom")
        if not get_ai_key(keys, pid):
            set_ai_key(keys, pid, old_ai)
        changed = True
    if "api_key" in cfg:
        cfg.pop("api_key", None)
        changed = True

    search = cfg.get("search")
    if isinstance(search, dict):
        old_search = (search.get("api_key") or "").strip()
        if old_search:
            sid = search.get("provider", "duckduckgo")
            if not get_search_key(keys, sid):
                set_search_key(keys, sid, old_search)
            changed = True
        if "api_key" in search:
            search.pop("api_key", None)
            changed = True

    return cfg, keys, changed