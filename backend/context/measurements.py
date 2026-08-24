"""Storage and context-size measurement utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def directory_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def collect_context_measurements(bundle: Any | None = None, data_root: Path | str = "backend/data") -> dict[str, int]:
    root = Path(data_root)
    return {
        "context_chars": len(getattr(bundle, "text", "") or ""),
        "context_items": len(getattr(bundle, "items", []) or []),
        "memory_json_bytes": directory_size_bytes(root / "memory.json"),
        "daily_memory_bytes": directory_size_bytes(root / "memory" / "daily"),
        "knowledge_bytes": directory_size_bytes(root / "knowledge"),
        "temporary_bytes": directory_size_bytes(root / "tmp"),
    }
