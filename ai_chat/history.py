# ai_chat/history.py
"""聊天记录：log-<24位数字>.txt 保存在 data/logs/。"""
from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field

from .config import logs_dir

USER_PREFIX = "用户: "
AI_PREFIX = "AI: "

DEFAULT_NAME = "新话题"


@dataclass
class ChatLog:
    id: str
    name: str = DEFAULT_NAME
    messages: list = field(default_factory=list)

    @property
    def path(self) -> str:
        return os.path.join(logs_dir(), f"log-{self.id}.txt")


def new_id() -> str:
    """24 位纯数字 ID：13 位毫秒 + 11 位随机。"""
    ms = int(time.time() * 1000)
    suffix = random.randint(10_000_000_000, 99_999_999_999)
    return f"{ms}{suffix}"


def _encode(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\n")


def _decode(text: str) -> str:
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "\\" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _is_valid_id(log_id: str) -> bool:
    return len(log_id) == 24 and log_id.isdigit()


def _parse(path: str) -> ChatLog | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return None

    base = os.path.basename(path)
    if not (base.startswith("log-") and base.endswith(".txt")):
        return None
    log_id = base[4:-4]
    if not _is_valid_id(log_id):
        return None

    lines = content.split("\n")
    name = lines[0].strip() if lines else DEFAULT_NAME
    if not name:
        name = DEFAULT_NAME

    messages: list[dict] = []
    for raw in lines[1:]:
        if not raw:
            continue
        if raw.startswith(USER_PREFIX):
            messages.append({
                "role": "user",
                "content": _decode(raw[len(USER_PREFIX):]),
            })
        elif raw.startswith(AI_PREFIX):
            messages.append({
                "role": "assistant",
                "content": _decode(raw[len(AI_PREFIX):]),
            })

    return ChatLog(id=log_id, name=name, messages=messages)


def list_logs() -> list[ChatLog]:
    directory = logs_dir()
    try:
        files = [f for f in os.listdir(directory)
                 if f.startswith("log-") and f.endswith(".txt")]
    except OSError:
        return []

    entries = []
    for fname in files:
        full = os.path.join(directory, fname)
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            mtime = 0
        entries.append((mtime, full))
    entries.sort(reverse=True)

    logs: list[ChatLog] = []
    for _mtime, path in entries:
        log = _parse(path)
        if log is not None:
            logs.append(log)
    return logs


def load_log(log_id: str) -> ChatLog | None:
    if not _is_valid_id(log_id):
        return None
    path = os.path.join(logs_dir(), f"log-{log_id}.txt")
    if not os.path.exists(path):
        return None
    return _parse(path)


def save_log(log: ChatLog) -> bool:
    try:
        lines = [log.name or DEFAULT_NAME]
        for msg in log.messages:
            role = msg.get("role", "")
            content = _encode(msg.get("content", "") or "")
            if role == "user":
                lines.append(USER_PREFIX + content)
            elif role == "assistant":
                lines.append(AI_PREFIX + content)
        with open(log.path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        return True
    except OSError:
        return False


def delete_log(log_id: str) -> bool:
    if not _is_valid_id(log_id):
        return False
    path = os.path.join(logs_dir(), f"log-{log_id}.txt")
    try:
        os.remove(path)
        return True
    except OSError:
        return False