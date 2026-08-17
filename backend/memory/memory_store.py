"""JSON-backed persistent memory store."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from backend.memory.memory_models import MemoryData

LOGGER = logging.getLogger(__name__)


class JsonMemoryStore:
    """Persistent memory store with a SQLite-friendly public surface."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else Path(__file__).resolve().parents[1] / "data" / "memory.json"

    def load(self) -> MemoryData:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            data = MemoryData.empty()
            self.save(data)
            LOGGER.info("Memory Load: created missing memory file at %s", self.path)
            return data

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Memory Load: corrupted JSON recovered safely. error=%r", exc)
            self._backup_corrupted_file()
            data = MemoryData.empty()
            self.save(data)
            return data

        data = self._from_raw(raw)
        LOGGER.info("Memory Load: profile=%s skills=%d goals=%d", bool(data.profile.name), len(data.skills), len(data.goals))
        return data

    def save(self, data: MemoryData) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 2, **data.to_dict()}
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        LOGGER.info("Memory Save: %s", self.path)

    def _from_raw(self, raw: Any) -> MemoryData:
        if not isinstance(raw, dict):
            return MemoryData.empty()
        if "profile" in raw or "preferences" in raw:
            return MemoryData.from_dict(raw)
        return self._migrate_legacy_facts(raw)

    @staticmethod
    def _migrate_legacy_facts(raw: dict[str, Any]) -> MemoryData:
        data = MemoryData.empty()
        facts = raw.get("facts", [])
        if not isinstance(facts, list):
            return data
        for item in facts:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip()
            value = str(item.get("value", "")).strip()
            if not key or not value:
                continue
            if key == "favorite_language":
                data.preferences.favorite_language = value
            elif key == "preference":
                data.preferences.preferred_ai = value
            elif key == "goal":
                data.goals.append(value)
            elif key == "project":
                data.projects.append(value)
            elif key in data.profile.__dataclass_fields__:
                if key == "occupation" and value.lower().startswith("studying "):
                    data.profile.education = value.split(" ", 1)[1].strip()
                else:
                    setattr(data.profile, key, value)
        return data

    def _backup_corrupted_file(self) -> None:
        if not self.path.exists():
            return
        backup = self.path.with_suffix(f"{self.path.suffix}.corrupt")
        try:
            shutil.copy2(self.path, backup)
        except OSError:
            LOGGER.exception("Memory Load: failed to back up corrupted memory file.")
