"""Groq chat-completion service adapter."""

from __future__ import annotations

import json
import logging
from typing import Any, Iterable

from backend.config.config import Settings, settings
from backend.utils.http_client import HttpClient, HttpClientError
from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


class GroqService:
    """Encapsulates Groq API access for chat completions."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        config: Settings = settings,
        http_client: HttpClient | None = None,
    ) -> None:
        self.config = config
        self.http_client = http_client or HttpClient(
            timeout=config.request_timeout,
            retry_attempts=config.retry_attempts,
            retry_backoff_seconds=config.retry_backoff_seconds,
        )

    def chat_completion(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """Return a non-streaming Groq chat response."""
        if not self.config.groq_api_key:
            return error_response("groq", "chat_completion", "GROQ_API_KEY is not configured.")

        payload = self._payload(prompt, model, system_prompt, temperature, max_tokens, stream=False)
        LOGGER.info("Sending Groq chat request with model=%s", payload["model"])

        try:
            raw = self.http_client.post_json(self.API_URL, payload, headers=self._headers())
            content = raw["choices"][0]["message"]["content"].strip()
            return success_response(
                "groq",
                "chat_completion",
                {
                    "content": content,
                    "model": raw.get("model", payload["model"]),
                    "usage": raw.get("usage", {}),
                    "raw": raw,
                },
                message=content,
            )
        except (HttpClientError, KeyError, IndexError, TypeError) as exc:
            LOGGER.warning("Groq chat completion failed: %s", exc)
            status = exc.status_code if isinstance(exc, HttpClientError) else None
            details = exc.details if isinstance(exc, HttpClientError) else None
            return error_response("groq", "chat_completion", str(exc), status, details)

    def stream_chat_completion(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Iterable[dict[str, Any]]:
        """Yield structured chunks from Groq streaming chat completions."""
        if not self.config.groq_api_key:
            yield error_response("groq", "stream_chat_completion", "GROQ_API_KEY is not configured.")
            return

        payload = self._payload(prompt, model, system_prompt, temperature, max_tokens, stream=True)
        LOGGER.info("Opening Groq streaming request with model=%s", payload["model"])

        try:
            for line in self.http_client.stream_post_json_lines(
                self.API_URL,
                payload,
                headers=self._headers(),
            ):
                if not line.startswith("data: "):
                    continue

                data = line.removeprefix("data: ").strip()
                if data == "[DONE]":
                    break

                chunk = json.loads(data)
                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if delta:
                    yield success_response(
                        "groq",
                        "stream_chat_completion",
                        {"content": delta, "raw": chunk},
                        message=delta,
                    )
        except (HttpClientError, json.JSONDecodeError) as exc:
            LOGGER.warning("Groq streaming request failed: %s", exc)
            status = exc.status_code if isinstance(exc, HttpClientError) else None
            details = exc.details if isinstance(exc, HttpClientError) else None
            yield error_response("groq", "stream_chat_completion", str(exc), status, details)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.config.groq_api_key}"}

    def _payload(
        self,
        prompt: str,
        model: str | None,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return {
            "model": model or self.config.groq_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
