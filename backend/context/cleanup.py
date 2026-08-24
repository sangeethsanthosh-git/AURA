"""Cleanup helpers for temporary AURA context and local caches."""

from __future__ import annotations

from pathlib import Path
from time import time

from backend.context.temporary import TemporaryContextStore


class ContextCleanupManager:
    """Deletes expired transient records and bounded local cache files."""

    def __init__(self, temporary_store: TemporaryContextStore | None = None, roots: list[Path] | None = None) -> None:
        self.temporary_store = temporary_store or TemporaryContextStore()
        self.roots = roots or [Path("backend/data/tmp"), Path("output")]

    def cleanup(self, max_age_seconds: int = 3600) -> dict[str, int]:
        removed_records = self.temporary_store.cleanup()
        removed_files = 0
        cutoff = time() - max_age_seconds
        for root in self.roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file() and path.stat().st_mtime < cutoff and self._is_temporary(path):
                    path.unlink(missing_ok=True)
                    removed_files += 1
        return {"temporary_context_records": removed_records, "temporary_files": removed_files}

    @staticmethod
    def _is_temporary(path: Path) -> bool:
        name = path.name.lower()
        return name.startswith(("aura_screen_", "speech_", "tmp_", "cache_")) or path.suffix.lower() in {".tmp", ".wav"}
