"""Small, dependency-light Ollama client with structured-output support."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
        budget: float | None = None,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", "gemma3:4b")
        self.base_url = (
            base_url or os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
        ).rstrip("/")
        self.timeout = timeout
        self.deadline = None if budget is None else time.monotonic() + budget
        self.halted = False

    def chat(
        self,
        system: str,
        user: str,
        *,
        json_output: bool = False,
        temperature: float = 0.0,
    ) -> str:
        if self.halted or (self.deadline is not None and time.monotonic() >= self.deadline):
            raise OllamaError("Model request budget exhausted or a previous call failed")
        timeout = self.timeout if self.deadline is None else min(self.timeout, self.deadline - time.monotonic())
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": temperature},
        }
        if json_output:
            payload["format"] = "json"
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=max(0.001, timeout),
            )
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise OllamaError("Ollama response must be an object")
            if result.get("done") is not True or result.get("done_reason") == "length":
                raise OllamaError("Ollama generation did not complete normally")
            content = result["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise OllamaError("Ollama returned no textual answer")
            return content
        except (httpx.HTTPError, KeyError, TypeError, ValueError, OllamaError) as exc:
            if self.deadline is not None:
                self.halted = True
            raise OllamaError("Model service unavailable or returned an invalid/incomplete response") from exc

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        raw = self.chat(system, user, json_output=True)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            if self.deadline is not None:
                self.halted = True
            raise OllamaError("Ollama returned invalid JSON") from exc
        if not isinstance(value, dict):
            if self.deadline is not None:
                self.halted = True
            raise OllamaError("Ollama JSON response must be an object")
        return value
