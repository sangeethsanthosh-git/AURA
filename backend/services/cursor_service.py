"""
AURA Windows Cursor Management Service
Provides safe, official Windows system-wide cursor theme configuration,
automatic scheme backup, and restoration using Win32 SystemParametersInfoW.
Does not require administrator privileges.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import winreg
import ctypes

logger = logging.getLogger(__name__)

SPI_SETCURSORS = 0x0057
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02

CURSOR_REG_PATH = r"Control Panel\Cursors"

# Registry keys representing standard Windows cursor roles
CURSOR_ROLES = [
    "Arrow",
    "Help",
    "AppStarting",
    "Wait",
    "Crosshair",
    "IBeam",
    "NWPen",
    "No",
    "SizeNS",
    "SizeWE",
    "SizeNESW",
    "SizeNWSE",
    "SizeAll",
    "UpArrow",
    "Hand",
]


class WindowsCursorService:
    """Manages official Windows cursor schemes with backup and restore."""

    def __init__(self):
        user_home = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))).resolve()
        self.cursor_base_dir = user_home / "AppData" / "Local" / "AURA" / "cursors"
        self.cat_paw_dir = self.cursor_base_dir / "kawaii_cat_paw"
        self.backup_file = self.cursor_base_dir / "windows_cursor_backup.json"

        self.cat_paw_dir.mkdir(parents=True, exist_ok=True)

        self.ani_file = self.cat_paw_dir / "Kawaii Pixel Cat Paw Animated Cursor--cursor--SweezyCursors.ani"
        self.cur_file = self.cat_paw_dir / "Kawaii Pixel Cat Paw Animated Cursor--pointer--SweezyCursors.cur"

    def get_status(self) -> Dict[str, Any]:
        """Returns the current Windows cursor configuration and Kawaii Cat Paw installation status."""
        current_arrow = ""
        current_hand = ""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CURSOR_REG_PATH, 0, winreg.KEY_READ) as key:
                try:
                    current_arrow, _ = winreg.QueryValueEx(key, "Arrow")
                except FileNotFoundError:
                    pass
                try:
                    current_hand, _ = winreg.QueryValueEx(key, "Hand")
                except FileNotFoundError:
                    pass
        except Exception as e:
            logger.error(f"Failed to read current Windows cursor registry: {e}")

        is_system_active = (
            str(self.ani_file).lower() in current_arrow.lower()
            or "kawaii" in current_arrow.lower()
        )

        has_backup = self.backup_file.exists()

        return {
            "system_wide_active": is_system_active,
            "current_system_arrow": current_arrow,
            "current_system_hand": current_hand,
            "backup_available": has_backup,
            "ani_asset_exists": self.ani_file.exists(),
            "cur_asset_exists": self.cur_file.exists(),
            "asset_directory": str(self.cat_paw_dir),
        }

    def backup_current_scheme(self) -> bool:
        """Saves current Windows cursor scheme to local backup JSON."""
        saved_values: Dict[str, str] = {}
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CURSOR_REG_PATH, 0, winreg.KEY_READ) as key:
                for role in CURSOR_ROLES:
                    try:
                        val, _ = winreg.QueryValueEx(key, role)
                        saved_values[role] = str(val)
                    except FileNotFoundError:
                        saved_values[role] = ""

            with open(self.backup_file, "w", encoding="utf-8") as f:
                json.dump(saved_values, f, indent=2)

            logger.info(f"Backed up {len(saved_values)} Windows cursor settings to {self.backup_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to back up Windows cursor scheme: {e}")
            return False

    def apply_cat_paw_system_wide(self) -> Dict[str, Any]:
        """
        Applies Kawaii Pixel Cat Paw animated cursor (.ani) and link pointer (.cur)
        to Windows system-wide via official Win32 SystemParametersInfoW.
        """
        if not self.ani_file.exists() or not self.cur_file.exists():
            return {
                "success": False,
                "error": "Required .ani or .cur asset file missing in AURA directory",
            }

        # 1. Back up previous scheme if not already backed up
        if not self.backup_file.exists():
            self.backup_current_scheme()

        ani_path_str = str(self.ani_file.resolve())
        cur_path_str = str(self.cur_file.resolve())

        try:
            # 2. Write to HKCU\Control Panel\Cursors
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CURSOR_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "Arrow", 0, winreg.REG_SZ, ani_path_str)
                winreg.SetValueEx(key, "Hand", 0, winreg.REG_SZ, cur_path_str)
                winreg.SetValueEx(key, "AppStarting", 0, winreg.REG_SZ, ani_path_str)

            # 3. Reload cursor scheme via Win32 SystemParametersInfoW
            res = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETCURSORS, 0, None, 0
            )

            logger.info("Successfully applied Kawaii Pixel Cat Paw cursor system-wide to Windows.")
            return {
                "success": bool(res),
                "message": "Kawaii Pixel Cat Paw cursor applied to Windows successfully.",
                "system_wide_active": True,
            }
        except Exception as e:
            logger.error(f"Failed to apply Windows cursor theme: {e}")
            return {"success": False, "error": str(e)}

    def restore_previous_system_theme(self) -> Dict[str, Any]:
        """
        Restores previous Windows cursor scheme from backup file, or defaults if no backup exists.
        """
        defaults = {
            "Arrow": r"C:\Windows\cursors\aero_arrow.cur",
            "Hand": r"C:\Windows\cursors\aero_link.cur",
            "AppStarting": r"C:\Windows\cursors\aero_working.ani",
            "Wait": r"C:\Windows\cursors\aero_busy.ani",
            "IBeam": "",
        }

        scheme_to_restore = defaults
        if self.backup_file.exists():
            try:
                with open(self.backup_file, "r", encoding="utf-8") as f:
                    scheme_to_restore = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load backup, using Windows defaults: {e}")

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CURSOR_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                for role, path in scheme_to_restore.items():
                    try:
                        winreg.SetValueEx(key, role, 0, winreg.REG_SZ, str(path))
                    except Exception:
                        pass

            res = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETCURSORS, 0, None, 0
            )

            logger.info("Restored previous Windows cursor theme.")
            return {
                "success": bool(res),
                "message": "Original Windows cursor scheme restored.",
                "system_wide_active": False,
            }
        except Exception as e:
            logger.error(f"Failed to restore Windows cursor theme: {e}")
            return {"success": False, "error": str(e)}


# Global service instance
windows_cursor_service = WindowsCursorService()
