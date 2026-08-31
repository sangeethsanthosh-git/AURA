"""Compatibility wrapper around the existing Ollama conversation workflow."""

from __future__ import annotations

import logging
from typing import Any

from conversation_manager import ConversationManager
from language_manager import LanguageManager
from model_router import ModelRouter

from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


class OllamaService:
    """Uses the current local chat stack without altering Ollama internals."""

    def __init__(self, conversation_manager: ConversationManager | None = None) -> None:
        self.conversation_manager = conversation_manager or ConversationManager(
            LanguageManager(),
            ModelRouter(),
        )

    def chat(self, prompt: str, model: str | None = None) -> dict[str, Any]:
        """Ask the existing local Ollama conversation manager."""
        try:
            content, selection = self.conversation_manager.ask(prompt, model_override=model)
            return success_response(
                "ollama",
                "chat",
                {
                    "content": content,
                    "language": selection.language,
                    "model": selection.model,
                },
                message=content,
            )
        except RuntimeError as exc:
            LOGGER.exception("Ollama service failed.")
            return error_response("ollama", "chat", str(exc))
