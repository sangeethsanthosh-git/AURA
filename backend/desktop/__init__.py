"""AURA Desktop Automation Package."""

from backend.desktop.mouse_controller import mouse_controller, MouseController
from backend.desktop.keyboard_controller import keyboard_controller, KeyboardController
from backend.desktop.window_manager import window_manager, WindowManager
from backend.desktop.desktop_perception import desktop_perception, DesktopPerception
from backend.desktop.browser_controller import browser_controller, BrowserController
from backend.desktop.media_controller import media_controller, MediaController
from backend.desktop.file_explorer_controller import file_explorer_controller, FileExplorerController
from backend.desktop.desktop_controller import desktop_controller, DesktopController

__all__ = [
    "mouse_controller",
    "MouseController",
    "keyboard_controller",
    "KeyboardController",
    "window_manager",
    "WindowManager",
    "desktop_perception",
    "DesktopPerception",
    "browser_controller",
    "BrowserController",
    "media_controller",
    "MediaController",
    "file_explorer_controller",
    "FileExplorerController",
    "desktop_controller",
    "DesktopController",
]
