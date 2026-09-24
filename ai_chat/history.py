# ai_chat/history.py
"""聊天记录：每个话题保存为一个独立的「会话文件夹」。

目录结构（data/chat/ 下）：

    <YYYYMMDD>-<HHMM>_<24位小写英数随机数>/
        chat/<id>.txt      聊天正文（标题 / me / AI / system）
        txt/<id>.txt       文本类产出
        json/<id>.json     JSON 产出
        py/<id>.py         Python 产出
        java/<id>.java     Java 产出
        html/<id>.html     HTML 产出
        js/ css/ md/ ...   其它类型，按需自动创建
        screenshots/       AI 眼睛截取的屏幕图片

聊天正文文件格式：
    标题:<标题>
    me:<用户消息>
    AI:<AI 回复>
    system:<系统信息，比如联网搜索结果 / 工具输出>

换行使用 \\n 转义，反斜杠使用 \\\\ 转义。

同时兼容旧版本的单文件 chat_<24位纯数字>.txt（只读加载，可继续保存）。
"""
from __future__ import annotations

import os
import random
import re
import shutil
import time
from dataclasses import dataclass, field

from .config import chat_dir

TITLE_PREFIX = "标题:"
USER_PREFIX = "me:"
AI_PREFIX = "AI:"
SYS_PREFIX = "system:"

DEFAULT_NAME = "新话题"

# 新 ID：20260721-1430_ + 24 位小写英数
NEW_ID_RE = re.compile(r"^\d{8}-\d{4}_[0-9a-z]{24}$")
# 旧 ID：24 位纯数字
OLD_ID_RE = re.compile(r"^\d{24}$")

# 聊天正文固定子目录
CHAT_SUBDIR = "chat"
# 截图子目录
SCREENSHOT_SUBDIR = "screenshots"

# 扩展名 → 产出子文件夹名（未列出的扩展名直接用扩展名自身）
ARTIFACT_TYPES: dict[str, str] = {
    "txt": "txt",
    "json": "json",
    "py": "py",
    "java": "java",
    "html": "html",
    "htm": "html",
    "js": "js",
    "mjs": "js",
    "css": "css",
    "md": "md",
    "markdown": "md",
    "c": "c",
    "h": "h",
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "cs": "cs",
    "go": "go",
    "rs": "rs",
    "rb": "rb",
    "php": "php",
    "sh": "sh",
    "bash": "sh",
    "bat": "bat",
    "cmd": "bat",
    "sql": "sql",
    "xml": "xml",
    "yaml": "yaml",
    "yml": "yaml",
    "toml": "toml",
    "ini": "ini",
    "cfg": "ini",
    "csv": "csv",
    "ts": "ts",
    "tsx": "tsx",
    "jsx": "jsx",
    "vue": "vue",
    "kt": "kt",
    "swift": "swift",
    "r": "r",
    "lua": "lua",
    "pl": "pl",
    "dart": "dart",
    "scala": "scala",
    "rust": "rs",
    "diff": "diff",
    "log": "log",
}

_RANDOM_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


@dataclass
class ChatLog:
    id: str
    name: str = DEFAULT_NAME
    messages: list = field(default_factory=list)  # [{"role": ..., "content": ...}]

    # ---------------------------------------------------------- 路径

    @property
    def is_legacy(self) -> bool:
        return bool(OLD_ID_RE.match(self.id))

    @property
    def folder(self) -> str:
        """会话文件夹（新结构）。"""
        return os.path.join(chat_dir(), self.id)

    @property
    def path(self) -> str:
        """聊天正文文件的完整路径。"""
        if self.is_legacy:
            return os.path.join(chat_dir(), f"chat_{self.id}.txt")
        return os.path.join(self.folder, CHAT_SUBDIR, f"{self.id}.txt")

    def artifact_path(self, ext: str, name: str | None = None) -> str:
        """某类产出文件的完整路径（父目录按需创建）。"""
        ext = ext.lower().lstrip(".")
        sub = ARTIFACT_TYPES.get(ext, ext or "misc")
        folder = os.path.join(self.folder, sub)
        os.makedirs(folder, exist_ok=True)
        fname = name or f"{self.id}.{ext}"
        return os.path.join(folder, fname)

    def screenshot_path(self, name: str | None = None) -> str:
        folder = os.path.join(self.folder, SCREENSHOT_SUBDIR)
        os.makedirs(folder, exist_ok=True)
        fname = name or (time.strftime("%Y%m%d-%H%M%S") + ".png")
        return os.path.join(folder, fname)


