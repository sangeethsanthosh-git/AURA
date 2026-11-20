"""
AURA Lightweight Native OCR Service
Provides ultra-fast in-memory text recognition using Windows Media OCR (WinRT).
Enforces zero disk writes, 0 MB VRAM footprint, perceptual caching, and precise word coordinate localization.
"""

from typing import Dict, Any, Optional, Tuple, List
import io
import time
import asyncio
import logging
from PIL import Image

from backend.services.perception_cache import perception_cache

logger = logging.getLogger(__name__)


class OCRService:
    """Zero-VRAM Windows Native OCR with Perceptual Caching."""

    def __init__(self):
        self._engine = None
        self._available = False
        self._last_ocr_duration_ms: float = 0.0
        self._total_ocr_runs: int = 0
        self._total_ocr_ms: float = 0.0
        self._init_engine()

    def _init_engine(self) -> None:
        """Initializes native Windows Media OCR engine."""
        try:
            from winsdk.windows.media.ocr import OcrEngine
            from winsdk.windows.globalization import Language

            lang = Language("en-US")
            if OcrEngine.is_language_supported(lang):
                self._engine = OcrEngine.try_create_from_language(lang)
                self._available = self._engine is not None
                if self._available:
                    logger.info("Windows Media OCR engine initialized successfully.")
        except Exception as e:
            logger.warning(f"Native Windows Media OCR initialization note: {e}")
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    async def _recognize_winrt_async(self, png_bytes: bytes) -> Dict[str, Any]:
        """Runs Windows Media OCR asynchronously on in-memory PNG bytes."""
        from winsdk.windows.graphics.imaging import BitmapDecoder
        from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream)
        writer.write_bytes(png_bytes)
        await writer.store_async()
        await writer.flush_async()
        stream.seek(0)

        decoder = await BitmapDecoder.create_async(stream)
        software_bitmap = await decoder.get_software_bitmap_async()

        result = await self._engine.recognize_async(software_bitmap)

        words_data: List[Dict[str, Any]] = []
        lines_data: List[Dict[str, Any]] = []

        for line in result.lines:
            line_text = line.text.strip()
            l_words: List[str] = []
            for word in line.words:
                w_text = word.text.strip()
                rect = word.bounding_rect
                bx = int(rect.x)
                by = int(rect.y)
                bw = int(rect.width)
                bh = int(rect.height)
                cx = bx + (bw // 2)
                cy = by + (bh // 2)

                words_data.append({
                    "text": w_text,
                    "box": {"x": bx, "y": by, "width": bw, "height": bh},
                    "center": (cx, cy),
                })
                l_words.append(w_text)

            lines_data.append({
                "text": line_text,
                "words": l_words,
            })

        # Explicit release
        del software_bitmap
        del decoder
        del writer
        del stream

        return {
            "full_text": result.text.strip() if result.text else "",
            "lines": lines_data,
            "words": words_data,
        }

    def recognize_image(
        self,
        image: Image.Image,
        hwnd: int = 0,
        window_title: str = "Desktop",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Recognizes text from in-memory PIL Image.
        Checks PerceptionCache first; if screen is unchanged, returns cached result in < 0.2ms.
        """
        t0 = time.perf_counter()
        resolution = (image.width, image.height)
        screen_hash = perception_cache.calculate_screen_hash(image)

        # 1. Perception Cache Check
        if use_cache:
            cached = perception_cache.get_ocr(screen_hash, hwnd, resolution, window_title)
            if cached is not None:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                return {
                    "full_text": cached.get("full_text", ""),
                    "lines": cached.get("lines", []),
                    "words": cached.get("words", []),
                    "word_count": len(cached.get("words", [])),
                    "from_cache": True,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "screen_hash": screen_hash,
                }

        # 2. Perform OCR in Memory
        if not self._available:
            return {
                "full_text": "",
                "lines": [],
                "words": [],
                "word_count": 0,
                "from_cache": False,
                "error": "OCR engine not available",
                "elapsed_ms": 0.0,
            }

        # Encode in-memory PNG
        buf = io.BytesIO()
        # If image is excessively large (>1080p), resize for OCR speed while retaining accuracy
        scale_factor = 1.0
        target_img = image
        if image.width > 2560 or image.height > 1440:
            scale_factor = 0.5
            target_img = image.resize(
                (int(image.width * scale_factor), int(image.height * scale_factor)),
                Image.Resampling.BILINEAR,
            )

        target_img.save(buf, format="PNG")
        png_bytes = buf.getvalue()
        buf.close()

        # Run async OCR safely in isolated thread to prevent event-loop collisions
        try:
            import concurrent.futures

            def _run_isolated():
                return asyncio.run(self._recognize_winrt_async(png_bytes))

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                ocr_raw = ex.submit(_run_isolated).result(timeout=6.0)

            # Rescale boxes back to original screen coordinates if downscaled
            if scale_factor != 1.0:
                inv_scale = 1.0 / scale_factor
                for w in ocr_raw["words"]:
                    w["box"]["x"] = int(w["box"]["x"] * inv_scale)
                    w["box"]["y"] = int(w["box"]["y"] * inv_scale)
                    w["box"]["width"] = int(w["box"]["width"] * inv_scale)
                    w["box"]["height"] = int(w["box"]["height"] * inv_scale)
                    w["center"] = (
                        int(w["center"][0] * inv_scale),
                        int(w["center"][1] * inv_scale),
                    )

            elapsed_ms = (time.perf_counter() - t0) * 1000
            self._last_ocr_duration_ms = elapsed_ms
            self._total_ocr_runs += 1
            self._total_ocr_ms += elapsed_ms

            # 3. Store in Perception Cache
            if use_cache:
                perception_cache.put_ocr(
                    screen_hash=screen_hash,
                    hwnd=hwnd,
                    resolution=resolution,
                    window_title=window_title,
                    ocr_data=ocr_raw,
                )

            return {
                "full_text": ocr_raw.get("full_text", ""),
                "lines": ocr_raw.get("lines", []),
                "words": ocr_raw.get("words", []),
                "word_count": len(ocr_raw.get("words", [])),
                "from_cache": False,
                "elapsed_ms": round(elapsed_ms, 2),
                "screen_hash": screen_hash,
            }

        except Exception as e:
            logger.error(f"Error during Windows Media OCR: {e}", exc_info=True)
            return {
                "full_text": "",
                "lines": [],
                "words": [],
                "word_count": 0,
                "from_cache": False,
                "error": str(e),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
            }

    def find_text_coordinate(
        self,
        query: str,
        image: Image.Image,
        hwnd: int = 0,
        window_title: str = "Desktop",
    ) -> Optional[Tuple[int, int]]:
        """
        Locates the physical screen coordinate (cx, cy) of a word or phrase on the screen using OCR.
        """
        res = self.recognize_image(image, hwnd=hwnd, window_title=window_title)
        q = query.strip().lower()

        # 1. Exact or substring match in words
        for w in res.get("words", []):
            if q == w["text"].lower() or q in w["text"].lower():
                return w["center"]

        # 2. Match in whole line
        for line in res.get("lines", []):
            if q in line["text"].lower():
                # Find matching word in line
                for w in res.get("words", []):
                    if w["text"].lower() in q or q in w["text"].lower():
                        return w["center"]

        return None

    def get_metrics(self) -> Dict[str, Any]:
        """Returns OCR performance telemetry."""
        avg_ms = round(self._total_ocr_ms / self._total_ocr_runs, 2) if self._total_ocr_runs > 0 else 0.0
        return {
            "available": self._available,
            "engine": "Windows.Media.Ocr.OcrEngine (Native WinRT)",
            "last_duration_ms": round(self._last_ocr_duration_ms, 2),
            "average_duration_ms": avg_ms,
            "total_runs": self._total_ocr_runs,
        }


# Global OCR service instance
ocr_service = OCRService()
