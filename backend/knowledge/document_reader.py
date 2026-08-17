"""Safe local document validation and text extraction."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from backend.knowledge.models import ExtractedDocument


class DocumentReadError(ValueError):
    """Raised when a local file cannot be safely read as a document."""


class DocumentReader:
    """Reads explicitly selected local files as inert data."""

    SUPPORTED_TYPES = {".txt", ".md", ".pdf"}

    def __init__(self, max_size_mb: int = 15) -> None:
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def read(self, path: str | Path) -> ExtractedDocument:
        resolved = Path(path).expanduser().resolve()
        if not resolved.exists():
            raise DocumentReadError("File not found.")
        if not resolved.is_file():
            raise DocumentReadError("Selected path is not a file.")
        suffix = resolved.suffix.lower()
        if suffix not in self.SUPPORTED_TYPES:
            raise DocumentReadError(f"Unsupported file type: {suffix or 'unknown'}.")
        size = resolved.stat().st_size
        if size <= 0:
            raise DocumentReadError("The selected file is empty.")
        if size > self.max_size_bytes:
            raise DocumentReadError(f"File is too large. Limit is {self.max_size_bytes // (1024 * 1024)} MB.")

        content_hash = self._sha256(resolved)
        if suffix in {".txt", ".md"}:
            text = self._read_text(resolved)
        else:
            text = self._read_pdf(resolved)
        cleaned = self._clean_text(text)
        if not cleaned:
            if suffix == ".pdf":
                raise DocumentReadError("This PDF appears to contain scanned images or no extractable text.")
            raise DocumentReadError("No readable text was found in the selected file.")
        return ExtractedDocument(
            path=resolved,
            filename=resolved.name,
            file_type=suffix.lstrip("."),
            content_hash=content_hash,
            text=cleaned,
            size_bytes=size,
            title=resolved.stem,
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _read_text(path: Path) -> str:
        for encoding in ("utf-8-sig", "utf-8", "cp1252"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                raise DocumentReadError("Could not read the selected file.") from exc
        raise DocumentReadError("Could not decode the selected text file.")

    @staticmethod
    def _read_pdf(path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise DocumentReadError("PDF support requires the pypdf package.") from exc
        try:
            reader = PdfReader(str(path))
            if getattr(reader, "is_encrypted", False):
                raise DocumentReadError("This PDF is encrypted or password protected.")
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            return "\n\n".join(pages)
        except DocumentReadError:
            raise
        except Exception as exc:
            raise DocumentReadError("Could not extract text from this PDF.") from exc

    @staticmethod
    def _clean_text(text: str) -> str:
        text = text.replace("\x00", "")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
