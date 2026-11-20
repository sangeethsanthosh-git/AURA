"""
Vision Service (Phase 8: Resource-Efficient Screen Vision & Desktop Awareness)
Provides memory-efficient screen capture, perceptual caching, Windows Media OCR routing,
bounded temporary storage, and automatic GPU VRAM model release.
"""

import base64
import ctypes
from ctypes import wintypes
import io
import logging
import os
import time
import atexit
import gc
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Set, Generator
import httpx
from PIL import Image

from backend.services.perception_cache import perception_cache
from backend.services.ocr_service import ocr_service
from backend.services.resource_monitor import resource_monitor

logger = logging.getLogger(__name__)

_DEFAULT_DESKTOP_HANDLE = None

user32 = ctypes.windll.user32
user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenDesktopW.restype = wintypes.HANDLE
user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
user32.SetThreadDesktop.restype = wintypes.BOOL


def ensure_interactive_desktop():
    """Ensure calling thread is attached to the interactive desktop for BitBlt / capture."""
    global _DEFAULT_DESKTOP_HANDLE
    try:
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if not hdesk:
            hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            _DEFAULT_DESKTOP_HANDLE = hdesk
            user32.SetThreadDesktop(hdesk)
            return hdesk
    except Exception as e:
        logger.debug(f"Could not bind thread to interactive desktop: {e}")
    return None


def get_active_window_title() -> str:
    """Retrieve the title of the current active foreground window using Win32 API."""
    try:
        ensure_interactive_desktop()
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "Desktop"
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value.strip()
            return title if title else "Desktop"
        return "Desktop"
    except Exception as e:
        logger.debug(f"Could not retrieve active window title: {e}")
        return "Desktop"


def get_active_window_hwnd() -> int:
    """Retrieve the HWND of the active foreground window."""
    try:
        return int(ctypes.windll.user32.GetForegroundWindow() or 0)
    except Exception:
        return 0


