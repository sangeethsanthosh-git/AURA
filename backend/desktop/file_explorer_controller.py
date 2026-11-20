"""
AURA File Explorer Controller
Provides native Windows File Explorer automation: opening folders, navigating directory trees,
searching files, folder creation, clipboard copying/moving, and safety checkpoints.
"""

from typing import Dict, Any, Optional
import os
import subprocess
import time
from pathlib import Path
import logging
from backend.desktop.keyboard_controller import keyboard_controller
from backend.desktop.window_manager import window_manager
from backend.security.filesystem_guard import filesystem_guard

logger = logging.getLogger(__name__)


class FileExplorerController:
    """Controls Windows File Explorer and directory operations."""

    COMMON_FOLDERS = {
        "downloads": lambda: Path(os.environ["USERPROFILE"]) / "Downloads",
        "documents": lambda: Path(os.environ["USERPROFILE"]) / "Documents",
        "desktop": lambda: Path(os.environ["USERPROFILE"]) / "Desktop",
        "pictures": lambda: Path(os.environ["USERPROFILE"]) / "Pictures",
        "videos": lambda: Path(os.environ["USERPROFILE"]) / "Videos",
        "music": lambda: Path(os.environ["USERPROFILE"]) / "Music",
        "project": lambda: Path(__file__).resolve().parent.parent.parent,
    }

    def open_folder(self, folder_query: str) -> Dict[str, Any]:
        """
        Validates target directory with FilesystemGuard and opens it in Windows File Explorer.
        """
        q = folder_query.strip().lower()

        # Resolve common folder aliases
        target_path: Optional[Path] = None
        for key, resolver in self.COMMON_FOLDERS.items():
            if key in q:
                target_path = resolver()
                break

        if not target_path:
            target_path = Path(folder_query).resolve()

        # Filesystem Guard Boundary Validation
        is_valid, reason, resolved = filesystem_guard.validate_path_access(str(target_path))
        if not is_valid:
            return {"success": False, "error": f"Folder access denied by security guard: {reason}"}

        final_path = resolved or target_path
        if not final_path.exists():
            final_path.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.Popen(["explorer.exe", str(final_path)], shell=False)
            time.sleep(0.4)
            return {
                "success": True,
                "path": str(final_path),
                "folder_name": final_path.name,
                "message": f"Opened {final_path.name} in File Explorer",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def new_folder(self, name: str) -> bool:
        """Creates a new folder inside active File Explorer window (Ctrl+Shift+N)."""
        self._ensure_explorer_focus()
        keyboard_controller.hotkey("ctrl", "shift", "n")
        time.sleep(0.2)
        if name:
            keyboard_controller.type_text(name)
            time.sleep(0.05)
            keyboard_controller.press_key("enter")
        return True

    def search_in_folder(self, query: str) -> bool:
        """Triggers File Explorer search bar (Ctrl+F) and types query."""
        self._ensure_explorer_focus()
        keyboard_controller.hotkey("ctrl", "f")
        time.sleep(0.15)
        keyboard_controller.type_text(query)
        time.sleep(0.05)
        return keyboard_controller.press_key("enter")

    def go_up(self) -> bool:
        """Navigates to parent folder (Alt+Up)."""
        self._ensure_explorer_focus()
        return keyboard_controller.hotkey("alt", "up")

    def go_back(self) -> bool:
        """Navigates back (Alt+Left)."""
        self._ensure_explorer_focus()
        return keyboard_controller.hotkey("alt", "left")

    def select_all(self) -> bool:
        """Selects all items in folder (Ctrl+A)."""
        self._ensure_explorer_focus()
        return keyboard_controller.hotkey("ctrl", "a")

    def copy_selected(self) -> bool:
        """Copies selected items (Ctrl+C)."""
        self._ensure_explorer_focus()
        return keyboard_controller.hotkey("ctrl", "c")

    def paste(self) -> bool:
        """Pastes items (Ctrl+V)."""
        self._ensure_explorer_focus()
        return keyboard_controller.hotkey("ctrl", "v")

    def rename_selected(self, new_name: str) -> bool:
        """Renames selected item (F2)."""
        self._ensure_explorer_focus()
        keyboard_controller.press_key("f2")
        time.sleep(0.1)
        keyboard_controller.type_text(new_name)
        time.sleep(0.05)
        return keyboard_controller.press_key("enter")

    @staticmethod
    def _ensure_explorer_focus() -> bool:
        """Focuses active File Explorer window."""
        win = window_manager.find_window("explorer")
        if not win:
            win = window_manager.find_window("file explorer")
        if win and win.get("hwnd"):
            return window_manager.focus_window(win["hwnd"])
        return False


# Global explorer controller instance
file_explorer_controller = FileExplorerController()
