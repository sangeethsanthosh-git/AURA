"""
Unit Tests for AURA Windows Cursor Service
Validates asset detection, scheme backup, registry queries, and restoration.
"""

import unittest
import os
from pathlib import Path
from backend.services.cursor_service import windows_cursor_service


class TestWindowsCursorService(unittest.TestCase):
    """Cursor service test cases."""

    def test_cursor_status(self):
        status = windows_cursor_service.get_status()
        self.assertIn("system_wide_active", status)
        self.assertIn("current_system_arrow", status)
        self.assertTrue(status["ani_asset_exists"], ".ani asset must exist")
        self.assertTrue(status["cur_asset_exists"], ".cur asset must exist")
        self.assertTrue(os.path.isdir(status["asset_directory"]))

    def test_backup_scheme(self):
        success = windows_cursor_service.backup_current_scheme()
        self.assertTrue(success)
        self.assertTrue(windows_cursor_service.backup_file.exists())


if __name__ == "__main__":
    unittest.main()
