# ai_chat/history.py
"""聊天记录：chat_<24位数字>.txt，保存在 data/chat/。

文件格式：
    标题:<标题>
    me:<用户消息>
    AI:<AI 回复>
    system:<系统信息，比如联网搜索结果>

换行使用 \\n 转义，反斜杠使用 \\\\ 转义。
"""
from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field

from .config import chat_dir

TITLE_PREFIX = "标题:"
USER_PREFIX = "me:"
AI_PREFIX = "AI:"
SYS_PREFIX = "system:"

DEFAULT_NAME = "新话题"


@dataclass
class ChatLog:
    id: str
    name: str = DEFAULT_NAME
    messages: list = field(default_factory=list)  # [{"role": ..., "content": ...}]

    @property
    def path(self) -> str:
        return os.path.join(chat_dir(), f"chat_{self.id}.txt")


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
    if not (base.startswith("chat_") and base.endswith(".txt")):
        return None
    log_id = base[5:-4]
    if not _is_valid_id(log_id):
        return None

    lines = content.split("\n")
    name = DEFAULT_NAME
    messages: list[dict] = []

    for raw in lines:
        if not raw:
            continue
        if raw.startswith(TITLE_PREFIX):
            name = _decode(raw[len(TITLE_PREFIX):]).strip() or DEFAULT_NAME
        elif raw.startswith(USER_PREFIX):
            messages.append({
                "role": "user",
                "content": _decode(raw[len(USER_PREFIX):]),
            })
        elif raw.startswith(AI_PREFIX):
            messages.append({
                "role": "assistant",
                "content": _decode(raw[len(AI_PREFIX):]),
            })
        elif raw.startswith(SYS_PREFIX):
            messages.append({
                "role": "system",
                "content": _decode(raw[len(SYS_PREFIX):]),
                "meta": "system",
            })

    return ChatLog(id=log_id, name=name, messages=messages)


def list_logs() -> list[ChatLog]:
    directory = chat_dir()
    try:
        files = [f for f in os.listdir(directory)
                 if f.startswith("chat_") and f.endswith(".txt")]
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
    path = os.path.join(chat_dir(), f"chat_{log_id}.txt")
    if not os.path.exists(path):
        return None
    return _parse(path)


def save_log(log: ChatLog) -> bool:
    try:
        lines = [TITLE_PREFIX + _encode(log.name or DEFAULT_NAME)]
        for msg in log.messages:
            role = msg.get("role", "")
            content = _encode(msg.get("content", "") or "")
            if role == "user":
                lines.append(USER_PREFIX + content)
            elif role == "assistant":
                lines.append(AI_PREFIX + content)
            elif role == "system":
                lines.append(SYS_PREFIX + content)
        with open(log.path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        return True
    except OSError:
        return False


def delete_log(log_id: str) -> bool:
    if not _is_valid_id(log_id):
        return False
    path = os.path.join(chat_dir(), f"chat_{log_id}.txt")
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def make_title_from(text: str, limit: int = 20) -> str:
    text = (text or "").strip().replace("\n", " ")
    if not text:
        return DEFAULT_NAME
    return text[:limit] + ("…" if len(text) > limit else "")