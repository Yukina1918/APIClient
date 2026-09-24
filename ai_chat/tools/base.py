# ai_chat/tools/base.py
"""工具基类、执行结果与注册表（OpenAI Function Calling 格式）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .sandbox import Sandbox


@dataclass
class ToolResult:
    """一次工具执行的结果，content 会作为 role=tool 消息回传给模型。"""
    ok: bool
    content: str
    data: dict = field(default_factory=dict)

    @staticmethod
    def success(content: str, **data: Any) -> "ToolResult":
        return ToolResult(True, content, data)

    @staticmethod
    def failure(content: str, **data: Any) -> "ToolResult":
        return ToolResult(False, content, data)


class Tool:
    """所有工具的基类。

    子类需要设置：
      name         —— 模型调用时用的函数名
      description  —— 给模型看的说明
      parameters   —— JSON Schema（OpenAI parameters 字段）
      dangerous     —— True 时执行前必须人工确认（写 / 删 / 执行命令）
    """
    name: str = ""
    description: str = ""
    parameters: dict = {"type": "object", "properties": {}}
    dangerous: bool = False

    def __init__(self, sandbox: Sandbox | None = None,
                 config: dict | None = None) -> None:
        self.sandbox = sandbox
        self.config = config or {}

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def describe(self, arguments: dict) -> str:
        """给人工确认弹窗看的一句话描述，子类可覆盖。"""
        return "%s %s" % (self.name, arguments)

    def execute(self, arguments: dict) -> ToolResult:  # pragma: no cover
        raise NotImplementedError

    # 工具内部常用小工具 ------------------------------------------------

    @staticmethod
    def _arg(arguments: dict, key: str, default=None):
        value = arguments.get(key, default)
        return value if value is not None else default

    @staticmethod
    def _truncate(text: str, limit: int = 6000) -> str:
        text = text or ""
        if len(text) <= limit:
            return text
        head = text[:limit]
        return head + "\n…(输出过长，已截断，共 %d 字符)" % len(text)


class ToolRegistry:
    """按名注册 / 查找 / 执行工具。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def add(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("工具缺少 name")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self._tools.values()]

    def is_dangerous(self, name: str) -> bool:
        tool = self._tools.get(name)
        return bool(tool and tool.dangerous)

    def describe(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return name
        try:
            return tool.describe(arguments)
        except Exception:
            return "%s %s" % (name, arguments)

    def execute(self, name: str, arguments: dict) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.failure("未知工具：%s" % name)
        if not isinstance(arguments, dict):
            return ToolResult.failure("工具参数必须是 JSON 对象")
        try:
            result = tool.execute(arguments)
        except Exception as exc:
            return ToolResult.failure("工具执行异常：%s" % exc)
        if not isinstance(result, ToolResult):
            return ToolResult.failure("工具返回格式错误")
        return result


# 确认回调：(工具名, 参数dict) -> bool；由 GUI 弹窗 / CLI y/n 实现
ConfirmCallback = Callable[[str, dict], bool]
