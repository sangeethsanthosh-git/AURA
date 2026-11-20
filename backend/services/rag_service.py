"""
RAG Service (Phase 9: Local Document Q&A / Personal Knowledge)
Indexes local documents (Markdown, text, code, JSON), stores semantic chunks in SQLite,
and provides fast contextual retrieval to ground Ollama responses in user files.
"""

import logging
import math
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "is", "was", "are", "were", "it", "this", "that", "these", "those", "what",
    "how", "why", "when", "where", "who", "which", "my", "your", "our", "their",
    "can", "you", "tell", "me", "about", "search", "find", "document", "documents",
}


def tokenize(text: str) -> List[str]:
    """Extract clean lowercase word tokens."""
    words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
    return [w for w in words if w not in STOPWORDS]


class RAGService:
    """Manages document chunking, indexing, and relevance retrieval."""

    def __init__(self, doc_dir: Optional[str] = None, db_path: str = "aura.db"):
        self.doc_dir = Path(doc_dir or "backend/data/documents").resolve()
        self.doc_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(Path(db_path).resolve())
        self._init_db()
        self._ensure_sample_doc()
        self.index_directory()

    def _init_db(self) -> None:
        """Initialize document chunks schema in SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    chunk_idx INTEGER NOT NULL,
                    snippet TEXT NOT NULL,
                    lower_snippet TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    mtime REAL NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_doc_chunks_path ON document_chunks(file_path);
                """
            )
            conn.commit()

    def _ensure_sample_doc(self) -> None:
        """Create a helpful sample note if directory is empty."""
        sample_file = self.doc_dir / "welcome_aura.md"
        if not sample_file.exists():
            sample_file.write_text(
                "# Welcome to AURA Personal Knowledge\n\n"
                "AURA can index your local project notes, documents, and code files.\n\n"
                "## Key Features\n"
                "- Fast local search with zero cloud upload\n"
                "- Supports Markdown (.md), Text (.txt), JSON (.json), and Code files (.py, .ts, .js)\n"
                "- Ask questions like: 'What did my notes say about database setup?'\n\n"
                "## Project Guidelines\n"
                "The AURA project runs on Windows 11 with an RTX 2050 GPU and Faster-Whisper CPU transcription.\n",
                encoding="utf-8",
            )

    def chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 60) -> List[str]:
        """Split text into overlapping semantic passages."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []

        for p in paragraphs:
            if len(p) <= chunk_size:
                chunks.append(p)
            else:
                # Segment long paragraph
                start = 0
                while start < len(p):
                    end = min(start + chunk_size, len(p))
                    segment = p[start:end].strip()
                    if segment:
                        chunks.append(segment)
                    if end >= len(p):
                        break
                    start += (chunk_size - overlap)

        return chunks if chunks else [text[:chunk_size]]

    def index_file(self, file_path: Path) -> int:
        """Index a single document file into chunks."""
        try:
            mtime = file_path.stat().st_mtime
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                # Check existing mtime
                cur.execute("SELECT mtime FROM document_chunks WHERE file_path = ? LIMIT 1", (str(file_path),))
                row = cur.fetchone()
                if row and abs(row[0] - mtime) < 0.1:
                    return 0  # Up to date

                # Remove old chunks for this file
                cur.execute("DELETE FROM document_chunks WHERE file_path = ?", (str(file_path),))

                text = file_path.read_text(encoding="utf-8", errors="replace")
                chunks = self.chunk_text(text)

                for idx, c in enumerate(chunks):
                    words = len(c.split())
                    cur.execute(
                        """
                        INSERT INTO document_chunks (doc_name, file_path, chunk_idx, snippet, lower_snippet, word_count, mtime)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (file_path.name, str(file_path), idx, c, c.lower(), words, mtime),
                    )
                conn.commit()
                return len(chunks)
        except Exception as e:
            logger.error(f"Error indexing {file_path}: {e}")
            return 0

    def index_directory(self) -> Dict[str, Any]:
        """Scan document directory and index all supported files."""
        supported_exts = {".txt", ".md", ".markdown", ".json", ".csv", ".py", ".js", ".ts", ".html"}
        files = [p for p in self.doc_dir.rglob("*") if p.is_file() and p.suffix.lower() in supported_exts]

        total_chunks = 0
        indexed_files = 0
        for f in files:
            chunks_added = self.index_file(f)
            if chunks_added > 0:
                indexed_files += 1
                total_chunks += chunks_added

        return {
            "total_files": len(files),
            "indexed_files": indexed_files,
            "total_chunks_added": total_chunks,
        }

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search indexed document chunks using keyword frequency and phrase proximity scoring.
        Returns top matching chunks with metadata.
        """
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT id, doc_name, file_path, chunk_idx, snippet, lower_snippet FROM document_chunks")
            rows = cur.fetchall()

        scored_results = []
        q_lower = query.lower()

        for row in rows:
            snippet_lower = row["lower_snippet"]
            score = 0.0

            # 1. Exact phrase match bonus
            if q_lower in snippet_lower:
                score += 5.0

            # 2. Token matches
            matched_tokens = 0
            for token in q_tokens:
                occurrences = snippet_lower.count(token)
                if occurrences > 0:
                    matched_tokens += 1
                    score += (1.0 + math.log(occurrences + 1))

            # Coverage factor: ratio of query terms present
            coverage = matched_tokens / len(q_tokens)
            score *= (1.0 + coverage * 2.0)

            if score > 0.5:
                scored_results.append({
                    "id": row["id"],
                    "doc_name": row["doc_name"],
                    "file_path": row["file_path"],
                    "chunk_idx": row["chunk_idx"],
                    "snippet": row["snippet"],
                    "score": round(score, 2),
                })

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:top_k]

    def format_context_for_prompt(self, matches: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks as reference context for Ollama."""
        if not matches:
            return ""

        context_lines = ["\n[Context from your local documents]:"]
        for idx, m in enumerate(matches, 1):
            snippet_clean = m["snippet"].replace("\n", " ")
            context_lines.append(f"{idx}. (From {m['doc_name']}): \"{snippet_clean}\"")
        context_lines.append("Use this context when relevant to answer the user's question.\n")
        return "\n".join(context_lines)

    def list_documents(self) -> List[str]:
        """List distinct document names currently indexed."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT doc_name FROM document_chunks ORDER BY doc_name ASC")
            return [r[0] for r in cur.fetchall()]

    def get_chunk_count(self) -> int:
        """Get total number of indexed document chunks."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM document_chunks")
            row = cur.fetchone()
            return row[0] if row else 0