class VisionService:
    """
    Provides memory-conscious, zero-leak screen capture and local desktop analysis.
    Supports pure in-memory workflows, temporary screenshot lifecycle management,
    and automatic GPU model unloading.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or "backend/data/temp_screenshots").resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.latest_capture_path: Optional[Path] = None
        self._temp_files: Set[Path] = set()
        self.max_retained_screenshots: int = 5

        # Register cleanup on process exit
        atexit.register(self._cleanup_all_temp_on_exit)

    def grab_screen_image(self) -> Tuple[Image.Image, float]:
        """
        Captures primary monitor directly into an in-memory PIL Image.
        Returns (Image, elapsed_ms). Does NOT write any files to disk.
        """
        import mss

        ensure_interactive_desktop()
        t0 = time.perf_counter()
        img = None
        try:
            with mss.MSS() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                del sct_img
        except Exception as e:
            logger.warning(f"Native MSS grab failed ({e}, LastError={ctypes.GetLastError()}). Generating fallback canvas...")
            img = Image.new("RGB", (1280, 720), color=(26, 27, 38))

        elapsed_ms = (time.perf_counter() - t0) * 1000
        resource_monitor.record_capture_time(elapsed_ms)
        return img, elapsed_ms

    def capture_screen(
        self,
        save_filename: str = "latest_screen.png",
        save_to_disk: bool = True,
    ) -> Dict[str, Any]:
        """
        Capture primary display, create lightweight thumbnail, and manage temporary file retention.
        """
        window_title = get_active_window_title()
        img, elapsed_ms = self.grab_screen_image()

        save_path = self.storage_dir / save_filename
        if save_to_disk:
            img.save(save_path, format="PNG")
            self.latest_capture_path = save_path
            self._temp_files.add(save_path)
            self._prune_excess_screenshots()

        # Generate lightweight JPEG thumbnail for UI card (640px wide max, 70% quality)
        thumb = img.copy()
        thumb.thumbnail((640, 360), Image.Resampling.LANCZOS)
        thumb_buffer = io.BytesIO()
        thumb.save(thumb_buffer, format="JPEG", quality=70)
        thumb_base64 = f"data:image/jpeg;base64,{base64.b64encode(thumb_buffer.getvalue()).decode('utf-8')}"
        thumb_buffer.close()
        del thumb

        width, height = img.width, img.height
        del img

        logger.debug(f"Screen capture completed in {elapsed_ms:.1f}ms: {save_path} ({width}x{height})")

        return {
            "status": "success",
            "image_path": str(save_path) if save_to_disk else "",
            "thumbnail": thumb_base64,
            "width": width,
            "height": height,
            "window_title": window_title,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_ms": round(elapsed_ms, 1),
        }

    @contextmanager
    def temporary_screenshot(self) -> Generator[Tuple[Image.Image, Path], None, None]:
        """
        Context manager that creates a temporary on-disk screenshot and
        GUARANTEES immediate deletion upon block exit, even if an exception occurs.
        """
        img, _ = self.grab_screen_image()
        temp_name = f"temp_aura_{int(time.time() * 1000)}_{os.getpid()}.png"
        temp_path = self.storage_dir / temp_name
        try:
            img.save(temp_path, format="PNG")
            self._temp_files.add(temp_path)
            yield img, temp_path
        finally:
            try:
                if temp_path.exists():
                    temp_path.unlink()
                    self._temp_files.discard(temp_path)
            except Exception as e:
                logger.debug(f"Error unlinking temporary screenshot: {e}")
            try:
                img.close()
                del img
            except Exception:
                pass

    def get_latest_screenshot_path(self) -> Optional[str]:
        """Return file path of the most recent screenshot."""
        if self.latest_capture_path and self.latest_capture_path.exists():
            return str(self.latest_capture_path)
        default_p = self.storage_dir / "latest_screen.png"
        if default_p.exists():
            return str(default_p)
        return None

    def _prune_excess_screenshots(self) -> None:
        """Enforces bounded disk retention: keeps at most max_retained_screenshots in storage_dir."""
        try:
            png_files = sorted(
                self.storage_dir.glob("*.png"),
                key=lambda p: p.stat().st_mtime,
            )
            while len(png_files) > self.max_retained_screenshots:
                oldest = png_files.pop(0)
                try:
                    oldest.unlink()
                    self._temp_files.discard(oldest)
                    logger.debug(f"Pruned older screenshot: {oldest.name}")
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Error pruning excess screenshots: {e}")

    def cleanup_temp_files(self, max_age_seconds: float = 60.0) -> int:
        """
        Safely deletes temporary screenshot files older than max_age_seconds.
        Strictly sandboxed to self.storage_dir; never deletes outside files.
        """
        now = time.time()
        deleted = 0
        if not self.storage_dir.exists():
            return 0

        for f in list(self.storage_dir.glob("*")):
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg"):
                try:
                    if (now - f.stat().st_mtime) >= max_age_seconds or f.name.startswith("temp_aura_"):
                        f.unlink()
                        self._temp_files.discard(f)
                        deleted += 1
                except Exception:
                    pass

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} temporary screenshot files.")
        return deleted

    def _cleanup_all_temp_on_exit(self) -> None:
        """Atexit handler to ensure no temporary screenshots remain on disk."""
        for p in list(self._temp_files):
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        self._temp_files.clear()

    @staticmethod
    def unload_vision_models(ollama_url: str = "http://127.0.0.1:11434") -> Dict[str, Any]:
        """
        Evicts loaded models from GPU VRAM by setting Ollama keep_alive to 0
        and calling torch.cuda.empty_cache().
        """
        unloaded = []
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{ollama_url}/api/ps")
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", []) if m.get("name")]
                    for m in models:
                        client.post(f"{ollama_url}/api/generate", json={"model": m, "keep_alive": 0})
                        unloaded.append(m)
        except Exception as e:
            logger.debug(f"Ollama unload call note: {e}")

        # PyTorch CUDA empty cache
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception:
            pass

        gc.collect()
        logger.info(f"Unloaded {len(unloaded)} models from VRAM: {unloaded}")
        return {
            "success": True,
            "unloaded_models": unloaded,
            "count": len(unloaded),
        }

    async def analyze_screen(
        self,
        image_path: str,
        query: str = "What is on my screen?",
        window_title: str = "Desktop",
        ollama_url: str = "http://127.0.0.1:11434",
    ) -> str:
        """
        Resource-efficient screen analysis:
        1. Checks PerceptionCache for unchanged screen content.
        2. Routes text-reading queries to lightweight Windows Media OCR (< 40ms, 0 VRAM).
        3. Invokes multimodal LLMs only for complex visual scene queries with keep_alive='1m'.
        """
        hwnd = get_active_window_hwnd()

        # Load image into memory for hashing and analysis
        img = None
        try:
            if image_path and Path(image_path).exists():
                img = Image.open(image_path)
            else:
                img, _ = self.grab_screen_image()
        except Exception as e:
            return f"Unable to read screenshot for analysis: {e}"

        screen_hash = perception_cache.calculate_screen_hash(img)
        resolution = (img.width, img.height)

        # 1. Perception Cache Check: If identical screen was already summarized
        cached_summary = perception_cache.get_vision_summary(screen_hash, hwnd, resolution)
        if cached_summary:
            logger.info("Returning cached screen vision summary (screen unchanged).")
            img.close()
            return cached_summary

        # 2. Text Reading Query Optimization (prefer zero-VRAM Windows Media OCR)
        q_lower = query.lower()
        is_text_reading = any(
            t in q_lower
            for t in [
                "read text", "read the text", "what is written", "what text",
                "read screen", "what does it say", "read words", "find text"
            ]
        )

        if is_text_reading and ocr_service.is_available:
            ocr_res = ocr_service.recognize_image(img, hwnd=hwnd, window_title=window_title, use_cache=True)
            full_txt = ocr_res.get("full_text", "")
            img.close()
            if full_txt:
                preview = full_txt[:300] + ("..." if len(full_txt) > 300 else "")
                ans = f"On your screen in '{window_title}', I read the following text:\n\n{preview}"
                perception_cache.update_vision_summary(screen_hash, hwnd, resolution, ans)
                return ans
            else:
                return f"No readable text was detected on your active screen in '{window_title}'."

        # 3. Multimodal Vision LLM check
        # Read image to base64
        buf = io.BytesIO()
        # Scale down large screens for vision model inference to save VRAM and latency
        inference_img = img
        if img.width > 1280 or img.height > 720:
            inference_img = img.copy()
            inference_img.thumbnail((1280, 720), Image.Resampling.BILINEAR)

        inference_img.save(buf, format="JPEG", quality=80)
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        buf.close()
        if inference_img != img:
            del inference_img
        img.close()

        vision_model = None
        fallback_model = "llama3.2:3b"

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{ollama_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name", "") for m in res.json().get("models", [])]
                    for candidate in ["moondream", "llava", "llama3.2-vision", "qwen2-vl"]:
                        for m in models:
                            if candidate in m.lower():
                                vision_model = m
                                break
                        if vision_model:
                            break
        except Exception:
            pass

        # If vision model is installed, perform vision inference with bounded keep_alive
        if vision_model:
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    payload = {
                        "model": vision_model,
                        "prompt": f"{query}\nActive window: {window_title}",
                        "images": [img_b64],
                        "stream": False,
                        "keep_alive": "1m",  # Evict from VRAM 1 minute after last inference
                    }
                    resp = await client.post(f"{ollama_url}/api/generate", json=payload)
                    if resp.status_code == 200:
                        analysis = resp.json().get("response", "").strip()
                        if analysis:
                            perception_cache.update_vision_summary(screen_hash, hwnd, resolution, analysis)
                            return analysis
            except Exception as e:
                logger.warning(f"Vision model inference error: {e}")

        # Fallback contextual desktop description
        prompt = (
            f"You are AURA, an AI desktop assistant. The user just asked you to inspect their screen.\n"
            f"Active Foreground Window: \"{window_title}\"\n"
            f"User Question: \"{query}\"\n\n"
            f"Respond concisely in 1 to 2 conversational sentences explaining that you captured their screen "
            f"with active window '{window_title}', and provide helpful advice based on their query."
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "model": fallback_model,
                    "prompt": prompt,
                    "stream": False,
                }
                resp = await client.post(f"{ollama_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    summary = resp.json().get("response", "").strip()
                    perception_cache.update_vision_summary(screen_hash, hwnd, resolution, summary)
                    return summary
        except Exception:
            pass

        summary = f"I captured your desktop screen. You are currently viewing '{window_title}'."
        perception_cache.update_vision_summary(screen_hash, hwnd, resolution, summary)
        return summary

    def analyze_screen_sync(
        self,
        image_path: str,
        query: str = "What is on my screen?",
        window_title: str = "Desktop",
    ) -> str:
        """Synchronous wrapper for analyze_screen."""
        import asyncio
        import concurrent.futures

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(lambda: asyncio.run(self.analyze_screen(image_path, query, window_title)))
                    return fut.result(timeout=12.0)
            else:
                return loop.run_until_complete(self.analyze_screen(image_path, query, window_title))
        except Exception as e:
            logger.warning(f"Vision analysis fallback due to sync runner error: {e}")
            return f"I captured your desktop screen. You are currently viewing '{window_title}'."
