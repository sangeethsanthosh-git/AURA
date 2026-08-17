"""Compact local Markdown daily memory."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class DailyMemory:
    """Stores concise daily entries without dumping full conversations."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root else Path(__file__).resolve().parents[1] / "data" / "memory" / "daily"

    def append(self, text: str, day: date | None = None) -> bool:
        entry = self._compact(text)
        if not entry:
            return False
        path = self.path_for(day)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = path.read_text(encoding="utf-8") if path.exists() else self._header(day)
        line = f"- {entry}"
        if line.lower() in content.lower():
            LOGGER.info("Daily Memory: duplicate prevented.")
            return False
        path.write_text(content.rstrip() + "\n" + line + "\n", encoding="utf-8")
        LOGGER.info("Daily Memory: entry stored at %s", path)
        return True

    def read(self, day: date | None = None) -> list[str]:
        path = self.path_for(day)
        if not path.exists():
            return []
        return [line[2:].strip() for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("- ")]

    def path_for(self, day: date | None = None) -> Path:
        selected = day or date.today()
        return self.root / f"{selected.isoformat()}.md"

    @staticmethod
    def _header(day: date | None = None) -> str:
        selected = day or date.today()
        return f"# AURA Daily Memory\n\nDate: {selected.isoformat()}\n\n## Important Interactions\n"

    @staticmethod
    def _compact(text: str) -> str:
        cleaned = " ".join(text.strip().split()).strip(" .")
        if not cleaned or cleaned.lower() in {"hello", "hi", "hey", "thanks"}:
            return ""
        return cleaned[:180] + ("..." if len(cleaned) > 180 else ".")
