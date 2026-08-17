"""Local-first knowledge and temporary document context manager."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.knowledge.chunker import DocumentChunker
from backend.knowledge.document_reader import DocumentReadError, DocumentReader
from backend.knowledge.knowledge_store import KnowledgeStore
from backend.knowledge.models import DocumentChunk, ExtractedDocument, KnowledgeDocument, SearchResult, utc_now_iso
from backend.knowledge.retriever import KnowledgeRetriever
from backend.utils.responses import error_response, success_response


class KnowledgeManager:
    """Coordinates temporary file analysis and persistent local knowledge."""

    def __init__(
        self,
        store: KnowledgeStore | None = None,
        reader: DocumentReader | None = None,
        chunker: DocumentChunker | None = None,
        retriever: KnowledgeRetriever | None = None,
    ) -> None:
        self.store = store or KnowledgeStore()
        self.reader = reader or DocumentReader()
        self.chunker = chunker or DocumentChunker()
        self.retriever = retriever or KnowledgeRetriever()
        self.documents, self.chunks = self.store.load()
        self.temporary_document: ExtractedDocument | None = None
        self.temporary_chunks: list[DocumentChunk] = []

    def analyze_file(self, path: str | Path, query: str | None = None) -> dict[str, Any]:
        extracted = self._read(path)
        if isinstance(extracted, dict):
            return extracted
        document_id = "temporary"
        self.temporary_document = extracted
        self.temporary_chunks = self.chunker.chunk(document_id, extracted.text)
        if query:
            return self.answer_temporary(query)
        message = self._summary(extracted.text, extracted.filename)
        return success_response(
            "knowledge",
            "temporary_analysis",
            {
                "filename": extracted.filename,
                "file_type": extracted.file_type,
                "size_bytes": extracted.size_bytes,
                "temporary": True,
                "sources": [{"filename": extracted.filename, "section": "", "chunk_id": "temporary"}],
            },
            message,
        )

    def answer_temporary(self, query: str) -> dict[str, Any]:
        if not self.temporary_document:
            return error_response("knowledge", "temporary_query", "No active temporary document. Analyze a file first.")
        temp_doc = KnowledgeDocument(
            document_id="temporary",
            filename=self.temporary_document.filename,
            original_path=str(self.temporary_document.path),
            content_hash=self.temporary_document.content_hash,
            file_type=self.temporary_document.file_type,
            size_bytes=self.temporary_document.size_bytes,
            title=self.temporary_document.title,
        )
        results = self.retriever.search(query, [temp_doc], self.temporary_chunks, limit=3)
        return self._answer_from_results("temporary_query", query, results)

    def clear_temporary(self) -> dict[str, Any]:
        self.temporary_document = None
        self.temporary_chunks = []
        return success_response("knowledge", "clear_temporary", {}, "Temporary document context cleared.")

    def add_document(self, path: str | Path) -> dict[str, Any]:
        extracted = self._read(path)
        if isinstance(extracted, dict):
            return extracted
        existing = self._find_by_hash(extracted.content_hash)
        if existing:
            return success_response(
                "knowledge",
                "add_document",
                {"document": existing.to_dict(), "duplicate": True},
                f"{existing.filename} is already in the local knowledge base.",
            )
        document_id = uuid4().hex
        extracted_path = self.store.write_extracted(document_id, extracted.text)
        document = KnowledgeDocument(
            document_id=document_id,
            filename=extracted.filename,
            original_path=str(extracted.path),
            content_hash=extracted.content_hash,
            file_type=extracted.file_type,
            extracted_path=extracted_path,
            size_bytes=extracted.size_bytes,
            title=extracted.title,
        )
        chunks = self.chunker.chunk(document_id, extracted.text)
        self.documents.append(document)
        self.chunks.extend(chunks)
        self.store.save(self.documents, self.chunks)
        return success_response(
            "knowledge",
            "add_document",
            {"document": document.to_dict(), "chunks": len(chunks), "duplicate": False},
            f"Added {document.filename} to the local knowledge base.",
        )

    def list_documents(self) -> dict[str, Any]:
        return success_response(
            "knowledge",
            "list_documents",
            {"documents": [document.to_dict() for document in self.documents]},
            self._list_message(),
        )

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        results = self.retriever.search(query, self.documents, self.chunks, limit=limit)
        return self._answer_from_results("search", query, results)

    def remove_document(self, query: str) -> dict[str, Any]:
        target = self._find_document(query)
        if not target:
            return error_response("knowledge", "remove_document", "No matching knowledge document was found.")
        self.documents = [document for document in self.documents if document.document_id != target.document_id]
        self.chunks = [chunk for chunk in self.chunks if chunk.document_id != target.document_id]
        self.store.delete_extracted(target.document_id)
        self.store.save(self.documents, self.chunks)
        return success_response("knowledge", "remove_document", {"document_id": target.document_id}, f"Removed {target.filename} from local knowledge.")

    def _answer_from_results(self, action: str, query: str, results: list[SearchResult]) -> dict[str, Any]:
        if not results:
            return success_response(
                "knowledge",
                action,
                {"query": query, "sources": [], "chunks": []},
                "I could not find relevant information in the selected/local knowledge documents.",
            )
        excerpts = []
        for result in results:
            excerpt = result.chunk.text.strip().replace("\n", " ")
            excerpts.append(f"- {result.document.filename}: {excerpt[:420]}")
        message = "Relevant local knowledge:\n" + "\n".join(excerpts)
        return success_response(
            "knowledge",
            action,
            {
                "query": query,
                "sources": [result.to_source() for result in results],
                "chunks": [{"text": result.chunk.text, **result.to_source()} for result in results],
            },
            message,
        )

    def _read(self, path: str | Path) -> ExtractedDocument | dict[str, Any]:
        try:
            return self.reader.read(path)
        except DocumentReadError as exc:
            return error_response("knowledge", "read_document", str(exc))

    def _find_by_hash(self, content_hash: str) -> KnowledgeDocument | None:
        return next((document for document in self.documents if document.content_hash == content_hash), None)

    def _find_document(self, query: str) -> KnowledgeDocument | None:
        lowered = query.lower()
        for document in self.documents:
            if document.document_id == query or lowered in document.filename.lower() or lowered in document.title.lower():
                return document
        return None

    def _list_message(self) -> str:
        if not self.documents:
            return "No local knowledge documents have been added yet."
        names = ", ".join(document.filename for document in self.documents[:8])
        return f"Local knowledge documents: {names}"

    @staticmethod
    def _summary(text: str, filename: str) -> str:
        preview = " ".join(text.split())[:900]
        suffix = "..." if len(preview) >= 900 else ""
        return f"Temporary analysis for {filename}:\n{preview}{suffix}"
