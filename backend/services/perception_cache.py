"""
AURA Intelligent Perception Cache
Provides perceptual screen hashing, LRU caching for OCR and vision results,
TTL expiration, change detection, and memory pressure management.
"""

from typing import Dict, Any, Optional, Tuple, List
import time
import hashlib
import gc
import logging
from PIL import Image
import psutil

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached screen perception/OCR analysis."""

    def __init__(
        self,
        key: str,
        screen_hash: str,
        window_title: str,
        hwnd: int,
        resolution: Tuple[int, int],
        ocr_data: Optional[Dict[str, Any]] = None,
        vision_summary: Optional[str] = None,
        estimated_bytes: int = 1024,
    ):
        self.key = key
        self.screen_hash = screen_hash
        self.window_title = window_title
        self.hwnd = hwnd
        self.resolution = resolution
        self.ocr_data = ocr_data
        self.vision_summary = vision_summary
        self.created_at = time.time()
        self.last_accessed = self.created_at
        self.hit_count = 0
        self.estimated_bytes = estimated_bytes

    def is_expired(self, ttl_seconds: float) -> bool:
        return (time.time() - self.created_at) > ttl_seconds

    def touch(self) -> None:
        self.last_accessed = time.time()
        self.hit_count += 1


class PerceptionCache:
    """
    Intelligent, bounded cache for screen perception and OCR results.
    Invalidates on window focus change, resolution change, or screen content mutation.
    """

    def __init__(
        self,
        max_entries: int = 15,
        max_memory_mb: float = 25.0,
        ttl_seconds: float = 12.0,
    ):
        self.max_entries = max_entries
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.ttl_seconds = ttl_seconds

        self._cache: Dict[str, CacheEntry] = {}
        self._total_bytes: int = 0
        self._hits: int = 0
        self._misses: int = 0
        self._invalidations: int = 0
        self._last_invalidation_reason: str = "None"

    @staticmethod
    def calculate_screen_hash(image: Image.Image) -> str:
        """
        Calculates a fast, robust perceptual hash (dHash + average luminance) of the screen image.
        Uses downscaling to 16x16 grayscale for sub-millisecond execution.
        """
        try:
            # 16x16 thumbnail for content fingerprinting
            thumb = image.convert("L").resize((16, 16), Image.Resampling.BILINEAR)
            raw_bytes = thumb.tobytes()
            # Combine raw md5 digest with luminance average
            md5_hash = hashlib.md5(raw_bytes).hexdigest()
            avg = sum(raw_bytes) // len(raw_bytes)
            # 64-bit difference hash
            dhash_bits = []
            for y in range(8):
                for x in range(8):
                    p1 = raw_bytes[y * 16 + x]
                    p2 = raw_bytes[y * 16 + x + 1]
                    dhash_bits.append("1" if p1 > p2 else "0")
            dhash_hex = f"{int(''.join(dhash_bits), 2):016x}"
            return f"{dhash_hex}_{md5_hash[:16]}_{avg}"
        except Exception as e:
            logger.debug(f"Error computing screen hash: {e}")
            return f"fallback_{int(time.time() * 1000)}"

    def make_cache_key(
        self,
        screen_hash: str,
        hwnd: int,
        resolution: Tuple[int, int],
    ) -> str:
        """Constructs unique cache key binding screen content to active window and display dimensions."""
        return f"{hwnd}_{resolution[0]}x{resolution[1]}_{screen_hash}"

    def get_ocr(
        self,
        screen_hash: str,
        hwnd: int,
        resolution: Tuple[int, int],
        window_title: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached OCR result if screen content and active window are demonstrably unchanged.
        """
        self._purge_expired()
        key = self.make_cache_key(screen_hash, hwnd, resolution)
        entry = self._cache.get(key)

        if not entry:
            self._misses += 1
            return None

        # Verify active window state hasn't drifted
        if entry.hwnd != hwnd or entry.resolution != resolution:
            self._invalidate_entry(key, "Window or resolution changed")
            self._misses += 1
            return None

        # Verify TTL
        if entry.is_expired(self.ttl_seconds):
            self._invalidate_entry(key, "TTL expired")
            self._misses += 1
            return None

        # Cache Hit!
        entry.touch()
        self._hits += 1
        logger.debug(f"PerceptionCache HIT for window HWND={hwnd} (hits: {entry.hit_count})")
        return entry.ocr_data

    def put_ocr(
        self,
        screen_hash: str,
        hwnd: int,
        resolution: Tuple[int, int],
        window_title: str,
        ocr_data: Dict[str, Any],
        vision_summary: Optional[str] = None,
    ) -> None:
        """Stores OCR and perception analysis into the bounded LRU cache."""
        # Estimate footprint in memory
        est_bytes = len(str(ocr_data)) + (len(vision_summary) if vision_summary else 0) + 512

        # Check memory pressure before adding
        self._check_memory_pressure()

        # Evict if capacity reached
        while len(self._cache) >= self.max_entries or (self._total_bytes + est_bytes) > self.max_memory_bytes:
            if not self._evict_oldest():
                break

        key = self.make_cache_key(screen_hash, hwnd, resolution)
        entry = CacheEntry(
            key=key,
            screen_hash=screen_hash,
            window_title=window_title,
            hwnd=hwnd,
            resolution=resolution,
            ocr_data=ocr_data,
            vision_summary=vision_summary,
            estimated_bytes=est_bytes,
        )

        # If overwriting existing key, adjust byte count
        if key in self._cache:
            self._total_bytes -= self._cache[key].estimated_bytes

        self._cache[key] = entry
        self._total_bytes += est_bytes
        logger.debug(f"PerceptionCache cached result for HWND={hwnd} ({est_bytes} bytes). Total entries: {len(self._cache)}")

    def get_vision_summary(
        self,
        screen_hash: str,
        hwnd: int,
        resolution: Tuple[int, int],
    ) -> Optional[str]:
        """Retrieves cached vision summary for unchanged screen."""
        self._purge_expired()
        key = self.make_cache_key(screen_hash, hwnd, resolution)
        entry = self._cache.get(key)
        if entry and not entry.is_expired(self.ttl_seconds):
            entry.touch()
            self._hits += 1
            return entry.vision_summary
        return None

    def update_vision_summary(
        self,
        screen_hash: str,
        hwnd: int,
        resolution: Tuple[int, int],
        summary: str,
    ) -> None:
        """Updates vision summary for existing or new entry."""
        key = self.make_cache_key(screen_hash, hwnd, resolution)
        if key in self._cache:
            self._cache[key].vision_summary = summary
            self._cache[key].touch()

    def invalidate_all(self, reason: str = "Manual Invalidation") -> int:
        """Clears all cached perception entries and forces memory release."""
        count = len(self._cache)
        self._cache.clear()
        self._total_bytes = 0
        self._invalidations += count
        self._last_invalidation_reason = reason
        gc.collect()
        logger.info(f"PerceptionCache cleared {count} entries ({reason}).")
        return count

    def invalidate_window(self, hwnd: int) -> int:
        """Invalidates all cache entries for a specific window handle."""
        to_del = [k for k, v in self._cache.items() if v.hwnd == hwnd]
        for k in to_del:
            self._invalidate_entry(k, f"Window HWND={hwnd} closed or changed")
        return len(to_del)

    def _invalidate_entry(self, key: str, reason: str) -> None:
        if key in self._cache:
            self._total_bytes -= self._cache[key].estimated_bytes
            del self._cache[key]
            self._invalidations += 1
            self._last_invalidation_reason = reason

    def _purge_expired(self) -> None:
        """Removes entries older than ttl_seconds."""
        now = time.time()
        expired = [k for k, v in self._cache.items() if (now - v.created_at) > self.ttl_seconds]
        for k in expired:
            self._invalidate_entry(k, "TTL Expiration")

    def _evict_oldest(self) -> bool:
        """Evicts least recently accessed cache entry."""
        if not self._cache:
            return False
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        self._invalidate_entry(oldest_key, "LRU Capacity Limit")
        return True

    def _check_memory_pressure(self) -> None:
        """Checks system RAM pressure (>85%); aggressively evicts cache if memory is constrained."""
        try:
            mem = psutil.virtual_memory()
            if mem.percent > 85.0:
                logger.warning(f"High system memory pressure ({mem.percent}%). Evicting perception cache.")
                self.invalidate_all(f"High Memory Pressure ({mem.percent}%)")
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        """Returns cache telemetry and memory utilization."""
        self._purge_expired()
        total_queries = self._hits + self._misses
        hit_ratio = round(self._hits / total_queries, 3) if total_queries > 0 else 0.0

        return {
            "entries_count": len(self._cache),
            "max_entries": self.max_entries,
            "estimated_memory_kb": round(self._total_bytes / 1024, 2),
            "max_memory_mb": round(self.max_memory_bytes / (1024 * 1024), 2),
            "hit_count": self._hits,
            "miss_count": self._misses,
            "total_queries": total_queries,
            "hit_ratio": hit_ratio,
            "invalidations_count": self._invalidations,
            "last_invalidation_reason": self._last_invalidation_reason,
            "ttl_seconds": self.ttl_seconds,
        }


# Global perception cache instance
perception_cache = PerceptionCache()
