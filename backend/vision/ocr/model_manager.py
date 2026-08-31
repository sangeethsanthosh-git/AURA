"""Project-local OCR model discovery and status helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from backend.vision.ocr.paths import OCR_MODEL_ROOT, ensure_ocr_directories, ocr_environment


@dataclass(frozen=True)
class OCRModelStatus:
    name: str
    installed: bool
    path: Path
    size_bytes: int
    languages: tuple[str, ...]
    license: str
    notes: str = ""

    def safe_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "installed": self.installed,
            "path": str(self.path),
            "size_bytes": self.size_bytes,
            "languages": list(self.languages),
            "license": self.license,
            "notes": self.notes,
        }


class OCRModelManager:
    """Keeps AURA-controlled OCR artifacts inside the project directory."""

    SURYA_MODEL_DIR = OCR_MODEL_ROOT / "primary" / "surya"

    def __init__(self, model_root: Path = OCR_MODEL_ROOT) -> None:
        self.model_root = model_root
        ensure_ocr_directories()

    def apply_environment(self) -> dict[str, str]:
        env = ocr_environment()
        os.environ.update(env)
        return env

    def status(self) -> dict[str, object]:
        self.apply_environment()
        surya = self.surya_status()
        return {
            "model_root": str(self.model_root),
            "cache_environment": ocr_environment(),
            "models": [surya.safe_dict()],
            "policy": "UNLOAD_AFTER_TASK",
        }

    def surya_status(self) -> OCRModelStatus:
        installed = self._surya_package_available()
        size = self._directory_size(self.SURYA_MODEL_DIR)
        return OCRModelStatus(
            name="Surya OCR",
            installed=installed,
            path=self.SURYA_MODEL_DIR,
            size_bytes=size,
            languages=("en", "ml", "mixed"),
            license="Code: GPL-3.0/Apache notices vary by package version; weights: non-commercial/dual-license terms per Surya model card.",
            notes="Primary Malayalam-capable OCR path. Model files must be cached under models/ocr or data/ocr/cache before offline use.",
        )

    @staticmethod
    def _surya_package_available() -> bool:
        try:
            import surya  # noqa: F401
        except ImportError:
            return False
        return True

    @staticmethod
    def _directory_size(path: Path) -> int:
        if not path.exists():
            return 0
        return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())

