from __future__ import annotations

import ctypes
import json
import os
import platform
import socket
import subprocess
import threading
import asyncio
import base64
from dataclasses import asdict, is_dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from backend.electron_bridge import command as bridge_command
from ui.controller.aura_controller import AuraController

try:
    import webview
except Exception:  # pragma: no cover - fallback only
    webview = None

try:
    import win32con
    import win32gui
except Exception:  # pragma: no cover - fallback only
    win32con = None
    win32gui = None

try:
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
    from winsdk.windows.storage.streams import DataReader
except Exception:  # pragma: no cover
    GlobalSystemMediaTransportControlsSessionManager = None
    DataReader = None

ROOT = Path(__file__).resolve().parent
USER_DATA_DIR = Path(os.getenv("APPDATA") or Path.home()) / "AURA ASUS"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = USER_DATA_DIR / "provider-keys.json"
APP_SETTINGS_FILE = USER_DATA_DIR / "app-settings.json"


def resource_path(relative: str) -> Path:
    base = Path(getattr(__import__("sys"), "_MEIPASS", ROOT))
    return base / relative


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "value"):
        return value.value
    return str(value)


def _write_json(handler: SimpleHTTPRequestHandler, status: int, payload: Any) -> None:
    data = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


def _system_info() -> dict[str, Any]:
    memory_gb = 8
    if platform.system() == "Windows":
        try:
            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memoryLoad", ctypes.c_ulong),
                    ("totalPhys", ctypes.c_ulonglong),
                    ("availPhys", ctypes.c_ulonglong),
                    ("totalPageFile", ctypes.c_ulonglong),
                    ("availPageFile", ctypes.c_ulonglong),
                    ("totalVirtual", ctypes.c_ulonglong),
                    ("availVirtual", ctypes.c_ulonglong),
                    ("availExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            memory_gb = round(status.totalPhys / 1024 / 1024 / 1024)
        except Exception:
            memory_gb = 8
    return {
        "platform": platform.system().lower(),
        "arch": platform.machine().lower(),
        "totalMemoryGb": max(memory_gb, 4),
        "cpuCount": os.cpu_count() or 4,
        "hostname": platform.node() or "This PC",
        "electron": "none",
    }


def _open_path(file_path: str) -> None:
    if not file_path:
        return
    try:
        os.startfile(file_path)  # type: ignore[attr-defined]
    except Exception:
        return


def _hidden_creationflags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)


def _install_ollama_silently() -> dict[str, Any]:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        "irm https://ollama.com/install.ps1 | iex",
    ]
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=_hidden_creationflags(),
        )
        return {"ok": True, "message": "Ollama installer started in the background."}
    except Exception as exc:
        return {"ok": False, "message": f"Could not start Ollama installer: {exc}"}


def _send_media_key(vk_code: int) -> bool:
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, 0, 0)
        user32.keybd_event(vk_code, 0, 2, 0)
        return True
    except Exception:
        return False


def _media_window_title() -> tuple[str, str]:
    if win32gui is None or win32con is None:
        return ""

    titles: list[tuple[str, str]] = []

    def enum_handler(hwnd: int, _extra: Any) -> None:
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return
            _, pid = win32gui.GetWindowThreadProcessId(hwnd)
            if not pid:
                return
            text = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            if text and cls:
                lower_text = text.lower()
                lower_cls = cls.lower()
                media_apps = {"spotify": "Spotify", "chrome": "Chrome", "msedge": "Microsoft Edge", "firefox": "Firefox"}
                for marker, app_name in media_apps.items():
                    if marker in lower_text or marker in lower_cls:
                        titles.append((text, app_name))
                        break
        except Exception:
            return

    try:
        win32gui.EnumWindows(enum_handler, None)
    except Exception:
        return "", ""
    if not titles:
        return "", ""
    # Prefer a browser window whose title contains actual media metadata.
    generic = {"new tab", "google chrome", "chrome", "microsoft edge", "firefox", "spotify"}
    media_titles = [item for item in titles if item[0].strip().lower() not in generic]
    return (media_titles or titles)[0]


def _spotify_state() -> dict[str, Any]:
    system_media = _windows_media_state()
    if system_media:
        return system_media
    title, app_name = _media_window_title()
    if not title:
        return {
            "ok": True,
            "active": False,
            "isPlaying": False,
            "title": "Windows Media",
            "artist": "",
            "album": "",
            "device": "Windows media session",
            "message": "Play audio in Spotify, Chrome, Edge, or another media app to show now playing.",
        }
    parts = [part.strip() for part in title.replace(" | YouTube", "").split(" - ") if part.strip()]
    track_title = parts[0] if parts else title
    artist = parts[1] if len(parts) > 1 else ""
    return {
        "ok": True,
        "active": True,
        "isPlaying": True,
        "title": track_title,
        "artist": artist,
        "album": "",
        "device": app_name or "Windows Media",
        "message": "Windows media playback is active.",
        "progressMs": 0,
        "durationMs": 0,
        "imageUrl": "",
    }


