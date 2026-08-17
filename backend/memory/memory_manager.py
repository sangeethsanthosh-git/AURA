"""Production-quality memory manager for AURA.

The manager coordinates independent concerns:
- extraction: ``MemoryExtractor``
- storage/persistence: ``JsonMemoryStore``
- retrieval/search: schema-aware methods in this class
- formatting: ``MemoryFormatter``

The public ``handle()`` and ``analyze()`` methods remain compatible with the
Smart Router while the internal storage uses the structured memory schema.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from backend.memory.daily_memory import DailyMemory
from backend.memory.long_term_memory import LongTermMemoryStore
from backend.memory.memory_decision import MemoryDecisionEngine
from backend.memory.memory_extractor import MemoryExtractor
from backend.memory.memory_formatter import MemoryFormatter
from backend.memory.memory_models import ExtractionResult, MemoryData, MemoryDecision, MemoryImportance, MemoryPlan, StorageDecision, SessionMemory, utc_now_iso
from backend.memory.memory_promoter import MemoryPromoter
from backend.memory.memory_retriever import MemoryRetriever
from backend.memory.memory_store import JsonMemoryStore
from backend.memory.memory_utils import (
    CLEAR_SESSION_TERMS,
    FORGET_EVERYTHING_TERMS,
    LIST_FIELDS,
    PREFERENCE_FIELDS,
    PROFILE_FIELDS,
    append_unique,
    field_label,
    forget_field_from_text,
    normalize_text,
)
from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


class MemoryManager:
    """Structured memory facade used by the Smart Router."""

    SUMMARY_ALIASES = (
        "who am i",
        "tell me about me",
        "what do you know about me",
        "what do you remember about me",
        "what do you remember",
        "summarize my profile",
        "do you remember me",
    )
    CONVERSATION_ALIASES = (
        "what did i just say",
        "what did i tell you",
        "what were we discussing",
        "continue our discussion",
        "summarize today's conversation",
        "summarize our conversation",
    )

    def __init__(
        self,
        store: JsonMemoryStore | None = None,
        path: Path | str | None = None,
        extractor: MemoryExtractor | None = None,
        formatter: MemoryFormatter | None = None,
        daily_root: Path | str | None = None,
        session_context_limit: int = 8,
    ) -> None:
        self.store = store or JsonMemoryStore(path)
        self.extractor = extractor or MemoryExtractor()
        self.formatter = formatter or MemoryFormatter()
        self.decision_engine = MemoryDecisionEngine()
        self.daily_memory = DailyMemory(daily_root)
        self.retriever = MemoryRetriever(self.daily_memory)
        self.promoter = MemoryPromoter()
        self.session = SessionMemory(context_limit=session_context_limit)
        self.data = MemoryData.empty()
        self.load()

    def handle(self, text: str) -> dict[str, Any]:
        """Handle a memory-specific user request and return a structured response."""
        self.track_conversation(text)
        decision = self.analyze(text)
        if not decision.requires_memory:
            LOGGER.info("Memory Miss: request does not require memory. text=%s", text)
            return error_response("memory", "miss", "Memory is not required for this request.")

        try:
            if decision.operation == "daily_recall":
                return self.daily_recall()
            if decision.operation == "remember":
                extraction = self.extractor.extract(text)
                if extraction is None:
                    LOGGER.info("Memory Miss: no extractable memory found. text=%s", text)
                    return success_response("memory", "remember", {}, "I could not identify what to remember.")
                return self.remember(extraction)
            if decision.operation == "recall":
                return self.recall(decision.field)
            if decision.operation == "summary":
                return self.summary()
            if decision.operation == "search":
                return self.search(text)
            if decision.operation == "forget":
                return self.forget(decision.field or decision.value or text, query=decision.value or text)
            if decision.operation == "clear_session":
                return self.clear_session()
            if decision.operation == "clear_all":
                return self.clear_all()
            if decision.operation == "conversation":
                return self.conversation_recall(text)
            return self.summary()
        except Exception as exc:
            LOGGER.exception("MemoryManager failed.")
            return error_response("memory", "handle", "Memory operation failed.", details=repr(exc))

    def analyze(self, text: str) -> MemoryDecision:
        """Decide whether a request should be routed to memory."""
        normalized = normalize_text(text)
        lowered = normalized.lower()

        if any(term in lowered for term in CLEAR_SESSION_TERMS):
            return self._decision("clear_session", confidence=0.99)
        if any(term in lowered for term in FORGET_EVERYTHING_TERMS):
            return self._decision("clear_all", confidence=0.99)
        if lowered.startswith("forget "):
            target = normalize_text(text[7:])
            field = forget_field_from_text(text)
            extraction = self.extractor.extract(target)
            return MemoryDecision(True, "forget", field=field or (extraction.field if extraction else None), value=target, confidence=0.95)
        plan = self.plan(text)
        if plan.storage == StorageDecision.LONG_TERM and lowered.startswith(("remember ", "remember that ", "remember this ")):
            extraction = self.extractor.extract(normalized)
            if extraction:
                return MemoryDecision(
                    True,
                    "remember",
                    category=extraction.category,
                    field=extraction.field,
                    value=extraction.value,
                    confidence=extraction.confidence,
                )
        if plan.retrieval.value == "DAILY":
            return self._decision("daily_recall", confidence=plan.confidence)
        if any(term in lowered for term in self.CONVERSATION_ALIASES):
            return self._decision("conversation", confidence=0.96)
        if any(term in lowered for term in self.SUMMARY_ALIASES):
            return self._decision("summary", confidence=0.97)

        extraction = self.extractor.extract(normalized)
        if extraction:
            return MemoryDecision(
                True,
                "remember",
                category=extraction.category,
                field=extraction.field,
                value=extraction.value,
                confidence=extraction.confidence,
            )

        recall_field = self._recall_field_from_text(lowered)
        if recall_field:
            return self._decision("recall", field=recall_field, confidence=0.96)

        search_field = self._semantic_search_field(lowered)
        if search_field:
            return self._decision("search", field=search_field, confidence=0.90)

        LOGGER.info("Memory Miss: %s", text)
        return MemoryDecision(False)

    def plan(self, text: str) -> MemoryPlan:
        """Return lightweight retrieval/storage decisions for one message."""
        plan = self.decision_engine.plan(text)
        plan.query = text
        LOGGER.info("Memory Storage Decision: retrieval=%s storage=%s reason=%s", plan.retrieval.value, plan.storage.value, plan.reason)
        return plan

    def retrieve_for_request(self, text: str) -> dict[str, object]:
        """Selectively retrieve local memory without loading everything."""
        plan = self.plan(text)
        return self.retriever.retrieve(plan, self.session, LongTermMemoryStore(self.data.long_term))

    def observe_interaction(self, user_input: str, response: dict[str, Any] | None = None) -> None:
        """Apply post-response storage decisions for normal routed requests."""
        self.track_conversation(user_input)
        plan = self.plan(user_input)
        if plan.storage == StorageDecision.DAILY:
            self.daily_memory.append(user_input)
            LOGGER.info("Memory Promotion: stored daily context.")
        elif plan.storage == StorageDecision.LONG_TERM:
            extraction = self.extractor.extract(user_input)
            if extraction:
                self._store_long_term(extraction, explicit=user_input.lower().startswith("remember"))
                self.save()
        elif plan.storage == StorageDecision.SESSION_ONLY:
            LOGGER.info("Memory Storage Decision: session only.")

    def remember(self, extraction: ExtractionResult | str, value: str | None = None) -> dict[str, Any]:
        """Store or update a profile, preference, or list memory."""
        started = time.perf_counter()
        if isinstance(extraction, str):
            if value is None:
                raise ValueError("value is required when remember() receives a field string")
            extraction = ExtractionResult(self._category_for_field(extraction), extraction, value, 0.90, extraction in LIST_FIELDS)

        LOGGER.info(
            "Extraction Result: Detected Entity=%s Detected Category=%s Confidence Score=%.2f",
            extraction.field,
            extraction.category,
            extraction.confidence,
        )

        if extraction.field in PROFILE_FIELDS:
            setattr(self.data.profile, extraction.field, extraction.value)
        elif extraction.field in PREFERENCE_FIELDS:
            setattr(self.data.preferences, extraction.field, extraction.value)
        elif extraction.field in LIST_FIELDS:
            target = getattr(self.data, extraction.field)
            append_unique(target, extraction.value)
        else:
            LOGGER.warning("Memory Miss: unsupported field=%s", extraction.field)
            return error_response("memory", "remember", f"Unsupported memory field: {extraction.field}")

        self.data.updated_at = utc_now_iso()
        self._store_long_term(extraction, explicit=True)
        self.save()
        self._log_event("Memory Update", extraction.field, extraction.value, extraction.confidence, started)
        return success_response(
            "memory",
            "remember",
            {"category": extraction.category, "field": extraction.field, "value": extraction.value, "storage": StorageDecision.LONG_TERM.value},
            self.formatter.remembered(extraction.field, extraction.value, extraction.is_list),
        )

    def recall(self, field: str | None = None) -> dict[str, Any]:
        """Recall one field or return a profile summary."""
        started = time.perf_counter()
        if field is None:
            return self.summary()

        value = self._get_field_value(field)
        if not value:
            LOGGER.info("Memory Miss: field=%s", field)
        else:
            self._log_event("Memory Hit", field, str(value), 1.0, started)
        return success_response(
            "memory",
            "recall",
            {"field": field, "value": value},
            self.formatter.recalled(field, value),
        )

    def summary(self) -> dict[str, Any]:
        """Return a natural-language profile summary."""
        LOGGER.info("Memory Hit: profile summary requested")
        return success_response("memory", "summary", self.data.to_dict(), self.formatter.profile_summary(self.data))

    def daily_recall(self) -> dict[str, Any]:
        entries = self.daily_memory.read()
        if not entries:
            return success_response("memory", "daily_recall", {"entries": []}, "I do not have any important notes from today yet.")
        return success_response("memory", "daily_recall", {"entries": entries}, "Earlier today: " + " ".join(entries[-5:]))

    def update(self, field: str, value: str) -> dict[str, Any]:
        """Update an existing memory field with natural response wording."""
        response = self.remember(field, value)
        if response.get("ok"):
            response["message"] = "I've updated what I know about you."
        return response

    def forget(self, field: str | None, query: str | None = None) -> dict[str, Any]:
        """Delete one memory category or field."""
        started = time.perf_counter()
        if not field:
            LOGGER.info("Memory Miss: forget request did not identify a field")
            return success_response("memory", "forget", {}, "I could not identify which memory to forget.")

        removed = self._clear_field(field)
        deleted = LongTermMemoryStore(self.data.long_term).forget(query or field or "")
        removed = removed or deleted is not None
        if removed:
            self.save()
            self._log_event("Memory Delete", field, "deleted", 1.0, started)
            return success_response("memory", "forget", {"field": field}, f"I've forgotten your {field_label(field)}.")

        LOGGER.info("Memory Miss: field=%s", field)
        return success_response("memory", "forget", {"field": field}, f"I did not have your {field_label(field)} saved.")

    def clear_session(self) -> dict[str, Any]:
        self.session = SessionMemory()
        LOGGER.info("Memory Delete: session memory cleared")
        return success_response("memory", "clear_session", {}, "I've cleared this session's conversation memory.")

    def clear_all(self) -> dict[str, Any]:
        self.data = MemoryData.empty()
        self.session = SessionMemory()
        self.save()
        LOGGER.info("Memory Delete: all persistent and session memory cleared")
        return success_response("memory", "clear_all", {}, "I've forgotten everything I had saved.")

    def load(self) -> None:
        self.data = self.store.load()

    def save(self) -> None:
        self.store.save(self.data)

    def _store_long_term(self, extraction: ExtractionResult, explicit: bool = False) -> None:
        category, importance = self.promoter.classify(extraction, explicit=explicit)
        content = self.promoter.content_for(extraction)
        if explicit:
            importance = MemoryImportance.HIGH.value
        LongTermMemoryStore(self.data.long_term).upsert(category, content, importance=importance, confidence=extraction.confidence)
        LOGGER.info("Memory Promotion: long-term category=%s importance=%s", category, importance)

    def search(self, query: str) -> dict[str, Any]:
        field = self._semantic_search_field(query.lower()) or self._recall_field_from_text(query.lower())
        if field:
            return self.recall(field)
        return self.summary()

    def conversation_recall(self, text: str) -> dict[str, Any]:
        lowered = text.lower()
        history = self.session.conversation[:-1]
        if not history:
            return success_response("memory", "conversation_recall", {"conversation": []}, "We have just started this conversation.")
        if "just say" in lowered:
            return success_response("memory", "conversation_recall", {"last": history[-1]}, f"You just said: {history[-1]}")
        if "summarize" in lowered:
            summary = " ".join(history[-6:])
            return success_response("memory", "conversation_recall", {"summary": summary}, f"Today, we discussed: {summary}")
        topic = self.session.current_topic or history[-1]
        return success_response("memory", "conversation_recall", {"topic": topic}, f"We were discussing: {topic}")

    def track_conversation(self, text: str) -> None:
        normalized = normalize_text(text)
        self.session.conversation.append(normalized)
        self.session.recent_context = self.session.conversation[-self.session.context_limit :]
        if not self._looks_like_memory_query(normalized):
            self.session.current_topic = normalized

    @staticmethod
    def _decision(operation: str, field: str | None = None, confidence: float = 0.0) -> MemoryDecision:
        return MemoryDecision(True, operation, field=field, confidence=confidence)

    @staticmethod
    def _recall_field_from_text(lowered: str) -> str | None:
        aliases: dict[str, tuple[str, ...]] = {
            "name": ("what is my name", "tell me my name", "my name"),
            "age": ("what is my age", "how old am i", "my age"),
            "education": ("what am i studying", "what do i study", "my education", "what is my education"),
            "occupation": ("what do i do", "my occupation", "my job", "my profession"),
            "company": ("where do i work", "my company", "who do i work for"),
            "location": ("where do i live", "where am i from", "my location", "my city"),
            "favorite_language": ("favorite language", "favourite language"),
            "preferred_ai": ("preferred ai", "which ai do i prefer"),
            "operating_system": ("operating system", "which os", "preferred os"),
            "skills": ("what languages do i know", "what skills do i have", "my skills"),
            "goals": ("my goals", "what are my goals"),
            "projects": ("my projects", "what projects"),
        }
        for field, terms in aliases.items():
            if any(term in lowered for term in terms):
                return field
        return None

    @staticmethod
    def _semantic_search_field(lowered: str) -> str | None:
        semantic_aliases = {
            "skills": ("languages do i know", "technologies do i know", "what can i use"),
            "education": ("course", "degree", "studying"),
            "occupation": ("work", "job", "profession"),
            "location": ("live", "from", "place"),
            "goals": ("want to become", "goal", "aim"),
        }
        for field, terms in semantic_aliases.items():
            if any(term in lowered for term in terms) and lowered.endswith("?"):
                return field
        return None

    def _get_field_value(self, field: str) -> str | list[str] | None:
        if field in PROFILE_FIELDS:
            return getattr(self.data.profile, field) or None
        if field in PREFERENCE_FIELDS:
            return getattr(self.data.preferences, field) or None
        if field in LIST_FIELDS:
            return getattr(self.data, field) or None
        return None

    def _clear_field(self, field: str) -> bool:
        if field in PROFILE_FIELDS:
            had_value = bool(getattr(self.data.profile, field))
            setattr(self.data.profile, field, "")
            return had_value
        if field in PREFERENCE_FIELDS:
            had_value = bool(getattr(self.data.preferences, field))
            setattr(self.data.preferences, field, "")
            return had_value
        if field in LIST_FIELDS:
            target = getattr(self.data, field)
            had_value = bool(target)
            target.clear()
            return had_value
        return False

    @staticmethod
    def _category_for_field(field: str) -> str:
        if field in PROFILE_FIELDS:
            return "profile"
        if field in PREFERENCE_FIELDS:
            return "preferences"
        return field

    @staticmethod
    def _looks_like_memory_query(text: str) -> bool:
        lowered = text.lower()
        return lowered.startswith(("what ", "who ", "where ", "do you ", "forget ", "remember", "clear "))

    @staticmethod
    def _log_event(title: str, field: str, value: str, confidence: float, started: float) -> None:
        LOGGER.info(
            "\n=========================\n%s\n\nDetected Entity\n%s\n\nValue\n%s\n\nConfidence Score\n%.2f\n\nExecution\n%.3f sec\n=========================",
            title,
            field,
            value,
            confidence,
            time.perf_counter() - started,
        )
