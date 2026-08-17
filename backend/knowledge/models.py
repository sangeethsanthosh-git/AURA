"""Typed models for local knowledge documents."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    text: str
    section: str = ""
    ordinal: int = 0

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DocumentChunk":
        return cls(
            chunk_id=str(raw.get("chunk_id") or uuid4().hex),
            document_id=str(raw.get("document_id") or ""),
            text=str(raw.get("text") or ""),
            section=str(raw.get("section") or ""),
            ordinal=int(raw.get("ordinal") or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class KnowledgeDocument:
    document_id: str
    filename: str
    original_path: str
    content_hash: str
    file_type: str
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    extracted_path: str = ""
    size_bytes: int = 0
    title: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "KnowledgeDocument":
        return cls(
            document_id=str(raw.get("document_id") or uuid4().hex),
            filename=str(raw.get("filename") or ""),
            original_path=str(raw.get("original_path") or ""),
            content_hash=str(raw.get("content_hash") or ""),
            file_type=str(raw.get("file_type") or ""),
            created_at=str(raw.get("created_at") or utc_now_iso()),
            updated_at=str(raw.get("updated_at") or utc_now_iso()),
            extracted_path=str(raw.get("extracted_path") or ""),
            size_bytes=int(raw.get("size_bytes") or 0),
            title=str(raw.get("title") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    path: Path
    filename: str
    file_type: str
    content_hash: str
    text: str
    size_bytes: int
    title: str = ""


@dataclass(frozen=True, slots=True)
class SearchResult:
    document: KnowledgeDocument
    chunk: DocumentChunk
    score: float

    def to_source(self) -> dict[str, Any]:
        return {
            "document_id": self.document.document_id,
            "filename": self.document.filename,
            "section": self.chunk.section,
            "chunk_id": self.chunk.chunk_id,
            "score": round(self.score, 3),
        }
