"""Read-only active window inspection for AURA EYES."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ActiveWindowInfo:
    success: bool
    title: str = ""
    process_name: str = ""
    executable_path: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def application(self) -> str | None:
        if self.process_name:
            stem = Path(self.process_name).stem
            aliases = {
                "applicationframehost": self.title,
                "calculatorapp": "Calculator",
                "chrome": "Chrome",
                "code": "Visual Studio Code",
                "spotify": "Spotify",
                "notepad": "Notepad",
                "msedge": "Microsoft Edge",
            }
            return aliases.get(stem.lower(), " ".join(part.capitalize() for part in stem.replace("_", " ").split()))
        return self.title or None

    def safe_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "title": self.title,
            "process_name": self.process_name,
            "executable_path": self.executable_path,
            "application": self.application,
            "error": self.error,
            "metadata": self.metadata,
        }


class ActiveWindowInspector:
    """Inspects the foreground window without capturing screen contents."""

    def get_active_window(self) -> ActiveWindowInfo:
        try:
            import ctypes
            from ctypes import wintypes
        except Exception as exc:
            return ActiveWindowInfo(False, error=f"Active window inspection unavailable: {exc}")

        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
        except AttributeError as exc:
            return ActiveWindowInfo(False, error=f"Windows foreground-window APIs unavailable: {exc}")

        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return ActiveWindowInfo(False, error="No foreground window detected.")

            length = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value

            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            process_name = ""
            executable_path = ""
            process = kernel32.OpenProcess(0x0410, False, pid.value)
            if process:
                exe_buffer = ctypes.create_unicode_buffer(1024)
                if psapi.GetModuleFileNameExW(process, None, exe_buffer, len(exe_buffer)):
                    executable_path = exe_buffer.value
                    process_name = Path(executable_path).name
                kernel32.CloseHandle(process)

            return ActiveWindowInfo(
                True,
                title=title,
                process_name=process_name,
                executable_path=executable_path,
                metadata={"hwnd": int(hwnd), "pid": int(pid.value)},
            )
        except Exception as exc:
            return ActiveWindowInfo(False, error=f"Active window inspection failed: {exc}")
