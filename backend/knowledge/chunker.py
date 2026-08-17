"""Document chunking for lightweight local retrieval."""

from __future__ import annotations

import re
from uuid import uuid4

from backend.knowledge.models import DocumentChunk


class DocumentChunker:
    """Creates moderately sized chunks using headings and paragraphs."""

    def __init__(self, max_chars: int = 1200, overlap_chars: int = 120) -> None:
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, document_id: str, text: str) -> list[DocumentChunk]:
        blocks = self._blocks(text)
        chunks: list[DocumentChunk] = []
        current: list[str] = []
        current_section = ""
        ordinal = 0
        for section, block in blocks:
            if section:
                current_section = section
            if sum(len(item) for item in current) + len(block) + 2 > self.max_chars and current:
                chunks.append(self._make(document_id, "\n\n".join(current), current_section, ordinal))
                ordinal += 1
                tail = "\n\n".join(current)[-self.overlap_chars :]
                current = [tail] if tail.strip() else []
            current.append(block)
        if current:
            chunks.append(self._make(document_id, "\n\n".join(current), current_section, ordinal))
        return chunks

    @staticmethod
    def _blocks(text: str) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        section = ""
        for raw in re.split(r"\n\s*\n", text):
            block = raw.strip()
            if not block:
                continue
            heading = re.match(r"^(#{1,6})\s+(.+)$", block)
            if heading:
                section = heading.group(2).strip()
            result.append((section if heading else "", block))
        return result

    @staticmethod
    def _make(document_id: str, text: str, section: str, ordinal: int) -> DocumentChunk:
        return DocumentChunk(chunk_id=uuid4().hex, document_id=document_id, text=text.strip(), section=section, ordinal=ordinal)
