# ai_chat/vision.py
"""图灵识别：真实视觉采集（不是 OCR 文本提取）。

把剪贴板里的图片（截图后直接 Ctrl+C / 微信 QQ 复制 / 系统截图）或本地图片
转成 base64 data URL，按 OpenAI 多模态格式放进消息：

    content = [
        {"type": "text", "text": "..."},
        {"type": "image_url",
         "image_url": {"url": "data:image/png;base64,...."}},
    ]

图片来源：
  · read_clipboard_image()：直接读取系统剪贴板里的图片（无需找文件）
  · read_image_file(path)：选择本地图片文件
"""
from __future__ import annotations

import base64
import os

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}


class VisionError(RuntimeError):
    """读取剪贴板 / 读图失败。"""


# ---------------------------------------------------------------- 剪贴板

def qimage_to_bytes(qimage, fmt: str = "PNG") -> tuple[bytes, str]:
    """把 QImage 编码成 (图片字节, MIME)。"""
    from PyQt6.QtCore import QBuffer, QByteArray, QIODevice

    if qimage is None or qimage.isNull():
        raise VisionError("VISION_NO_IMAGE")

    ba = QByteArray()
    buf = QBuffer(ba)
    if not buf.open(QIODevice.OpenModeFlag.WriteOnly):
        raise VisionError("VISION_ENCODE_FAILED")
    ok = qimage.save(buf, fmt)
    buf.close()
    if not ok:
        raise VisionError("VISION_ENCODE_FAILED")

    mime = "image/png" if fmt.upper() == "PNG" else "image/jpeg"
    return bytes(ba), mime


def read_clipboard_image() -> tuple[bytes, str]:
    """读取系统剪贴板里的图片，返回 (图片字节, MIME)。

    剪贴板没有图片时抛 VisionError("VISION_NO_IMAGE_IN_CLIPBOARD")。
    """
    from PyQt6.QtWidgets import QApplication

    clipboard = QApplication.clipboard()
    if clipboard is None:
        raise VisionError("VISION_NO_CLIPBOARD")

    image = clipboard.image()
    if image is None or image.isNull():
        raise VisionError("VISION_NO_IMAGE_IN_CLIPBOARD")
    return qimage_to_bytes(image, "PNG")


def clipboard_has_image() -> bool:
    from PyQt6.QtWidgets import QApplication

    clipboard = QApplication.clipboard()
    if clipboard is None:
        return False
    mime = clipboard.mimeData()
    if mime is not None and mime.hasImage():
        return True
    image = clipboard.image()
    return image is not None and not image.isNull()


# ---------------------------------------------------------------- 本地文件

def read_image_file(path: str) -> tuple[bytes, str]:
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        raise VisionError("VISION_READ_FAILED: %s" % exc) from exc
    ext = os.path.splitext(path)[1].lower()
    return data, MIME_BY_EXT.get(ext, "image/png")


# ---------------------------------------------------------------- 多模态组装

def to_data_url(data: bytes, mime: str) -> str:
    return "data:%s;base64,%s" % (
        mime, base64.b64encode(data).decode("ascii"))


def build_multimodal_content(text: str,
                             images: list[tuple[bytes, str]]) -> list[dict]:
    """把文本 + 若干图片组装成多模态 content 列表。"""
    parts: list[dict] = [{"type": "text",
                          "text": text or "请描述并分析这张图片。"}]
    for data, mime in images:
        parts.append({
            "type": "image_url",
            "image_url": {"url": to_data_url(data, mime)},
        })
    return parts
