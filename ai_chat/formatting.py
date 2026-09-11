# ai_chat/formatting.py
"""削弱 Markdown 噪声符号，代码块内容原样保留。"""
from __future__ import annotations

import re

_FENCE = re.compile(r"(```.*?```|~~~.*?~~~)", re.S)

_RE_BOLD_STAR = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S)
_RE_BOLD_UNDER = re.compile(r"__(?=\S)(.+?)(?<=\S)__", re.S)
_RE_ITALIC_STAR = re.compile(r"(?<![\*\w])\*(?=\S)([^\*\n]+?)(?<=\S)\*(?!\*)")
_RE_ITALIC_UNDER = re.compile(r"(?<![\w_])_(?=\S)([^_\n]+?)(?<=\S)_(?![\w_])")
_RE_STRIKE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.S)
_RE_HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]*", re.M)
_RE_QUOTE = re.compile(r"^[ \t]{0,3}>[ \t]?", re.M)
_RE_HR = re.compile(r"^[ \t]{0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$", re.M)
_RE_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_RE_LINK = re.compile(r"\[([^\]\n]*)\]\((https?://[^)\s]+)\)")
_RE_ULIST = re.compile(r"^([ \t]*)[-*+][ \t]+", re.M)
_RE_OLIST = re.compile(r"^([ \t]*)\d{1,3}[.)][ \t]+", re.M)
_RE_BLANKS = re.compile(r"\n{3,}")

LEVELS = (0, 1, 2, 3)
DEFAULT_LEVEL = 2


def _soften_prose(text: str, level: int) -> str:
    text = _RE_BOLD_STAR.sub(r"\1", text)
    text = _RE_BOLD_UNDER.sub(r"\1", text)
    text = _RE_ITALIC_STAR.sub(r"\1", text)
    text = _RE_ITALIC_UNDER.sub(r"\1", text)

    if level >= 2:
        text = _RE_HEADING.sub("", text)
        text = _RE_QUOTE.sub("", text)
        text = _RE_HR.sub("", text)
        text = _RE_INLINE_CODE.sub(r"\1", text)
        text = _RE_STRIKE.sub(r"\1", text)

    if level >= 3:
        text = _RE_LINK.sub(r"\1", text)
        text = _RE_ULIST.sub(r"\1", text)
        text = _RE_OLIST.sub(r"\1", text)

    return _RE_BLANKS.sub("\n\n", text)


def soften_markdown(text: str, level: int = DEFAULT_LEVEL) -> str:
    if not text or level <= 0:
        return text
    parts = _FENCE.split(text)
    for idx in range(0, len(parts), 2):
        parts[idx] = _soften_prose(parts[idx], level)
    return "".join(parts)