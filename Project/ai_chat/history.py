"""会话历史存储模块，自定义txt日志格式；图片路径 data/chat/{id}/images/"""
from __future__ import annotations
import os
import re
import uuid
from datetime import datetime
from .config import data_dir

DEFAULT_NAME = "新话题"

def new_id() -> str:
    return str(uuid.uuid4())


class ChatLog:
    def __init__(self, id: str, name: str, messages: list[dict]):
        self.id = id
        self.name = name
        self.messages: list[dict] = messages

    def session_dir(self) -> str:
        """该会话专属文件夹：data/chat/{id}/"""
        return os.path.join(data_dir(), "chat", self.id)

    def log_dir(self) -> str:
        """兼容旧调用：返回会话专属文件夹（自动创建）。"""
        d = self.session_dir()
        os.makedirs(d, exist_ok=True)
        return d

    def log_file_path(self) -> str:
        """聊天记录 txt 放在会话文件夹内：data/chat/{id}/{id}.txt"""
        return os.path.join(self.session_dir(), f"{self.id}.txt")

    def images_dir(self) -> str:
        d = os.path.join(self.session_dir(), "images")
        os.makedirs(d, exist_ok=True)
        return d

    def get_image_path(self, index: int) -> str:
        return os.path.join(self.images_dir(), f"{index}.png")


def _read_meta(log_id: str, fp: str) -> ChatLog:
    name = DEFAULT_NAME
    try:
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s.startswith('name='):
                    name = s.split('"')[1]
                    break
    except Exception:
        pass
    return ChatLog(id=log_id, name=name, messages=[])


def _migrate_old_txt(sess_root: str, log_id: str, old_path: str) -> str:
    """把旧的平铺 data/chat/{id}.txt 移到 data/chat/{id}/{id}.txt。"""
    new_dir = os.path.join(sess_root, log_id)
    os.makedirs(new_dir, exist_ok=True)
    new_path = os.path.join(new_dir, f"{log_id}.txt")
    if not os.path.exists(new_path):
        try:
            os.rename(old_path, new_path)
        except OSError:
            pass
    return new_path


def list_logs() -> list[ChatLog]:
    """列出全部会话（每个会话一个文件夹，内含 {id}.txt），按修改时间倒序。"""
    sess_root = os.path.join(data_dir(), "chat")
    os.makedirs(sess_root, exist_ok=True)
    out: list[ChatLog] = []
    for entry in os.scandir(sess_root):
        if entry.is_dir(follow_symlinks=False):
            log_id = entry.name
            fp = os.path.join(entry.path, f"{log_id}.txt")
            if os.path.exists(fp):
                out.append(_read_meta(log_id, fp))
        elif entry.name.endswith(".txt"):
            # 兼容旧结构：平铺在 chat 根目录的 {id}.txt
            log_id = entry.name[:-4]
            new_path = _migrate_old_txt(sess_root, log_id, entry.path)
            out.append(_read_meta(log_id, new_path))
    out.sort(key=lambda x: os.path.getmtime(x.log_file_path()), reverse=True)
    return out


def save_log(log: ChatLog):
    """保存会话到txt，严格按照自定义模板格式"""
    log_path = log.log_file_path()
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    now_str = datetime.now().strftime("%Y/%m/%d‑%H:%M")
    log_lines = []
    for m in log.messages:
        role = m.get("role", "")
        txt = (m.get("content") or "").replace('"', '\\"')
        attach_cnt = m.get("attach_count", 0)
        if role == "user":
            log_lines.append(f'\tMe="{txt}"')
            if attach_cnt > 0:
                attach_str = "".join(["[图片]"] * attach_cnt)
                log_lines.append(f'\tMeAttachment="{attach_str}"')
        elif role == "assistant":
            log_lines.append(f'\tAI="{txt}"')
        elif role == "system":
            log_lines.append(f'\tSystem="{txt}"')
    log_block = "\n".join(log_lines)
    content = f'''name="{log.name}"
time="{now_str}"
log="
{log_block}
"
'''
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(content)


def load_log(log_id: str) -> ChatLog | None:
    """读取自定义格式txt会话记录，返回ChatLog对象"""
    log = ChatLog(id=log_id, name=DEFAULT_NAME, messages=[])
    fp = log.log_file_path()
    if not os.path.exists(fp):
        # 兼容旧平铺路径：data/chat/{id}.txt
        old_fp = os.path.join(data_dir(), "chat", f"{log_id}.txt")
        if os.path.exists(old_fp):
            fp = _migrate_old_txt(os.path.join(data_dir(), "chat"),
                                  log_id, old_fp)
        else:
            return None
    with open(fp, "r", encoding="utf-8") as f:
        raw = f.read()
    lines = raw.splitlines()
    msg_list = []
    for line in lines:
        s = line.strip()
        if s.startswith('name='):
            log.name = s.split('"')[1]
        elif s.startswith('Me="'):
            content = s.split('"')[1]
            msg_list.append({"role": "user", "content": content, "attach_count": 0})
        elif s.startswith('MeAttachment="'):
            attach_raw = s.split('"')[1]
            matches = re.findall(r"\[(.*?)\]", attach_raw)
            if msg_list and msg_list[-1]["role"] == "user":
                msg_list[-1]["attach_count"] = len(matches)
        elif s.startswith('AI="'):
            content = s.split('"')[1]
            msg_list.append({"role": "assistant", "content": content})
        elif s.startswith('System="'):
            content = s.split('"')[1]
            msg_list.append({"role": "system", "content": content})
    log.messages = msg_list
    return log


def save_artifact(log: ChatLog, ext: str, content: str):
    """保存agent输出的文件工件"""
    import time
    fn = f"artifact_{time.strftime('%Y%m%d_%H%M%S')}.{ext}"
    art_dir = os.path.join(log.session_dir(), "artifacts")
    os.makedirs(art_dir, exist_ok=True)
    path = os.path.join(art_dir, fn)
    with open(path, "w", encoding="utf‑8") as f:
        f.write(content)


def make_title_from(text: str, limit=24) -> str:
    """从用户提问生成会话标题"""
    clean = text.strip().replace("\n", " ")
    if len(clean) <= limit:
        return clean or DEFAULT_NAME
    return clean[:limit] + "…"
