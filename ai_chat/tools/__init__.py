# ai_chat/tools/__init__.py
"""工具系统：沙箱文件工具 + 受限命令工具。

用法：
    from .tools import build_registry
    registry = build_registry(agent_cfg)   # agent_cfg 见 config.DEFAULTS["agent"]
"""
from __future__ import annotations

import os

from .base import (ConfirmCallback, Tool, ToolRegistry, ToolResult)
from .files import (DeleteFileTool, ListFilesTool, ReadFileTool, WriteFileTool)
from .sandbox import Sandbox, SandboxError
from .shell import ShellTool


def default_sandbox_dir() -> str:
    """默认沙箱：data/sandbox（仍在软件数据目录内）。"""
    from ..config import data_dir
    return os.path.join(data_dir(), "sandbox")


def build_registry(agent_cfg: dict) -> tuple[ToolRegistry, Sandbox]:
    """根据 agent 配置构建工具注册表与沙箱。

    开关：
      enable_files —— 文件工具（列/读/写/删）
      enable_shell —— 受限命令工具（默认关闭）
    """
    root = (agent_cfg.get("workspace_dir") or agent_cfg.get("sandbox_dir")
            or "").strip() or default_sandbox_dir()
    sandbox = Sandbox(root)
    registry = ToolRegistry()

    if agent_cfg.get("enable_files", True):
        registry.add(ListFilesTool(sandbox, agent_cfg))
        registry.add(ReadFileTool(sandbox, agent_cfg))
        registry.add(WriteFileTool(sandbox, agent_cfg))
        registry.add(DeleteFileTool(sandbox, agent_cfg))

    if agent_cfg.get("enable_shell", False):
        registry.add(ShellTool(sandbox, agent_cfg))

    return registry, sandbox


__all__ = [
    "build_registry", "default_sandbox_dir",
    "Sandbox", "SandboxError",
    "Tool", "ToolRegistry", "ToolResult", "ConfirmCallback",
]
