"""Stable OCR provider interface for AURA Eyes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OCRRegion:
    text: str
    confidence: float | None = None
    bbox: tuple[int, int, int, int] | None = None
    language: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def safe_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "language": self.language,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class OCRResult:
    success: bool
    provider: str
    text: str = ""
    languages: tuple[str, ...] = ()
    regions: tuple[OCRRegion, ...] = ()
    confidence: float | None = None
    model: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def safe_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "provider": self.provider,
            "text": self.text,
            "languages": list(self.languages),
            "regions": [region.safe_dict() for region in self.regions],
            "confidence": self.confidence,
            "model": self.model,
            "error": self.error,
            "metadata": self.metadata,
        }


class OCRProvider(ABC):
    provider_name = "Unavailable OCR Provider"

    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the OCR runtime and required local models are usable."""

    @abstractmethod
    def supported_languages(self) -> tuple[str, ...]:
        """Return language codes this provider can recognize."""

    @abstractmethod
    def recognize(self, image_path: Path, languages: tuple[str, ...]) -> OCRResult:
        """Recognize text from an on-demand temporary image."""

    def unload(self) -> None:
        """Release provider resources. Providers may override this."""

