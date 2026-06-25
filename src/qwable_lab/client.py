from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ChatResult:
    text: str
    latency_s: float
    usage: dict[str, Any]
    raw: dict[str, Any]


class OpenAICompatibleClient:
    def __init__(self, endpoint: str, api_key: str | None = None, timeout: int = 180):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def list_models(self) -> dict[str, Any]:
        return self._request("GET", "/models")

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> ChatResult:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        started = time.perf_counter()
        raw = self._request("POST", "/chat/completions", payload)
        latency = time.perf_counter() - started
        text = _extract_text(raw)
        usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
        return ChatResult(text=text, latency_s=latency, usage=usage, raw=raw)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = Request(
            f"{self.endpoint}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(req, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} from {path}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not reach {self.endpoint}: {exc}") from exc


def _extract_text(raw: dict[str, Any]) -> str:
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
    text = first.get("text")
    return text if isinstance(text, str) else ""
