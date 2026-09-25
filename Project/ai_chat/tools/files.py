# ai_chat/tools/files.py
"""文件工具：列目录 / 读 / 写 / 删，全部锁在沙箱内。"""
from __future__ import annotations

import os
import shutil

from .base import Tool, ToolResult
from .sandbox import SandboxError

MAX_READ_BYTES = 200 * 1024      # 单次读取上限 200KB
MAX_WRITE_BYTES = 200 * 1024     # 单次写入上限 200KB


class ListFilesTool(Tool):
    name = "list_files"
    description = (
        "列出沙箱中某个目录下的文件和子目录。"
        "path 为相对沙箱根的路径，留空或填 \".\" 表示沙箱根目录。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "相对沙箱根的目录路径，默认根目录",
            },
        },
    }
    dangerous = False

    def execute(self, arguments: dict) -> ToolResult:
        assert self.sandbox is not None
        rel = self._arg(arguments, "path", ".") or "."
        try:
            target = self.sandbox.resolve(rel)
        except SandboxError as exc:
            return ToolResult.failure("路径被拒绝：%s" % exc)

        if not os.path.exists(target):
            return ToolResult.failure("目录不存在：%s" % rel)
        if not os.path.isdir(target):
            return ToolResult.failure("不是目录：%s" % rel)

        lines = []
        try:
            entries = sorted(os.listdir(target))
        except OSError as exc:
            return ToolResult.failure("无法读取目录：%s" % exc)

        for name in entries:
            full = os.path.join(target, name)
            try:
                if os.path.isdir(full):
                    lines.append("[目录] %s/" % name)
                else:
                    size = os.path.getsize(full)
                    lines.append("[文件] %-30s %8d 字节" % (name, size))
            except OSError:
                lines.append("[???] %s" % name)

        if not lines:
            return ToolResult.success("（目录为空）")
        body = "目录 %s 下共 %d 项：\n%s" % (
            self.sandbox.relative(target) or ".", len(lines), "\n".join(lines))
        return ToolResult.success(body)


class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "读取沙箱内的文本文件内容。path 为相对沙箱根的路径。"
        "只能读取 UTF-8 文本，二进制文件会被拒绝。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "相对沙箱根的文件路径"},
        },
        "required": ["path"],
    }
    dangerous = False

    def execute(self, arguments: dict) -> ToolResult:
        assert self.sandbox is not None
        rel = self._arg(arguments, "path", "")
        if not rel:
            return ToolResult.failure("缺少参数 path")
        try:
            target = self.sandbox.resolve(rel)
        except SandboxError as exc:
            return ToolResult.failure("路径被拒绝：%s" % exc)

        if not os.path.exists(target):
            return ToolResult.failure("文件不存在：%s" % rel)
        if os.path.isdir(target):
            return ToolResult.failure("是目录而非文件，请用 list_files：%s" % rel)

        try:
            size = os.path.getsize(target)
        except OSError as exc:
            return ToolResult.failure("无法获取文件信息：%s" % exc)
        if size > MAX_READ_BYTES:
            return ToolResult.failure(
                "文件过大（%d 字节），读取上限 %d 字节" % (size, MAX_READ_BYTES))

        try:
            with open(target, "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            return ToolResult.failure("读取失败：%s" % exc)

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return ToolResult.failure("疑似二进制/非 UTF-8 文件，无法读取")
        return ToolResult.success(self._truncate(text), path=rel)


class WriteFileTool(Tool):
    name = "write_file"
    description = (
        "向沙箱内写入文本文件（覆盖已存在的文件，不存在则创建，"
        "父目录不存在会自动创建）。path 为相对沙箱根的路径。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "相对沙箱根的文件路径"},
            "content": {"type": "string", "description": "要写入的完整文本内容"},
        },
        "required": ["path", "content"],
    }
    dangerous = True

    def describe(self, arguments: dict) -> str:
        return "写入文件 %s（%d 字符）" % (
            arguments.get("path", "?"), len(arguments.get("content", "") or ""))

    def execute(self, arguments: dict) -> ToolResult:
        assert self.sandbox is not None
        rel = self._arg(arguments, "path", "")
        content = self._arg(arguments, "content", "")
        if not rel:
            return ToolResult.failure("缺少参数 path")
        if content is None:
            content = ""
        content = str(content)
        if len(content.encode("utf-8", "replace")) > MAX_WRITE_BYTES:
            return ToolResult.failure("内容超过写入上限 %d 字节" % MAX_WRITE_BYTES)

        try:
            target = self.sandbox.resolve(rel)
            self.sandbox.ensure_parent(target)
        except SandboxError as exc:
            return ToolResult.failure("路径被拒绝：%s" % exc)

        if os.path.isdir(target):
            return ToolResult.failure("目标已是目录：%s" % rel)
        if os.path.exists(target):
            try:
                os.replace(target, target + ".bak")
            except OSError:
                pass

        try:
            with open(target, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
        except OSError as exc:
            return ToolResult.failure("写入失败：%s" % exc)
        return ToolResult.success("已写入 %s（%d 字符）" % (rel, len(content)),
                                  path=rel)


class DeleteFileTool(Tool):
    name = "delete_file"
    description = (
        "删除沙箱内的文件；仅当目录为空时才能删除目录。"
        "path 为相对沙箱根的路径。此操作不可恢复。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "相对沙箱根的文件路径"},
        },
        "required": ["path"],
    }
    dangerous = True

    def describe(self, arguments: dict) -> str:
        return "删除 %s" % arguments.get("path", "?")

    def execute(self, arguments: dict) -> ToolResult:
        assert self.sandbox is not None
        rel = self._arg(arguments, "path", "")
        if not rel:
            return ToolResult.failure("缺少参数 path")
        try:
            target = self.sandbox.resolve(rel)
        except SandboxError as exc:
            return ToolResult.failure("路径被拒绝：%s" % exc)

        if not os.path.exists(target):
            return ToolResult.failure("文件不存在：%s" % rel)

        try:
            if os.path.isdir(target):
                # 只允许删空目录，杜绝递归删除
                if os.listdir(target):
                    return ToolResult.failure("目录非空，拒绝删除：%s" % rel)
                os.rmdir(target)
            else:
                os.remove(target)
        except OSError as exc:
            return ToolResult.failure("删除失败：%s" % exc)
        return ToolResult.success("已删除 %s" % rel, path=rel)
