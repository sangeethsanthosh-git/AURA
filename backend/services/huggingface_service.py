"""Hugging Face text-generation service adapter."""

from __future__ import annotations

import logging
from typing import Any

from backend.config.config import Settings, settings
from backend.utils.http_client import HttpClient, HttpClientError
from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


class HuggingFaceService:
    """Encapsulates Hugging Face Inference API text generation."""

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

    def text_generation(
        self,
        prompt: str,
        model: str | None = None,
        max_new_tokens: int = 256,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Generate text from a configurable Hugging Face model."""
        if not self.config.hf_api_key:
            return error_response("huggingface", "text_generation", "HF_API_KEY is not configured.")

        selected_model = model or self.config.hf_model
        payload = {
            "model": selected_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_new_tokens,
            "temperature": temperature,
        }

        LOGGER.info("Sending Hugging Face generation request with model=%s", selected_model)

        try:
            raw = self.http_client.post_json(
                self.config.hf_api_base_url,
                payload,
                headers={"Authorization": f"Bearer {self.config.hf_api_key}"},
            )
            content = self._extract_text(raw)
            return success_response(
                "huggingface",
                "text_generation",
                {"content": content, "model": selected_model, "raw": raw},
                message=content,
            )
        except (HttpClientError, ValueError) as exc:
            LOGGER.warning("Hugging Face generation failed: %s", exc)
            status = exc.status_code if isinstance(exc, HttpClientError) else None
            details = exc.details if isinstance(exc, HttpClientError) else None
            return error_response("huggingface", "text_generation", str(exc), status, details)

    @staticmethod
    def _extract_text(raw: Any) -> str:
        if isinstance(raw, list) and raw:
            first = raw[0]
            if isinstance(first, dict):
                return str(first.get("generated_text", "")).strip()
        if isinstance(raw, dict):
            choices = raw.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message", {})
                if isinstance(message, dict):
                    return str(message.get("content", "")).strip()
            if "generated_text" in raw:
                return str(raw["generated_text"]).strip()
            if "error" in raw:
                raise ValueError(str(raw["error"]))
        raise ValueError(f"Unexpected Hugging Face response format: {raw}")
