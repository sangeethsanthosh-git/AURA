"""
AURA Resource Monitor
Aggregates real-time RAM, GPU VRAM, CPU, screenshot latency, OCR performance,
perception cache footprint, temporary storage usage, and model resident states.
"""

from typing import Dict, Any, List, Optional
import os
import time
import logging
from pathlib import Path
import psutil

from backend.services.perception_cache import perception_cache
from backend.services.ocr_service import ocr_service

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Provides unified system and perception resource telemetry."""

    def __init__(self, temp_dir: Optional[str] = None):
        self._process = psutil.Process()
        self.temp_dir = Path(temp_dir or "backend/data/temp_screenshots").resolve()
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self._last_capture_ms: float = 0.0
        self._total_captures: int = 0
        self._total_capture_ms: float = 0.0

    def record_capture_time(self, ms: float) -> None:
        """Records latency of screen capture operation."""
        self._last_capture_ms = ms
        self._total_captures += 1
        self._total_capture_ms += ms

    def get_gpu_metrics(self) -> Dict[str, Any]:
        """Inspects NVIDIA CUDA / PyTorch GPU VRAM metrics if available."""
        # PyTorch is large and the application uses CPU Whisper/Ollama. Avoid
        # importing it just to report GPU metrics when no GPU metrics are used.
        import sys
        if "torch" not in sys.modules:
            return self._empty_gpu_metrics()
        try:
            import torch
            if torch.cuda.is_available():
                device_idx = 0
                props = torch.cuda.get_device_properties(device_idx)
                allocated_bytes = torch.cuda.memory_allocated(device_idx)
                reserved_bytes = torch.cuda.memory_reserved(device_idx)
                total_bytes = props.total_memory

                allocated_mb = round(allocated_bytes / (1024 * 1024), 2)
                reserved_mb = round(reserved_bytes / (1024 * 1024), 2)
                total_mb = round(total_bytes / (1024 * 1024), 2)
                free_mb = round(total_mb - reserved_mb, 2)
                vram_pct = round((reserved_mb / total_mb) * 100, 1) if total_mb > 0 else 0.0

                return {
                    "available": True,
                    "device_name": props.name,
                    "allocated_mb": allocated_mb,
                    "reserved_mb": reserved_mb,
                    "total_mb": total_mb,
                    "free_mb": free_mb,
                    "vram_percent": vram_pct,
                }
        except Exception as e:
            logger.debug(f"GPU metrics probe note: {e}")

        return self._empty_gpu_metrics()

    @staticmethod
    def _empty_gpu_metrics() -> Dict[str, Any]:
        return {
            "available": False,
            "device_name": "None / Integrated",
            "allocated_mb": 0.0,
            "reserved_mb": 0.0,
            "total_mb": 0.0,
            "free_mb": 0.0,
            "vram_percent": 0.0,
        }

    def get_temporary_storage_metrics(self) -> Dict[str, Any]:
        """Calculates temporary screenshot file count and storage footprint."""
        total_bytes = 0
        file_count = 0

        if self.temp_dir.exists():
            try:
                for entry in os.scandir(self.temp_dir):
                    if entry.is_file():
                        file_count += 1
                        total_bytes += entry.stat().st_size
            except Exception as e:
                logger.debug(f"Error scanning temp directory: {e}")

        return {
            "temp_directory": str(self.temp_dir),
            "file_count": file_count,
            "size_kb": round(total_bytes / 1024, 2),
            "size_mb": round(total_bytes / (1024 * 1024), 3),
        }

    def get_model_states(self, ollama_url: str = "http://127.0.0.1:11434") -> Dict[str, Any]:
        """Queries Ollama for active models currently resident in VRAM/RAM."""
        import urllib.request
        import json

        loaded: List[str] = []
        try:
            req = urllib.request.Request(f"{ollama_url}/api/ps", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = data.get("models", [])
                    loaded = [m.get("name", "") for m in models if m.get("name")]
        except Exception:
            pass

        return {
            "loaded_models": loaded,
            "count": len(loaded),
            "has_vision_model_loaded": any(
                any(v in m.lower() for v in ["moondream", "llava", "vision", "qwen2-vl"])
                for m in loaded
            ),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive resource telemetry."""
        # 1. Memory (Process + System)
        try:
            mem_info = self._process.memory_info()
            proc_ram_mb = round(mem_info.rss / (1024 * 1024), 2)
            sys_mem = psutil.virtual_memory()
            sys_ram_used_mb = round((sys_mem.total - sys_mem.available) / (1024 * 1024), 2)
            sys_ram_total_mb = round(sys_mem.total / (1024 * 1024), 2)
            sys_ram_pct = sys_mem.percent
        except Exception:
            proc_ram_mb = 0.0
            sys_ram_used_mb = 0.0
            sys_ram_total_mb = 0.0
            sys_ram_pct = 0.0

        # 2. CPU
        try:
            proc_cpu = self._process.cpu_percent(interval=None)
            sys_cpu = psutil.cpu_percent(interval=None)
        except Exception:
            proc_cpu = 0.0
            sys_cpu = 0.0

        # 3. GPU VRAM
        gpu_data = self.get_gpu_metrics()

        # 4. Latencies
        avg_cap_ms = (
            round(self._total_capture_ms / self._total_captures, 2)
            if self._total_captures > 0
            else 0.0
        )
        ocr_metrics = ocr_service.get_metrics()

        # 5. Perception Cache
        cache_stats = perception_cache.get_stats()

        # 6. Temp Storage
        temp_stats = self.get_temporary_storage_metrics()

        # 7. Model States
        model_stats = self.get_model_states()

        return {
            "timestamp": time.time(),
            "ram": {
                "process_mb": proc_ram_mb,
                "system_used_mb": sys_ram_used_mb,
                "system_total_mb": sys_ram_total_mb,
                "system_percent": sys_ram_pct,
            },
            "cpu": {
                "process_percent": proc_cpu,
                "system_percent": sys_cpu,
            },
            "gpu": gpu_data,
            "latency": {
                "screenshot_capture_last_ms": round(self._last_capture_ms, 2),
                "screenshot_capture_avg_ms": avg_cap_ms,
                "ocr_last_ms": ocr_metrics["last_duration_ms"],
                "ocr_avg_ms": ocr_metrics["average_duration_ms"],
            },
            "ocr": ocr_metrics,
            "cache": cache_stats,
            "temporary_storage": temp_stats,
            "models": model_stats,
        }


# Global resource monitor instance
resource_monitor = ResourceMonitor()
