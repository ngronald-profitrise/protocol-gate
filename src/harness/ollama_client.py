"""A thin, dependency-light Ollama client.

Wraps the Ollama HTTP API (``/api/generate``) using httpx. Captures the two
metrics the benchmarks care about — tokens/second and time-to-first-token — from
Ollama's streaming response. If Ollama is unreachable, callers receive a clear
:class:`OllamaError` rather than a hang.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import httpx


class OllamaError(RuntimeError):
    """Raised when the Ollama server cannot be reached or returns an error."""


@dataclass
class Generation:
    """The result of one generation plus timing metrics."""

    text: str
    model: str
    time_to_first_token_s: float
    total_time_s: float
    eval_count: int
    tokens_per_second: float


class OllamaClient:
    def __init__(
        self,
        *,
        host: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._model = model or os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.0,
        format_json: bool = False,
    ) -> Generation:
        """Generate a completion, streaming to measure TTFT and throughput."""

        payload: dict[str, object] = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = "json"

        chunks: list[str] = []
        start = time.perf_counter()
        ttft: float | None = None
        eval_count = 0
        try:
            with httpx.Client(timeout=self._timeout) as client:
                with client.stream(
                    "POST", f"{self._host}/api/generate", json=payload
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        piece = data.get("response", "")
                        if piece and ttft is None:
                            ttft = time.perf_counter() - start
                        chunks.append(piece)
                        if data.get("done"):
                            eval_count = int(data.get("eval_count", 0))
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

        total = time.perf_counter() - start
        tps = eval_count / total if total > 0 and eval_count else 0.0
        return Generation(
            text="".join(chunks),
            model=self._model,
            time_to_first_token_s=ttft or total,
            total_time_s=total,
            eval_count=eval_count,
            tokens_per_second=tps,
        )

    def health(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                return client.get(f"{self._host}/api/tags").status_code == 200
        except httpx.HTTPError:
            return False
