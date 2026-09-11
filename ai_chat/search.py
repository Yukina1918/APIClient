# ai_chat/search.py
"""联网搜索：把检索结果拼进提示词，再交给模型回答。"""
from __future__ import annotations

import html
import json
import re
import socket
from dataclasses import dataclass
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

SEARCH_PROVIDERS = ("tavily", "serper", "brave", "bing", "searxng", "duckduckgo")
NEEDS_KEY = {"tavily", "serper", "brave", "bing"}
NEEDS_ENDPOINT = {"searxng"}


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchError(RuntimeError):
    pass


def _get(url: str, headers: dict, timeout: int) -> str:
    req = urlrequest.Request(url, headers=headers, method="GET")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except urlerror.HTTPError as exc:
        raise SearchError("HTTP_%s" % exc.code) from exc
    except (socket.timeout, TimeoutError) as exc:
        raise SearchError("TIMEOUT") from exc
    except urlerror.URLError as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise SearchError("TIMEOUT") from exc
        raise SearchError("NETWORK") from exc
    except Exception as exc:
        raise SearchError(str(exc)) from exc


def _post(url: str, headers: dict, payload: dict, timeout: int) -> str:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    head = {"Content-Type": "application/json", **headers}
    req = urlrequest.Request(url, data=data, headers=head, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except urlerror.HTTPError as exc:
        raise SearchError("HTTP_%s" % exc.code) from exc
    except (socket.timeout, TimeoutError) as exc:
        raise SearchError("TIMEOUT") from exc
    except urlerror.URLError as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise SearchError("TIMEOUT") from exc
        raise SearchError("NETWORK") from exc
    except Exception as exc:
        raise SearchError(str(exc)) from exc


def _tavily(query, key, endpoint, count, timeout):
    body = {
        "api_key": key,
        "query": query,
        "max_results": count,
        "search_depth": "basic",
        "include_answer": False,
    }
    data = json.loads(_post(endpoint or "https://api.tavily.com/search",
                            {}, body, timeout))
    return [SearchResult(r.get("title", ""), r.get("url", ""), r.get("content", ""))
            for r in data.get("results", [])]


def _serper(query, key, endpoint, count, timeout):
    body = {"q": query, "num": count}
    data = json.loads(_post(endpoint or "https://google.serper.dev/search",
                            {"X-API-KEY": key}, body, timeout))
    return [SearchResult(r.get("title", ""), r.get("link", ""), r.get("snippet", ""))
            for r in data.get("organic", [])]


def _brave(query, key, endpoint, count, timeout):
    base = endpoint or "https://api.search.brave.com/res/v1/web/search"
    url = base + "?" + urlparse.urlencode({"q": query, "count": count})
    data = json.loads(_get(url, {
        "Accept": "application/json",
        "X-Subscription-Token": key,
    }, timeout))
    return [SearchResult(r.get("title", ""), r.get("url", ""),
                         r.get("description", ""))
            for r in (data.get("web") or {}).get("results", [])]


def _bing(query, key, endpoint, count, timeout):
    base = endpoint or "https://api.bing.microsoft.com/v7.0/search"
    url = base + "?" + urlparse.urlencode({"q": query, "count": count})
    data = json.loads(_get(url, {"Ocp-Apim-Subscription-Key": key}, timeout))
    return [SearchResult(r.get("name", ""), r.get("url", ""), r.get("snippet", ""))
            for r in (data.get("webPages") or {}).get("value", [])]


def _searxng(query, key, endpoint, count, timeout):
    if not endpoint:
        raise SearchError("SEARXNG_ENDPOINT_MISSING")
    base = endpoint.rstrip("/")
    url = base + "/search?" + urlparse.urlencode({
        "q": query, "format": "json", "language": "auto",
    })
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    data = json.loads(_get(url, headers, timeout))
    results = data.get("results", [])[:count]
    return [SearchResult(r.get("title", ""), r.get("url", ""),
                         r.get("content", ""))
            for r in results]


_DDG_LINK = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_DDG_SNIPPET = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.S)
_TAG = re.compile(r"<[^>]+>")


def _strip_tags(fragment: str) -> str:
    return html.unescape(_TAG.sub("", fragment)).strip()


def _duckduckgo(query, key, endpoint, count, timeout):
    base = endpoint or "https://html.duckduckgo.com/html/"
    url = base + "?" + urlparse.urlencode({"q": query})
    page = _get(url, {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }, timeout)

    links = _DDG_LINK.findall(page)
    snippets = [_strip_tags(s) for s in _DDG_SNIPPET.findall(page)]

    results: list[SearchResult] = []
    for idx, (href, title) in enumerate(links[:count]):
        if href.startswith("//"):
            href = "https:" + href
        parsed = urlparse.urlparse(href)
        if "duckduckgo.com" in parsed.netloc:
            real = urlparse.parse_qs(parsed.query).get("uddg")
            if real:
                href = real[0]
        results.append(SearchResult(
            _strip_tags(title),
            href,
            snippets[idx] if idx < len(snippets) else "",
        ))
    return results


_DISPATCH = {
    "tavily": _tavily,
    "serper": _serper,
    "brave": _brave,
    "bing": _bing,
    "searxng": _searxng,
    "duckduckgo": _duckduckgo,
}


def run_search(search_cfg: dict, query: str, timeout: int = 20) -> list[SearchResult]:
    provider = search_cfg.get("provider", "duckduckgo")
    handler = _DISPATCH.get(provider)
    if handler is None:
        raise SearchError("UNKNOWN_PROVIDER")

    key = (search_cfg.get("api_key") or "").strip()
    endpoint = (search_cfg.get("endpoint") or "").strip()
    if provider in NEEDS_KEY and not key:
        raise SearchError("SEARCH_KEY_MISSING")

    try:
        count = max(1, min(10, int(search_cfg.get("max_results", 5))))
    except (TypeError, ValueError):
        count = 5

    return handler(query, key, endpoint, count, timeout)[:count]


PROMPT_TEMPLATE = """以下是从互联网检索到的资料，请优先依据这些资料回答用户问题。
引用资料时在句末标注来源编号，例如 [1]。若资料不足以回答，请明确说明哪些部分无法确认。

[资料开始]
{context}
[资料结束]

用户问题：{question}"""


def build_search_prompt(question: str, results: list[SearchResult]) -> str:
    blocks = []
    for idx, item in enumerate(results, 1):
        snippet = " ".join(item.snippet.split())
        if len(snippet) > 600:
            snippet = snippet[:600] + "…"
        blocks.append("[%d] %s\n%s\n%s" % (idx, item.title or "(无标题)",
                                           item.url, snippet))
    return PROMPT_TEMPLATE.format(context="\n\n".join(blocks), question=question)


def format_sources(results: list[SearchResult], limit: int = 5) -> str:
    lines = []
    for idx, item in enumerate(results[:limit], 1):
        lines.append("[%d] %s  %s" % (idx, item.title[:60] or "(无标题)",
                                       item.url))
    return "\n".join(lines)