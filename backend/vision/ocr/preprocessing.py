"""Lightweight screen OCR preprocessing."""

from __future__ import annotations

from pathlib import Path


class OcrPreprocessor:
    """Prepare UI screenshots without permanently storing derived images."""

    def prepare(self, image_path: Path, *, scale: float = 1.5) -> Path:
        try:
            from PIL import Image, ImageEnhance, ImageFilter
        except ImportError:
            return image_path

        try:
            with Image.open(image_path) as image:
                working = image.convert("RGB")
                if scale > 1:
                    width, height = working.size
                    working = working.resize((int(width * scale), int(height * scale)))
                working = ImageEnhance.Contrast(working).enhance(1.12)
                working = ImageEnhance.Sharpness(working).enhance(1.08)
                working = working.filter(ImageFilter.SHARPEN)
                working.save(image_path, "PNG")
        except Exception:
            return image_path
        return image_path
