# ai_chat/client.py
"""OpenAI 兼容的 /chat/completions 客户端（仅标准库）。

支持：
  · 流式 / 非流式对话
  · Function Calling：传入 tools（OpenAI 工具 schema），
    响应里的 tool_calls 会被聚合到 self.last_message
  · 多模态：messages 透传，content 可以是 [{"type": ...}, ...] 列表
"""
from __future__ import annotations

import json
import socket
from urllib import error as urlerror
from urllib import request as urlrequest


class APIError(RuntimeError):
    """服务端返回的错误。"""


class NetworkError(RuntimeError):
    """网络层错误。"""


class ChatClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        timeout: int = 120,
        proxy: str = "",
        auth_style: str = "bearer",
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.auth_style = auth_style
        self._resp = None
        self.last_message: dict | None = None

        if proxy:
            handler = urlrequest.ProxyHandler({"http": proxy, "https": proxy})
            self._opener = urlrequest.build_opener(handler)
        else:
            self._opener = urlrequest.build_opener()

    def _headers(self) -> dict:
        head = {"Content-Type": "application/json"}
        if self.auth_style == "x-api-key":
            head["x-api-key"] = self.api_key
        else:
            head["Authorization"] = "Bearer " + self.api_key
        return head

    @staticmethod
    def _extract_error(exc: urlerror.HTTPError) -> str:
        try:
            body = exc.read().decode("utf-8", "replace")
            data = json.loads(body)
            err = data.get("error")
            if isinstance(err, dict):
                return str(err.get("message") or err)
            if isinstance(err, str):
                return err
            return body[:300]
        except Exception:
            return "HTTP %s" % exc.code

    def _post(self, payload: dict):
        url = self.base_url + "/chat/completions"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urlrequest.Request(url, data=data, headers=self._headers(),
                                 method="POST")
        try:
            return self._opener.open(req, timeout=self.timeout)
        except urlerror.HTTPError as exc:
            raise APIError("HTTP %s: %s" % (exc.code,
                                            self._extract_error(exc))) from exc
        except urlerror.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, (socket.timeout, TimeoutError)):
                raise NetworkError("TIMEOUT") from exc
            raise NetworkError(str(reason)) from exc
        except (socket.timeout, TimeoutError) as exc:
            raise NetworkError("TIMEOUT") from exc

    def cancel(self) -> None:
        resp, self._resp = self._resp, None
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

    # ---------------------------------------------------------- 主调用

    def chat(self, messages, *, stream=True, on_chunk=None, stop_event=None,
             tools=None, tool_choice=None) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": bool(stream),
        }
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice

        resp = self._post(payload)
        self._resp = resp
        try:
            if stream:
                return self._read_stream(resp, on_chunk, stop_event)
            raw = resp.read().decode("utf-8", "replace")
            try:
                obj = json.loads(raw)
                message = obj["choices"][0].get("message") or {}
            except Exception as exc:
                raise APIError("无法解析响应：%s" % raw[:200]) from exc
            self.last_message = message
            return message.get("content") or ""
        finally:
            self._resp = None
            try:
                resp.close()
            except Exception:
                pass

    # ---------------------------------------------------------- 流式聚合

    @staticmethod
    def _merge_tool_call(tc_map: dict, tc: dict) -> None:
        idx = tc.get("index", 0)
        slot = tc_map.get(idx)
        if slot is None:
            slot = {"id": "", "type": "function",
                    "function": {"name": "", "arguments": ""}}
            tc_map[idx] = slot
        if tc.get("id"):
            slot["id"] = tc["id"]
        if tc.get("type"):
            slot["type"] = tc["type"]
        fn = tc.get("function") or {}
        if fn.get("name"):
            slot["function"]["name"] = fn["name"]
        if fn.get("arguments"):
            slot["function"]["arguments"] += fn["arguments"]

    def _read_stream(self, resp, on_chunk, stop_event) -> str:
        buffer: list[str] = []
        tc_map: dict = {}
        for raw in resp:
            if stop_event is not None and stop_event.is_set():
                break
            line = raw.decode("utf-8", "replace").strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                obj = json.loads(data)
                delta = obj["choices"][0].get("delta") or {}
            except Exception:
                continue
            piece = delta.get("content")
            if piece:
                buffer.append(piece)
                if on_chunk is not None:
                    on_chunk(piece)
            for tc in delta.get("tool_calls") or []:
                self._merge_tool_call(tc_map, tc)

        text = "".join(buffer)
        if tc_map:
            tool_calls = [tc_map[i] for i in sorted(tc_map)]
            self.last_message = {
                "role": "assistant",
                "content": text or None,
                "tool_calls": tool_calls,
            }
        else:
            self.last_message = {"role": "assistant", "content": text}
        return text

    def test(self) -> str:
        resp = self._post({
            "model": self.model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 8,
            "stream": False,
        })
        try:
            raw = resp.read().decode("utf-8", "replace")
        finally:
            try:
                resp.close()
            except Exception:
                pass
        try:
            return json.loads(raw)["choices"][0]["message"]["content"] or "(空)"
        except Exception:
            return raw[:120]