# ---------------------------------------------------------------- ID

def new_id() -> str:
    """新会话 ID：<YYYYMMDD>-<HHMM>_<24位小写英数混合随机数>。"""
    stamp = time.strftime("%Y%m%d-%H%M")
    suffix = "".join(random.choice(_RANDOM_ALPHABET) for _ in range(24))
    return f"{stamp}_{suffix}"


def is_new_id(log_id: str) -> bool:
    return bool(NEW_ID_RE.match(log_id or ""))


def _is_valid_id(log_id: str) -> bool:
    return bool(NEW_ID_RE.match(log_id or "") or OLD_ID_RE.match(log_id or ""))


# ---------------------------------------------------------------- 编解码

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


# ---------------------------------------------------------------- 解析

def _parse(txt_path: str) -> ChatLog | None:
    try:
        with open(txt_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return None

    base = os.path.basename(txt_path)
    if base.startswith("chat_") and base.endswith(".txt"):
        log_id = base[5:-4]
    elif base.endswith(".txt"):
        log_id = base[:-4]
    else:
        return None
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
    candidates: list[tuple[float, str]] = []
    try:
        names = os.listdir(directory)
    except OSError:
        return []

    for name in names:
        full = os.path.join(directory, name)
        try:
            if os.path.isdir(full) and is_new_id(name):
                txt = os.path.join(full, CHAT_SUBDIR, name + ".txt")
                if os.path.exists(txt):
                    candidates.append((os.path.getmtime(txt), txt))
            elif os.path.isfile(full) and name.startswith("chat_") \
                    and name.endswith(".txt"):
                candidates.append((os.path.getmtime(full), full))
        except OSError:
            continue

    candidates.sort(key=lambda item: item[0], reverse=True)

    logs: list[ChatLog] = []
    for _mtime, txt_path in candidates:
        log = _parse(txt_path)
        if log is not None:
            logs.append(log)
    return logs


def load_log(log_id: str) -> ChatLog | None:
    if not _is_valid_id(log_id):
        return None
    if OLD_ID_RE.match(log_id):
        txt_path = os.path.join(chat_dir(), f"chat_{log_id}.txt")
    else:
        txt_path = os.path.join(chat_dir(), log_id, CHAT_SUBDIR,
                                f"{log_id}.txt")
    if not os.path.exists(txt_path):
        return None
    return _parse(txt_path)


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
        os.makedirs(os.path.dirname(log.path), exist_ok=True)
        with open(log.path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines))
        return True
    except OSError:
        return False


def save_artifact(log: ChatLog, ext: str, content: str,
                  name: str | None = None) -> str:
    """把一段文本产出按扩展名保存到对应子文件夹，返回文件路径。"""
    path = log.artifact_path(ext, name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    return path


def delete_log(log_id: str) -> bool:
    if not _is_valid_id(log_id):
        return False
    try:
        if OLD_ID_RE.match(log_id):
            os.remove(os.path.join(chat_dir(), f"chat_{log_id}.txt"))
        else:
            shutil.rmtree(os.path.join(chat_dir(), log_id))
        return True
    except OSError:
        return False


def make_title_from(text: str, limit: int = 20) -> str:
    text = (text or "").strip().replace("\n", " ", )
    if not text:
        return DEFAULT_NAME
    return text[:limit] + ("…" if len(text) > limit else "")
