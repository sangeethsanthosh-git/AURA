"""JSON-backed local knowledge store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.knowledge.models import DocumentChunk, KnowledgeDocument


class KnowledgeStore:
    """Stores metadata and chunks under backend/data/knowledge."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else Path(__file__).resolve().parents[1] / "data" / "knowledge"
        self.extracted_dir = self.root / "extracted"
        self.index_path = self.root / "index.json"

    def load(self) -> tuple[list[KnowledgeDocument], list[DocumentChunk]]:
        if not self.index_path.exists():
            return [], []
        raw = json.loads(self.index_path.read_text(encoding="utf-8"))
        documents = [KnowledgeDocument.from_dict(item) for item in raw.get("documents", []) if isinstance(item, dict)]
        chunks = [DocumentChunk.from_dict(item) for item in raw.get("chunks", []) if isinstance(item, dict)]
        return documents, chunks

    def save(self, documents: list[KnowledgeDocument], chunks: list[DocumentChunk]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "version": 1,
            "documents": [document.to_dict() for document in documents],
            "chunks": [chunk.to_dict() for chunk in chunks],
        }
        self.index_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def write_extracted(self, document_id: str, text: str) -> str:
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        path = self.extracted_dir / f"{document_id}.txt"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def delete_extracted(self, document_id: str) -> None:
        path = self.extracted_dir / f"{document_id}.txt"
        if path.exists():
            path.unlink()
