"""Structured web intelligence models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str | None = None
    publication_date: str | None = None
    relevance: float | None = None

    def to_source(self, retrieved: bool = False) -> dict[str, Any]:
        domain = self.source or urlparse(self.url).netloc
        return {
            "title": self.title,
            "url": self.url,
            "domain": domain,
            "publication_date": self.publication_date,
            "retrieved_at": utc_now_iso() if retrieved else None,
            "relevance": self.relevance,
            "snippet": self.snippet,
            "retrieved": retrieved,
        }


@dataclass(frozen=True)
class RetrievedPage:
    result: SearchResult
    success: bool
    content: str = ""
    status_code: int | None = None
    retrieved_at: str = field(default_factory=utc_now_iso)
    error: str | None = None

    def to_source(self) -> dict[str, Any]:
        source = self.result.to_source(retrieved=self.success)
        source.update(
            {
                "status_code": self.status_code,
                "retrieved_at": self.retrieved_at,
                "content_available": bool(self.content),
                "error": self.error,
            }
        )
        return source


@dataclass(frozen=True)
class WebSource:
    title: str
    url: str
    domain: str
    publication_date: str | None
    retrieved_at: str
    relevance: float | None
    snippet: str
