# ai_chat/vision.py
"""AI 眼睛：真实视觉采集（不是 OCR 文本提取）。

把整屏截图或本地图片转成 base64 data URL，按 OpenAI 多模态格式放进消息：

    content = [
        {"type": "text", "text": "..."},
        {"type": "image_url",
         "image_url": {"url": "data:image/png;base64,...."}},
    ]

截屏后端：
  · Windows：ctypes + GDI（BitBlt / GetDIBits），并用标准库 zlib 手写 PNG
  · Linux：grim(Wayland) / scrot / ImageMagick import / gnome-screenshot / maim
  · macOS：screencrap
"""
from __future__ import annotations

import base64
import os
import struct
import subprocess
import sys
import tempfile
import zlib

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
    """截屏 / 读图失败。"""


# ---------------------------------------------------------------- PNG 编码

def _encode_png_rgb(bgra: bytes, w: int, h: int) -> bytes:
    """把 32 位 BGRA 像素手写编码成 8-bit RGB PNG（仅标准库 zlib）。"""
    raw = bytearray()
    row_bytes = w * 4
    for y in range(h):
        raw.append(0)  # filter type 0
        row = bgra[y * row_bytes:(y + 1) * row_bytes]
        rgb_row = bytearray(w * 3)
        rgb_row[0::3] = row[2::4]   # R
        rgb_row[1::3] = row[1::4]   # G
        rgb_row[2::3] = row[0::4]   # B
        raw.extend(rgb_row)

    def chunk(tag: bytes, data: bytes) -> bytes:
        head = tag + data
        crc = zlib.crc32(head) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + head + struct.pack(">I", crc)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8bit, color type 2
    idat = zlib.compress(bytes(raw), 6)
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) \
        + chunk(b"IEND", b"")


# ---------------------------------------------------------------- Windows

def _capture_windows() -> tuple[bytes, str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    c_void_p = ctypes.c_void_p

    # 64 位安全：句柄函数必须声明指针返回 / 参数
    user32.GetDC.restype = c_void_p
    user32.GetDC.argtypes = [c_void_p]
    user32.ReleaseDC.argtypes = [c_void_p, c_void_p]
    gdi32.CreateCompatibleDC.restype = c_void_p
    gdi32.CreateCompatibleDC.argtypes = [c_void_p]
    gdi32.CreateCompatibleBitmap.restype = c_void_p
    gdi32.CreateCompatibleBitmap.argtypes = [c_void_p, ctypes.c_int,
                                             ctypes.c_int]
    gdi32.SelectObject.restype = c_void_p
    gdi32.SelectObject.argtypes = [c_void_p, c_void_p]
    gdi32.BitBlt.argtypes = [c_void_p, ctypes.c_int, ctypes.c_int,
                             ctypes.c_int, ctypes.c_int, c_void_p,
                             ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
    gdi32.GetDIBits.argtypes = [c_void_p, c_void_p, ctypes.c_uint,
                                ctypes.c_uint, c_void_p, c_void_p,
                                ctypes.c_uint]
    gdi32.DeleteObject.argtypes = [c_void_p]
    gdi32.DeleteDC.argtypes = [c_void_p]

    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    if width <= 0 or height <= 0:
        raise VisionError("VISION_BAD_SCREEN_SIZE")

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    screen_dc = user32.GetDC(0)
    mem_dc = gdi32.CreateCompatibleDC(screen_dc)
    bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
    gdi32.SelectObject(mem_dc, bitmap)
    # 0x00CC0020 == SRCCOPY
    ok = gdi32.BitBlt(mem_dc, 0, 0, width, height, screen_dc, 0, 0,
                      0x00CC0020)

    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth = width
    bi.biHeight = -height       # 自上而下
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0        # BI_RGB

    buf = ctypes.create_string_buffer(width * height * 4)
    scanned = gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf,
                              ctypes.byref(bi), 0) if ok else 0

    # 清理 GDI 资源
    try:
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(0, screen_dc)
    except Exception:
        pass

    if not ok or scanned == 0:
        raise VisionError("VISION_CAPTURE_FAILED")

    png = _encode_png_rgb(buf.raw, width, height)
    return png, "image/png"


# ---------------------------------------------------------------- Linux/macOS

def _capture_linux() -> tuple[bytes, str]:
    # Wayland：grim 直接把 PNG 写到 stdout
    if _which("grim"):
        proc = subprocess.run(["grim", "-"], capture_output=True)
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout, "image/png"

    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    commands = (
        ["scrot", "-o", path],
        ["maim", path],
        ["import", "-window", "root", path],
        ["gnome-screenshot", "-f", path],
        ["xwd", "-root", "-silent", "-out", path],
    )
    try:
        for cmd in commands:
            if _which(cmd[0]):
                proc = subprocess.run(cmd, capture_output=True)
                if proc.returncode == 0 and os.path.exists(path) \
                        and os.path.getsize(path) > 0:
                    with open(path, "rb") as fh:
                        data = fh.read()
                    # xwd 不是 PNG；其它工具默认输出 PNG
                    if cmd[0] == "xwd":
                        continue
                    return data, "image/png"
        raise VisionError("VISION_NO_CAPTURE_BACKEND")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _capture_macos() -> tuple[bytes, str]:
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        proc = subprocess.run(["screencapture", "-x", path],
                              capture_output=True)
        if proc.returncode == 0 and os.path.getsize(path) > 0:
            with open(path, "rb") as fh:
                return fh.read(), "image/png"
        raise VisionError("VISION_CAPTURE_FAILED")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _which(name: str) -> str | None:
    from shutil import which
    return which(name)


# ---------------------------------------------------------------- 对外接口

def capture_screen() -> tuple[bytes, str]:
    """截取主屏幕，返回 (图片字节, MIME)。"""
    if sys.platform == "win32":
        return _capture_windows()
    if sys.platform == "darwin":
        return _capture_macos()
    return _capture_linux()


def read_image_file(path: str) -> tuple[bytes, str]:
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        raise VisionError("VISION_READ_FAILED: %s" % exc) from exc
    ext = os.path.splitext(path)[1].lower()
    return data, MIME_BY_EXT.get(ext, "image/png")


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
