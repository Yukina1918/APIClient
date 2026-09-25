# ai_chat/tools/shell.py
"""受限命令执行工具：白名单程序 + shell=False + 工作目录锁定沙箱。

安全策略（多层）：
  1. 只允许白名单内的可执行程序 / Windows 内置命令
  2. 永远 shell=False，参数以列表传递，杜绝 shell 注入
  3. 命令字符串中出现管道 / 重定向 / 命令分隔 / 命令替换字符 → 直接拒绝
  4. 工作目录强制为沙箱根
  5. 超时强杀，输出截断
"""
from __future__ import annotations

import os
import subprocess
import sys

from .base import Tool, ToolResult

# Windows cmd.exe 内置命令里允许进入白名单的子集（不含 copy/move/del/format 等）
_WIN_BUILTINS = {
    "dir", "type", "echo", "cd", "chdir", "ver", "where",
    "mkdir", "md", "rmdir", "rd", "set", "hostname", "whoami",
}

# 任何命令里出现这些字符一律拒绝（即使作为参数）
_FORBIDDEN_CHARS = ("|", ";", "&", ">", "<", "^", "`", "$(", "\n", "\r",
                    "&&", "||")

DEFAULT_TIMEOUT = 15
MAX_TIMEOUT = 60
MAX_OUTPUT = 6000


def _split_command(command: str) -> list[str]:
    """简单的命令行拆分，支持双引号包裹的参数（跨平台）。"""
    tokens: list[str] = []
    buf: list[str] = []
    in_quotes = False
    for ch in command.strip():
        if ch == '"':
            in_quotes = not in_quotes
            continue
        if ch.isspace() and not in_quotes:
            if buf:
                tokens.append("".join(buf))
                buf = []
            continue
        buf.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


def _parse_whitelist(raw: str) -> set[str]:
    out: set[str] = set()
    for item in (raw or "").split(","):
        name = item.strip().lower()
        if name:
            # 允许写 python.exe，统一去扩展名做匹配
            if name.endswith(".exe"):
                name = name[:-4]
            out.add(name)
    return out


def _minimal_env() -> dict:
    """构造最小环境变量，保留程序运行必需项。"""
    safe_keys = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR",
                 "TEMP", "TMP", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE",
                 "PATHEXT", "NUMBER_OF_PROCESSORS", "USERPROFILE", "APPDATA")
    env = {k: v for k, v in os.environ.items() if k.upper() in
           {x.upper() for x in safe_keys}}
    return env


class ShellTool(Tool):
    name = "run_command"
    description = (
        "在沙箱目录内执行一条白名单命令（不支持管道、重定向、命令连接）。"
        "command 为完整命令行，例如 \"python hello.py\"。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的完整命令行"},
            "timeout": {"type": "integer", "description": "超时秒数，默认 15"},
        },
        "required": ["command"],
    }
    dangerous = True

    def describe(self, arguments: dict) -> str:
        return "执行命令：%s" % arguments.get("command", "?")

    def execute(self, arguments: dict) -> ToolResult:
        assert self.sandbox is not None
        command = self._arg(arguments, "command", "")
        if not command or not str(command).strip():
            return ToolResult.failure("缺少参数 command")
        command = str(command)

        for bad in _FORBIDDEN_CHARS:
            if bad in command:
                return ToolResult.failure(
                    "命令包含不允许的字符 %r（禁止管道/重定向/命令连接）" % bad)

        whitelist = _parse_whitelist(self.config.get("shell_whitelist", ""))
        if not whitelist:
            return ToolResult.failure("命令白名单为空：请先在设置中配置")

        tokens = _split_command(command)
        if not tokens:
            return ToolResult.failure("无法解析命令")

        prog = os.path.basename(tokens[0]).lower()
        if prog.endswith(".exe"):
            prog = prog[:-4]
        if prog not in whitelist:
            return ToolResult.failure(
                "程序 %r 不在白名单内，允许：%s" % (
                    prog, ", ".join(sorted(whitelist))))

        # Windows 内置命令需要走 cmd /c
        if sys.platform == "win32" and prog in _WIN_BUILTINS:
            args = ["cmd.exe", "/c"] + tokens
        else:
            args = tokens

        try:
            timeout = int(self._arg(arguments, "timeout", DEFAULT_TIMEOUT))
        except (TypeError, ValueError):
            timeout = DEFAULT_TIMEOUT
        timeout = max(1, min(MAX_TIMEOUT, timeout))

        try:
            proc = subprocess.run(
                args,
                cwd=self.sandbox.root,
                env=_minimal_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return ToolResult.failure("命令超时（>%d 秒），已终止" % timeout)
        except FileNotFoundError:
            return ToolResult.failure("找不到程序：%s" % prog)
        except OSError as exc:
            return ToolResult.failure("执行失败：%s" % exc)

        out = proc.stdout.decode("utf-8", "replace")
        err = proc.stderr.decode("utf-8", "replace")
        parts = []
        if out:
            parts.append("[stdout]\n" + self._truncate(out, MAX_OUTPUT))
        if err:
            parts.append("[stderr]\n" + self._truncate(err, MAX_OUTPUT))
        body = "\n".join(parts) if parts else "（无输出）"
        body += "\n[退出码 %d]" % proc.returncode

        if proc.returncode != 0:
            return ToolResult.failure(body)
        return ToolResult.success(body, returncode=proc.returncode)
