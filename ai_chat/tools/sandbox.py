# ai_chat/tools/sandbox.py
"""沙箱：把所有文件操作锁死在指定根目录内。

核心方法 resolve()：
  · 相对路径 → 拼到沙箱根
  · 绝对路径 / 含 .. 的路径 → realpath 规范化后必须仍在沙箱根内
  · 任何穿越尝试（../、符号链接、Windows 盘符跳转）都抛 SandboxError
"""
from __future__ import annotations

import os


class SandboxError(RuntimeError):
    """路径越界或沙箱不可用。"""


class Sandbox:
    def __init__(self, root: str) -> None:
        if not root or not str(root).strip():
            raise SandboxError("SANDBOX_EMPTY")
        self.root = os.path.realpath(os.path.abspath(os.path.expanduser(root)))
        try:
            os.makedirs(self.root, exist_ok=True)
        except OSError as exc:
            raise SandboxError("SANDBOX_CREATE_FAILED: %s" % exc) from exc

    # ------------------------------------------------------------------

    def _is_inside(self, path: str) -> bool:
        try:
            common = os.path.commonpath([self.root, path])
        except ValueError:
            # Windows 下跨盘符会抛 ValueError
            return False
        return common == self.root

    def resolve(self, rel_path: str) -> str:
        """把工具传入的路径解析为沙箱内的绝对路径，越界即拒绝。"""
        if rel_path is None:
            raise SandboxError("PATH_EMPTY")
        rel_path = str(rel_path).strip().replace("\\", "/")
        if not rel_path:
            raise SandboxError("PATH_EMPTY")

        # 明显的非法片段
        if os.path.isabs(rel_path) or rel_path.startswith(("/",)):
            candidate = os.path.realpath(os.path.abspath(rel_path))
        else:
            candidate = os.path.realpath(os.path.join(self.root, rel_path))

        if not self._is_inside(candidate):
            # 不回显具体越界路径，避免给模型多余信息
            raise SandboxError("PATH_OUTSIDE_SANDBOX")
        return candidate

    def relative(self, abs_path: str) -> str:
        """转回相对沙箱根的展示路径（用 / 分隔，跨平台一致）。"""
        abs_path = os.path.realpath(os.path.abspath(abs_path))
        if not self._is_inside(abs_path):
            raise SandboxError("PATH_OUTSIDE_SANDBOX")
        return os.path.relpath(abs_path, self.root).replace("\\", "/")

    def ensure_parent(self, abs_path: str) -> None:
        parent = os.path.dirname(abs_path)
        if not self._is_inside(os.path.realpath(parent)):
            raise SandboxError("PATH_OUTSIDE_SANDBOX")
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as exc:
            raise SandboxError("MKDIR_FAILED: %s" % exc) from exc
