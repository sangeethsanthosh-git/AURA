"""NVIDIA NIM chat-completion service adapter."""

from __future__ import annotations

import logging
from typing import Any

from backend.config.config import Settings, settings
from backend.utils.http_client import HttpClient, HttpClientError
from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


class NvidiaService:
    """Encapsulates NVIDIA NIM OpenAI-compatible chat completions."""

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
        temperature: float = 0.45,
        top_p: float = 0.95,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Return a non-streaming NVIDIA NIM response."""
        keys = self.config.nvidia_api_keys
        if not keys:
            return error_response("nvidia", "chat_completion", "NVIDIA_API_KEY is not configured.")

        selected_model = model or self.config.nvidia_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        url = f"{self.config.nvidia_api_base_url.rstrip('/')}/chat/completions"

        last_error: Exception | None = None
        for index, key in enumerate(keys):
            try:
                raw = self.http_client.post_json(url, payload, headers={"Authorization": f"Bearer {key}"})
                content = raw["choices"][0]["message"]["content"].strip()
                return success_response(
                    "nvidia",
                    "chat_completion",
                    {
                        "content": content,
                        "model": raw.get("model", selected_model),
                        "usage": raw.get("usage", {}),
                        "key_index": index,
                        "raw": raw,
                    },
                    message=content,
                )
            except (HttpClientError, KeyError, IndexError, TypeError) as exc:
                last_error = exc
                LOGGER.warning("NVIDIA chat completion failed with key index %s: %s", index, exc)
                if not self._should_try_next_key(exc):
                    break

        status = last_error.status_code if isinstance(last_error, HttpClientError) else None
        details = last_error.details if isinstance(last_error, HttpClientError) else None
        message = self._limit_message(last_error) if status == 429 else str(last_error or "NVIDIA request failed.")
        return error_response("nvidia", "chat_completion", message, status, details)

    @staticmethod
    def _should_try_next_key(exc: Exception) -> bool:
        return isinstance(exc, HttpClientError) and exc.status_code in {401, 403, 408, 429}

    @staticmethod
    def _limit_message(exc: Exception | None) -> str:
        detail = getattr(exc, "details", None)
        if detail:
            return f"NVIDIA key token or rate limit reached. Tried configured fallback keys. Details: {detail}"
        return "NVIDIA key token or rate limit reached. Tried configured fallback keys."
