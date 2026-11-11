"""Shared HTTP clients for real Groq and the controllable local stand-in."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import AsyncIterator

import httpx
from dotenv import load_dotenv

from pipeline import ModelResult

load_dotenv()


class ProviderError(RuntimeError):
    def __init__(self, status_code: int, message: str, headers: dict[str, str]) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.headers = headers


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str | None = None, model: str = "llama-3.1-8b-instant", timeout_s: float = 20.0) -> None:
        self.base_url, self.api_key, self.model, self.timeout_s = base_url.rstrip("/"), api_key, model, timeout_s

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"} if self.api_key else {"Content-Type": "application/json"}

    async def generate(self, messages: list[dict[str, str]]) -> ModelResult:
        """Collect a provider stream internally so model TTFT is measured before verification."""
        started = time.perf_counter()
        payload = {"model": self.model, "messages": messages, "temperature": 0, "stream": True, "stream_options": {"include_usage": True}}
        parts: list[str] = []
        first_token_ms: float | None = None
        usage: dict = {}
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", headers=self._headers(), json=payload) as response:
                headers = {key.lower(): value for key, value in response.headers.items()}
                if response.status_code >= 400:
                    raise ProviderError(response.status_code, (await response.aread()).decode(errors="replace"), headers)
                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    event = json.loads(line[6:])
                    delta = event.get("choices", [{}])[0].get("delta", {}).get("content", "") if event.get("choices") else ""
                    if delta:
                        if first_token_ms is None:
                            first_token_ms = round((time.perf_counter() - started) * 1000, 3)
                        parts.append(delta)
                    usage = event.get("usage") or usage
        return ModelResult(
            text="".join(parts),
            model_ttft_ms=first_token_ms,
            total_ms=round((time.perf_counter() - started) * 1000, 3),
            tokens_in=usage.get("prompt_tokens"), tokens_out=usage.get("completion_tokens"),
            provider_headers=headers,
        )

    async def generate_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[tuple[str, float, dict[str, str]]]:
        """Yield token text, elapsed ms, headers. Callers use this only for provider measurement."""
        started = time.perf_counter()
        payload = {"model": self.model, "messages": messages, "temperature": 0, "stream": True}
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", headers=self._headers(), json=payload) as response:
                headers = {key.lower(): value for key, value in response.headers.items()}
                if response.status_code >= 400:
                    raise ProviderError(response.status_code, await response.aread(), headers)
                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    delta = json.loads(line[6:])["choices"][0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta, round((time.perf_counter() - started) * 1000, 3), headers


class GroqClient(OpenAICompatibleClient):
    def __init__(self) -> None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set; no real Groq request was sent.")
        super().__init__("https://api.groq.com/openai/v1", key, os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"))


class StandInClient(OpenAICompatibleClient):
    def __init__(self, base_url: str = "http://127.0.0.1:8000/v1") -> None:
        super().__init__(base_url, api_key=None, model="relay-standin")
