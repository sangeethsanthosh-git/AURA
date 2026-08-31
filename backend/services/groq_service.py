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
        keys = self.config.groq_api_keys
        if not keys:
            return error_response("groq", "chat_completion", "GROQ_API_KEY is not configured.")

        payload = self._payload(prompt, model, system_prompt, temperature, max_tokens, stream=False)
        LOGGER.info("Sending Groq chat request with model=%s", payload["model"])

        last_error: Exception | None = None
        for index, key in enumerate(keys):
            try:
                raw = self.http_client.post_json(self.API_URL, payload, headers=self._headers(key))
                content = raw["choices"][0]["message"]["content"].strip()
                return success_response(
                    "groq",
                    "chat_completion",
                    {
                        "content": content,
                        "model": raw.get("model", payload["model"]),
                        "usage": raw.get("usage", {}),
                        "key_index": index,
                        "raw": raw,
                    },
                    message=content,
                )
            except (HttpClientError, KeyError, IndexError, TypeError) as exc:
                last_error = exc
                LOGGER.warning("Groq chat completion failed with key index %s: %s", index, exc)
                if not self._should_try_next_key(exc):
                    break

        status = last_error.status_code if isinstance(last_error, HttpClientError) else None
        details = last_error.details if isinstance(last_error, HttpClientError) else None
        message = self._limit_message(last_error) if status == 429 else str(last_error or "Groq request failed.")
        return error_response("groq", "chat_completion", message, status, details)

    def stream_chat_completion(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Iterable[dict[str, Any]]:
        """Yield structured chunks from Groq streaming chat completions."""
        if not self.config.groq_api_keys:
            yield error_response("groq", "stream_chat_completion", "GROQ_API_KEY is not configured.")
            return

        payload = self._payload(prompt, model, system_prompt, temperature, max_tokens, stream=True)
        LOGGER.info("Opening Groq streaming request with model=%s", payload["model"])

        try:
            for line in self.http_client.stream_post_json_lines(
                self.API_URL,
                payload,
                headers=self._headers(self.config.groq_api_keys[0]),
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

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    @staticmethod
    def _should_try_next_key(exc: Exception) -> bool:
        return isinstance(exc, HttpClientError) and exc.status_code in {401, 403, 408, 429}

    @staticmethod
    def _limit_message(exc: Exception | None) -> str:
        detail = getattr(exc, "details", None)
        if detail:
            return f"Groq key token or rate limit reached. Tried configured fallback keys. Details: {detail}"
        return "Groq key token or rate limit reached. Tried configured fallback keys."

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
