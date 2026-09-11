# ai_chat/providers.py
"""常见 OpenAI 兼容服务商预设。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    base_url: str
    models: tuple[str, ...] = ()
    console: str = ""
    auth_style: str = "bearer"


PROVIDERS: tuple[Provider, ...] = (
    Provider(
        "openai", "OpenAI", "https://api.openai.com/v1",
        ("gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "o4-mini"),
        "https://platform.openai.com/api-keys",
    ),
    Provider(
        "deepseek", "DeepSeek", "https://api.deepseek.com/v1",
        ("deepseek-chat", "deepseek-reasoner"),
        "https://platform.deepseek.com/api_keys",
    ),
    Provider(
        "moonshot", "Kimi / Moonshot", "https://api.moonshot.cn/v1",
        ("moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"),
        "https://platform.moonshot.cn/console/api-keys",
    ),
    Provider(
        "zhipu", "智谱 GLM", "https://open.bigmodel.cn/api/paas/v4",
        ("glm-4-flash", "glm-4-air", "glm-4-plus"),
        "https://open.bigmodel.cn/usercenter/apikeys",
    ),
    Provider(
        "dashscope", "通义千问", "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ("qwen-plus", "qwen-turbo", "qwen-max", "qwen-long"),
        "https://bailian.console.aliyun.com/",
    ),
    Provider(
        "siliconflow", "SiliconFlow", "https://api.siliconflow.cn/v1",
        ("deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct"),
        "https://cloud.siliconflow.cn/account/ak",
    ),
    Provider(
        "openrouter", "OpenRouter", "https://openrouter.ai/api/v1",
        ("openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet",
         "google/gemini-2.0-flash-001"),
        "https://openrouter.ai/keys",
    ),
    Provider(
        "groq", "Groq", "https://api.groq.com/openai/v1",
        ("llama-3.3-70b-versatile", "mixtral-8x7b-32768"),
        "https://console.groq.com/keys",
    ),
    Provider(
        "gemini", "Google Gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        ("gemini-2.0-flash", "gemini-1.5-pro"),
        "https://aistudio.google.com/app/apikey",
    ),
    Provider(
        "anthropic", "Anthropic Claude", "https://api.anthropic.com/v1",
        ("claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"),
        "https://console.anthropic.com/settings/keys",
        auth_style="x-api-key",
    ),
    Provider(
        "ollama", "Ollama（本地）", "http://localhost:11434/v1",
        ("llama3.2", "qwen2.5", "deepseek-r1"),
    ),
    Provider("custom", "自定义 / 其他兼容接口", "", ()),
)

_BY_ID = {p.id: p for p in PROVIDERS}


def get_provider(pid: str) -> Provider:
    return _BY_ID.get(pid, _BY_ID["custom"])


def guess_provider(base_url: str) -> str:
    url = (base_url or "").rstrip("/").lower()
    for p in PROVIDERS:
        if p.base_url and p.base_url.rstrip("/").lower() == url:
            return p.id
    return "custom"