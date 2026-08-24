"""Lightweight memory retrieval and storage decisions."""

from __future__ import annotations

import re

from backend.memory.memory_models import MemoryCategory, MemoryPlan, RetrievalDecision, StorageDecision
from backend.memory.memory_utils import normalize_text


class MemoryDecisionEngine:
    """Chooses the smallest useful local-memory action for one user message."""

    DAILY_RECALL_TERMS = (
        "what were we discussing earlier today",
        "what did we discuss today",
        "earlier today",
        "today's conversation",
        "summarize today",
    )
    LONG_TERM_RECALL_TERMS = (
        "what is my",
        "who am i",
        "what do you remember",
        "do you remember",
        "tell me about me",
    )
    CASUAL_TERMS = {"hello", "hi", "hey", "thanks", "thank you", "how are you"}
    CURRENT_INFO_TERMS = ("today", "latest", "recent", "current", "news", "weather", "stock price", "search")
    AMBIGUOUS_REMEMBER_TERMS = ("remember this article", "remember this page", "remember this website", "remember this search")
    SENSITIVE_TERMS = ("password", "api key", "secret", "token", "credit card", "bank account")

    def plan(self, text: str) -> MemoryPlan:
        normalized = normalize_text(text)
        lowered = normalized.lower()

        if self._looks_like_math(lowered):
            return MemoryPlan(reason="Math request does not need memory.")
        if lowered in self.CASUAL_TERMS or lowered.strip("?!.,") in self.CASUAL_TERMS:
            return MemoryPlan(RetrievalDecision.SESSION, StorageDecision.SESSION_ONLY, "Casual message kept only in session.", confidence=0.75)
        if any(term in lowered for term in self.SENSITIVE_TERMS) and lowered.startswith(("remember ", "remember that ", "remember this ")):
            return MemoryPlan(RetrievalDecision.SESSION, StorageDecision.ASK_USER, "Sensitive memory requires explicit confirmation.", confidence=0.99)
        if lowered.startswith(self.AMBIGUOUS_REMEMBER_TERMS):
            return MemoryPlan(RetrievalDecision.SESSION, StorageDecision.ASK_USER, "Ambiguous external content memory requires confirmation.", confidence=0.92)
        if lowered.startswith(("remember ", "remember that ", "remember this ")):
            return MemoryPlan(RetrievalDecision.SESSION, StorageDecision.LONG_TERM, "Explicit remember command.", confidence=0.98)
        if lowered.startswith(("forget ", "remove ", "delete memory")):
            return MemoryPlan(RetrievalDecision.LONG_TERM, StorageDecision.DO_NOT_STORE, "Explicit forget command.", confidence=0.97)
        if any(term in lowered for term in self.DAILY_RECALL_TERMS):
            return MemoryPlan(RetrievalDecision.DAILY, StorageDecision.DO_NOT_STORE, "Daily history requested.", confidence=0.94)
        if any(term in lowered for term in self.LONG_TERM_RECALL_TERMS):
            return MemoryPlan(RetrievalDecision.LONG_TERM, StorageDecision.DO_NOT_STORE, "Long-term personal memory requested.", confidence=0.94)
        if self._looks_like_stable_fact(lowered):
            return MemoryPlan(RetrievalDecision.NONE, StorageDecision.LONG_TERM, "Stable fact or preference detected.", category=self._category(lowered), confidence=0.86)
        if self._looks_like_daily_context(lowered):
            return MemoryPlan(RetrievalDecision.SESSION, StorageDecision.DAILY, "Useful daily context detected.", category=MemoryCategory.IMPORTANT_CONTEXT.value, confidence=0.72)
        if any(term in lowered for term in self.CURRENT_INFO_TERMS):
            return MemoryPlan(RetrievalDecision.SESSION, StorageDecision.SESSION_ONLY, "Volatile/current information is temporary by default.", confidence=0.78)
        return MemoryPlan(RetrievalDecision.NONE, StorageDecision.DO_NOT_STORE, "No durable memory needed.", confidence=0.60)

    @staticmethod
    def _looks_like_math(text: str) -> bool:
        return bool(re.search(r"\d\s*(?:[+\-*/x×÷]|Ã—|Ã·)\s*\d", text))

    @staticmethod
    def _looks_like_stable_fact(text: str) -> bool:
        starters = ("my name is", "call me", "i live in", "i am from", "i study", "i am studying", "my favorite", "my favourite", "i prefer", "my goal is", "my project is")
        return text.startswith(starters)

    @staticmethod
    def _looks_like_daily_context(text: str) -> bool:
        return any(term in text for term in ("worked on", "discussed", "thinking of", "changed", "continued", "improved", "built"))

    @staticmethod
    def _category(text: str) -> str:
        if "prefer" in text or "favorite" in text or "favourite" in text:
            return MemoryCategory.PREFERENCE.value
        if "goal" in text:
            return MemoryCategory.GOAL.value
        if "project" in text or "aura" in text:
            return MemoryCategory.PROJECT_CONTEXT.value
        return MemoryCategory.PERSONAL_FACT.value
