"""Lightweight lexical retrieval over local knowledge chunks."""

from __future__ import annotations

import re
from collections import Counter

from backend.knowledge.models import DocumentChunk, KnowledgeDocument, SearchResult


STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "my",
    "what", "does", "do", "about", "say", "this", "that", "is", "are",
}


class KnowledgeRetriever:
    """Scores chunks with simple token overlap and term frequency."""

    def search(
        self,
        query: str,
        documents: list[KnowledgeDocument],
        chunks: list[DocumentChunk],
        limit: int = 5,
    ) -> list[SearchResult]:
        query_terms = self._terms(query)
        if not query_terms:
            return []
        documents_by_id = {document.document_id: document for document in documents}
        scored: list[SearchResult] = []
        for chunk in chunks:
            chunk_terms = self._terms(chunk.text + " " + chunk.section)
            if not chunk_terms:
                continue
            counts = Counter(chunk_terms)
            overlap = set(query_terms) & set(chunk_terms)
            if not overlap:
                continue
            score = sum(counts[term] for term in overlap) + len(overlap) * 1.5
            document = documents_by_id.get(chunk.document_id)
            if document:
                scored.append(SearchResult(document, chunk, float(score)))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    @staticmethod
    def _terms(text: str) -> list[str]:
        return [term for term in re.findall(r"[a-z0-9]{2,}", text.lower()) if term not in STOPWORDS]
