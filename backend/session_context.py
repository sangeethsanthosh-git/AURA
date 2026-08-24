"""Lightweight session continuity for recent turns and active topic."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SessionTurn:
    role: str
    content: str


@dataclass
class SessionContext:
    max_recent_turns: int = 12
    summarize_after_turns: int = 18
    recent_turns: list[SessionTurn] = field(default_factory=list)
    summary: str = ""
    active_topic: str | None = None
    active_entities: list[str] = field(default_factory=list)

    def add_turn(self, role: str, content: str) -> None:
        clean = " ".join(content.split())
        if not clean:
            return
        self.recent_turns.append(SessionTurn(role, clean))
        if role == "user":
            self._update_topic(clean)
        if len(self.recent_turns) > self.summarize_after_turns:
            self._summarize_old_turns()
        self.recent_turns = self.recent_turns[-self.max_recent_turns :]

    def relevant_context_for(self, user_text: str) -> str:
        lowered = user_text.lower()
        pronoun_followup = bool(re.search(r"\b(it|its|that|this|they|them|there|part|disadvantages|memory part)\b", lowered))
        lines: list[str] = []
        if self.summary:
            lines.append(f"Session summary: {self.summary}")
        if self.active_topic and pronoun_followup:
            lines.append(f"Active topic: {self.active_topic}")
        if self.active_entities and pronoun_followup:
            lines.append("Relevant entities: " + ", ".join(self.active_entities[:6]))
        if pronoun_followup:
            recent = self.recent_turns[-6:]
            if recent:
                lines.append("Recent turns:")
                lines.extend(f"{turn.role}: {turn.content[:240]}" for turn in recent)
        return "\n".join(lines)

    def _update_topic(self, text: str) -> None:
        match = re.search(r"\b(?:about|explain|describe|tell me about)\s+([A-Za-z0-9 +#._-]{2,80})", text, re.IGNORECASE)
        if match:
            self.active_topic = match.group(1).strip(" ?.!")
        entities = re.findall(r"\b[A-Z][A-Za-z0-9+#.-]{1,}\b", text)
        for entity in entities:
            if entity not in self.active_entities:
                self.active_entities.insert(0, entity)
        self.active_entities = self.active_entities[:12]

    def _summarize_old_turns(self) -> None:
        old = self.recent_turns[: -self.max_recent_turns]
        if not old:
            return
        snippets = []
        for turn in old[-8:]:
            snippets.append(f"{turn.role}: {turn.content[:120]}")
        prefix = (self.summary + " ") if self.summary else ""
        self.summary = (prefix + " | ".join(snippets))[-1200:]