def _windows_media_state() -> dict[str, Any] | None:
    """Read Windows media metadata shared by Spotify, browsers, and local players."""
    if GlobalSystemMediaTransportControlsSessionManager is None or platform.system() != "Windows":
        return None

    async def read_session() -> dict[str, Any] | None:
        try:
            manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
            for session in manager.get_sessions():
                playback = session.get_playback_info()
                status = str(getattr(playback, "playback_status", "")).lower()
                if "closed" in status or "stopped" in status:
                    continue
                props = await session.try_get_media_properties_async()
                title = str(getattr(props, "title", "") or "").strip()
                if not title:
                    continue
                timeline = session.get_timeline_properties()
                position = max(0, int(timeline.position.total_seconds() * 1000))
                duration = max(0, int((timeline.end_time - timeline.start_time).total_seconds() * 1000))
                image_url = ""
                if DataReader is not None and getattr(props, "thumbnail", None) is not None:
                    try:
                        stream = await props.thumbnail.open_read_async()
                        size = min(int(stream.size), 2 * 1024 * 1024)
                        if size > 0:
                            reader = DataReader(stream.get_input_stream_at(0))
                            await reader.load_async(size)
                            data = bytearray(size)
                            reader.read_bytes(data)
                            content_type = str(getattr(stream, "content_type", "image/jpeg") or "image/jpeg")
                            image_url = f"data:{content_type};base64,{base64.b64encode(data).decode('ascii')}"
                    except Exception:
                        image_url = ""
                return {
                    "ok": True,
                    "active": True,
                    "isPlaying": "playing" in status and "paused" not in status and "stopped" not in status,
                    "title": title,
                    "artist": str(getattr(props, "artist", "") or "").strip(),
                    "album": str(getattr(props, "album_title", "") or "").strip(),
                    "device": "Windows Media",
                    "message": "Windows media session is active.",
                    "progressMs": position,
                    "durationMs": duration,
                    "imageUrl": image_url,
                }
        except Exception:
            return None
        return None

    try:
        return asyncio.run(read_session())
    except Exception:
        return None


def _select_files(allow_multiple: bool = False, audio_only: bool = False) -> list[dict[str, str]]:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        if audio_only:
            options = {"filetypes": [("Audio Files", "*.mp3 *.wav *.m4a *.flac"), ("All Files", "*.*")]}
        else:
            options = {}
        if allow_multiple:
            paths = filedialog.askopenfilenames(**options)
        else:
            path = filedialog.askopenfilename(**options)
            paths = (path,) if path else ()
        result = []
        for file_path in paths:
            if not file_path:
                continue
            path = Path(file_path)
            result.append({"id": path.stem, "title": path.name, "filePath": str(path), "url": path.as_uri()})
        return result
    finally:
        root.destroy()


