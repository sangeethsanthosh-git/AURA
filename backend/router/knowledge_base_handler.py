"""Local file intelligence and knowledge-base intent handler."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from backend.knowledge.knowledge_manager import KnowledgeManager
from backend.utils.responses import error_response


class KnowledgeBaseHandler:
    """Parses lightweight file/knowledge commands and delegates to KnowledgeManager."""

    PATH_PATTERN = re.compile(
        r"(?P<quoted>\"[^\"]+\.(?:txt|md|pdf)\"|'[^']+\.(?:txt|md|pdf)')|"
        r"(?P<drive>[A-Za-z]:[^\n\r\"']+?\.(?:txt|md|pdf))|"
        r"(?P<plain>\S+\.(?:txt|md|pdf))",
        re.IGNORECASE,
    )

    def __init__(self, manager: KnowledgeManager) -> None:
        self.manager = manager

    def handle_file_operation(self, prompt: str) -> dict[str, Any]:
        lowered = prompt.lower()
        if "clear" in lowered and "document" in lowered:
            return self.manager.clear_temporary()
        path = self._extract_path(prompt)
        if not path:
            return error_response("knowledge", "file_operation", "Please provide or attach a supported local file.")
        return self.manager.analyze_file(path)

    def handle_knowledge(self, prompt: str) -> dict[str, Any]:
        lowered = prompt.lower()
        path = self._extract_path(prompt)
        if path and any(term in lowered for term in ("add", "remember", "save", "import")):
            return self.manager.add_document(path)
        if path:
            return self.manager.analyze_file(path, query=prompt)
        if any(term in lowered for term in ("list", "show")) and "knowledge" in lowered:
            return self.manager.list_documents()
        if any(term in lowered for term in ("remove", "delete", "forget")) and "document" in lowered:
            return self.manager.remove_document(self._remove_target(prompt))
        if any(term in lowered for term in ("this document", "the document", "active document")):
            return self.manager.answer_temporary(prompt)
        return self.manager.search(prompt)

    @classmethod
    def _extract_path(cls, prompt: str) -> str | None:
        match = cls.PATH_PATTERN.search(prompt)
        if not match:
            return None
        value = match.group("quoted") or match.group("drive") or match.group("plain") or ""
        return value.strip(" .'\"")

    @staticmethod
    def _remove_target(prompt: str) -> str:
        cleaned = re.sub(r"\b(remove|delete|forget|document|from|knowledge|base)\b", " ", prompt, flags=re.IGNORECASE)
        return " ".join(cleaned.split()).strip(" .")
