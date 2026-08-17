"""Reusable application controller for GUI and future interfaces."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app import AssistantOutput, build_assistant_output
from backend.memory.memory_models import MemoryStatus
from backend.router.service_manager import ServiceManager
from backend.router.smart_router import SmartRouter
from backend.voice.manager import VoiceInputManager
from backend.voice.models import TranscriptionResult, VoiceState
from conversation_manager import ConversationManager
from language_manager import LanguageManager
from model_router import ModelRouter
from tts_manager import TTSManager

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuraResponse:
    """UI-facing response model built from the existing router response."""

    text: str
    success: bool
    intent: str = "Unknown"
    execution_source: str = "Unknown"
    llm_provider: str = "None"
    model: str = "None"
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActivityRecord:
    """Small activity entry for the UI debugging page."""

    user_message: str
    response_text: str
    intent: str
    execution_source: str
    llm_provider: str
    model: str
    execution_time: float
    success: bool
    error: str | None = None


class AuraController:
    """Owns the existing AURA backend objects for one desktop session."""

    def __init__(
        self,
        router: SmartRouter | None = None,
        language_manager: LanguageManager | None = None,
        tts_manager: TTSManager | None = None,
        voice_manager: VoiceInputManager | None = None,
    ) -> None:
        self.language_manager = language_manager or LanguageManager()
        if router is None:
            model_router = ModelRouter()
            conversation_manager = ConversationManager(self.language_manager, model_router)
            service_manager = ServiceManager(conversation_manager)
            router = SmartRouter(service_manager)
        self.router = router
        self.tts_manager = tts_manager or TTSManager()
        self.voice_manager = voice_manager or VoiceInputManager()
        self.tts_enabled = False
        self.activities: list[ActivityRecord] = []

    def process_user_message(self, message: str) -> AuraResponse:
        """Process one user message through the real SmartRouter pipeline."""
        clean_message = message.strip()
        if not clean_message:
            return AuraResponse("", False, error="Please enter a message.")

        try:
            raw = self.router.ask(clean_message)
            output = build_assistant_output(raw)
            response = self._to_response(raw, output)
        except Exception:
            LOGGER.exception("AURA controller failed to process message.")
            response = AuraResponse(
                text="AURA encountered a problem while processing that request.",
                success=False,
                error="Backend processing failed.",
            )

        self.activities.insert(0, self._activity_from(clean_message, response))
        self.activities = self.activities[:50]
        return response

    def speak_response(self, text: str) -> None:
        """Speak a response if TTS is enabled; exceptions are logged only."""
        if not self.tts_enabled or not text:
            return
        try:
            self.tts_manager.speak(text, self.language_manager.current_language)
        except Exception:
            LOGGER.exception("TTS failed while speaking GUI response.")

    def start_voice_recording(self) -> TranscriptionResult:
        """Start push-to-talk recording without entering the AURA text pipeline."""
        return self.voice_manager.start_recording()

    def stop_voice_recording(self) -> TranscriptionResult:
        """Stop recording and transcribe locally before user review."""
        return self.voice_manager.stop_and_transcribe()

    @property
    def voice_state(self) -> VoiceState:
        return self.voice_manager.state

    def list_memories(self) -> list[dict[str, Any]]:
        """Return active/current memory records without exposing storage secrets."""
        memory = self.router.memory_manager.data
        items: list[dict[str, Any]] = []
        for record in memory.long_term:
            if record.status == MemoryStatus.DELETED.value:
                continue
            items.append(
                {
                    "id": record.memory_id,
                    "category": record.category,
                    "content": record.content,
                    "status": record.status,
                    "importance": record.importance,
                    "updated_at": record.updated_at,
                }
            )
        return items

    def forget_memory(self, content: str) -> AuraResponse:
        """Forget through MemoryManager, never by direct database mutation."""
        raw = self.router.memory_manager.forget(content, query=content)
        output = build_assistant_output(raw)
        return self._to_response(raw, output)

    def provider_status(self) -> dict[str, str]:
        """Return simple local status without network health checks."""
        return {
            "Application": "Ready",
            "Ollama": "Configured through local service",
            "Groq": "Configured by environment" ,
            "Hugging Face": "Configured by environment",
            "TTS": "Enabled" if self.tts_enabled else "Disabled",
        }

    @staticmethod
    def _to_response(raw: dict[str, Any], output: AssistantOutput) -> AuraResponse:
        route = raw.get("route", {}) if isinstance(raw, dict) else {}
        error = raw.get("error") if isinstance(raw, dict) else None
        error_message = error.get("message") if isinstance(error, dict) else None
        return AuraResponse(
            text=output.assistant_message,
            success=bool(raw.get("ok")),
            intent=str(route.get("intent", "Unknown")),
            execution_source=str(route.get("execution_source", route.get("source", "Unknown"))),
            llm_provider=str(route.get("llm_provider") or "None"),
            model=str(route.get("model", "None")),
            execution_time=float(route.get("execution_time_seconds") or 0.0),
            metadata=dict(route),
            error=error_message,
            raw=raw,
        )

    @staticmethod
    def _activity_from(message: str, response: AuraResponse) -> ActivityRecord:
        return ActivityRecord(
            user_message=message,
            response_text=response.text,
            intent=response.intent,
            execution_source=response.execution_source,
            llm_provider=response.llm_provider,
            model=response.model,
            execution_time=response.execution_time,
            success=response.success,
            error=response.error,
        )