class DesktopHandler(SimpleHTTPRequestHandler):
    controller: AuraController
    dist_dir: Path

    def __init__(self, *args, directory: str | None = None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/desktop/system-info":
            return _write_json(self, 200, _system_info())
        if path == "/api/desktop/settings/provider-keys":
            return _write_json(self, 200, self._load_provider_keys())
        if path == "/api/desktop/settings/app-settings":
            return _write_json(self, 200, self._load_app_settings())
        if path == "/api/desktop/health":
            return _write_json(self, 200, {"ok": True})
        if not Path(self.translate_path(path)).exists() and not path.startswith("/assets/") and not path.startswith("/public/"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        payload = self._json_body()

        if path == "/api/desktop/request":
            command = str(payload.get("command", "")) if isinstance(payload, dict) else ""
            result = bridge_command(self.controller, command, payload.get("payload") if isinstance(payload, dict) else None)
            return _write_json(self, 200, result)

        if path == "/api/desktop/window/minimize":
            return _write_json(self, 200, {"ok": True})
        if path == "/api/desktop/window/maximize":
            return _write_json(self, 200, {"ok": True})
        if path == "/api/desktop/window/close":
            self.server.shutdown()
            return _write_json(self, 200, {"ok": True})

        if path == "/api/desktop/media/select-file":
            return _write_json(self, 200, {"path": self._select_file()})
        if path == "/api/desktop/media/open-path":
            _open_path(str(payload.get("filePath", "")) if isinstance(payload, dict) else "")
            return _write_json(self, 200, {"ok": True})
        if path == "/api/desktop/media/select-audio-files":
            return _write_json(self, 200, _select_files(allow_multiple=True, audio_only=True))
        if path == "/api/desktop/media/open-external":
            url = str(payload.get("url", "")) if isinstance(payload, dict) else ""
            if url:
                try:
                    os.startfile(url)  # type: ignore[attr-defined]
                except Exception:
                    pass
            return _write_json(self, 200, {"ok": True})

        if path == "/api/desktop/settings/save-provider-keys":
            keys = payload if isinstance(payload, list) else []
            SETTINGS_FILE.write_text(json.dumps(keys, ensure_ascii=False, indent=2), encoding="utf-8")
            return _write_json(self, 200, {"ok": True})

        if path == "/api/desktop/settings/save-app-settings":
            settings = payload if isinstance(payload, dict) else {}
            current = self._load_app_settings()
            current.update(settings)
            APP_SETTINGS_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
            return _write_json(self, 200, {"ok": True})

        if path == "/api/desktop/companion/show" or path == "/api/desktop/companion/hide":
            return _write_json(self, 200, {"ok": True})
        if path == "/api/desktop/runtime/install-ollama":
            return _write_json(self, 200, _install_ollama_silently())
        if path == "/api/desktop/spotify/request":
            action = str(payload.get("action", "")) if isinstance(payload, dict) else ""
            key_map = {
                "playpause": 0xB3,  # VK_MEDIA_PLAY_PAUSE
                "next": 0xB0,       # VK_MEDIA_NEXT_TRACK
                "previous": 0xB1,   # VK_MEDIA_PREV_TRACK
            }
            if action in key_map:
                sent = _send_media_key(key_map[action])
                return _write_json(self, 200, {"ok": sent, "message": "Sent media key." if sent else "Could not send media key."})
            if action == "current":
                return _write_json(self, 200, _spotify_state())
            if action == "connect" or action == "disconnect":
                return _write_json(self, 200, {"ok": True, "message": "Spotify uses system media keys in the desktop app."})
            if action == "search":
                query = str(payload.get("payload", {}).get("query", "")) if isinstance(payload, dict) else ""
                return _write_json(self, 200, {"ok": False, "needsAuth": True, "message": f"Search opens Spotify manually for: {query}", "results": []})
            if action == "play":
                sent = _send_media_key(0xB3)
                return _write_json(self, 200, {"ok": sent, "message": "Sent play command." if sent else "Could not send play command."})
            if action == "pause" or action == "stop":
                sent = _send_media_key(0xB3)
                return _write_json(self, 200, {"ok": sent, "message": "Sent pause command." if sent else "Could not send pause command."})
            return _write_json(self, 200, {"ok": False, "message": f"Spotify bridge is unavailable for action {action}."})
        if path == "/api/desktop/youtube/search":
            return _write_json(self, 200, {"ok": False, "results": [], "message": "YouTube bridge is unavailable in the shell."})
        if path == "/api/desktop/youtube/open-mini":
            video_id = str(payload.get("videoId", "")) if isinstance(payload, dict) else ""
            query = str(payload.get("query", "")) if isinstance(payload, dict) else ""
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id else f"https://www.youtube.com/results?search_query={query}"
            try:
                os.startfile(url)  # type: ignore[attr-defined]
            except Exception:
                pass
            return _write_json(self, 200, {"ok": True})

        _write_json(self, 404, {"ok": False, "message": "Not found."})

    def _json_body(self) -> Any:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def _load_provider_keys(self) -> list[dict[str, Any]]:
        if not SETTINGS_FILE.exists():
            return []
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _load_app_settings(self) -> dict[str, Any]:
        if not APP_SETTINGS_FILE.exists():
            return {}
        try:
            value = json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _select_file() -> str | None:
        files = _select_files(allow_multiple=False, audio_only=False)
        return files[0]["filePath"] if files else None


def make_handler(controller: AuraController, dist_dir: Path):
    class BoundDesktopHandler(DesktopHandler):
        pass

    BoundDesktopHandler.controller = controller
    BoundDesktopHandler.dist_dir = dist_dir
    return partial(BoundDesktopHandler, directory=str(dist_dir))


def start_server(dist_dir: Path) -> tuple[ThreadingHTTPServer, int]:
    controller = AuraController()
    handler = make_handler(controller, dist_dir)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1]


def launch_window(url: str) -> None:
    if webview is None:
        raise RuntimeError("pywebview is not available. Install it to run AURA as a native app window.")
    webview.create_window(
        "AURA ASUS",
        url,
        width=1400,
        height=900,
        resizable=True,
        background_color="#ffffff",
        text_select=False,
        zoomable=False,
        confirm_close=False,
    )
    webview.start(debug=False, http_server=False)


def main() -> int:
    dist_dir = resource_path("dist")
    if not dist_dir.exists():
        raise FileNotFoundError(f"React build not found: {dist_dir}")

    server, port = start_server(dist_dir)
    try:
        launch_window(f"http://127.0.0.1:{port}/")
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
