"""
Unit Tests for AURA Independent Virtual Assistant Hand & Cursor Skin Manager
Tests .ani and .cur parsing, ZIP package validation, path traversal defense,
theme switching, live WebSocket event emission, and zero-touch Windows cursor preservation.
"""

import os
import io
import json
import zipfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.services.virtual_hand_theme_service import VirtualHandThemeService
from backend.desktop.virtual_hand_controller import VirtualHandController
from backend.services.cursor_service import windows_cursor_service


class TestVirtualHandSystem(unittest.TestCase):
    """Exhaustive tests for Virtual Hand and Skin Management."""

    def setUp(self):
        self.theme_service = VirtualHandThemeService()
        self.hand_controller = VirtualHandController()

    def test_default_theme_seeded_and_active(self):
        """Verify built-in Kawaii Cat Paw is seeded and active by default."""
        active_id = self.theme_service.get_active_theme_id()
        self.assertEqual(active_id, "kawaii_cat_paw")

        active_theme = self.theme_service.get_active_theme()
        self.assertIsNotNone(active_theme)
        self.assertEqual(active_theme.get("id"), "kawaii_cat_paw")
        self.assertTrue(active_theme.get("is_builtin"))
        self.assertIn("normal", active_theme.get("variants", {}))
        self.assertIn("pointer", active_theme.get("variants", {}))

    def test_builtin_theme_cannot_be_deleted(self):
        """Verify built-in themes cannot be deleted."""
        res = self.theme_service.delete_theme("kawaii_cat_paw")
        self.assertFalse(res.get("success"))
        self.assertIn("Built-in", res.get("error", ""))

    def test_safe_zip_import_and_variant_classification(self):
        """Verify safe ZIP archive extraction and automatic variant detection."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            # Minimal 1x1 transparent PNG
            png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            zf.writestr("cat_normal.png", png_bytes)
            zf.writestr("cat_pointer_link.png", png_bytes)
            zf.writestr("cat_text_beam.png", png_bytes)
            zf.writestr("cat_wait_busy.png", png_bytes)
            zf.writestr("cat_drag_grab.png", png_bytes)

        res = self.theme_service.import_theme("My_Cool_Theme.zip", zip_buf.getvalue(), custom_name="My Cool Theme")
        self.assertTrue(res.get("success"), f"Import failed: {res.get('error')}")
        theme = res.get("theme", {})
        self.assertEqual(theme.get("name"), "My Cool Theme")

        # Verify variants were classified by name
        variants = theme.get("variants", {})
        self.assertIn("normal", variants)
        self.assertIn("pointer", variants)
        self.assertIn("typing", variants)
        self.assertIn("waiting", variants)
        self.assertIn("drag", variants)

        # Cleanup test theme
        del_res = self.theme_service.delete_theme(theme.get("id"))
        self.assertTrue(del_res.get("success"))

    def test_malicious_zip_path_traversal_blocked(self):
        """Security: Verify Zip-Slip path traversal is detected and rejected."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("../../Windows/System32/evil.png", b"fake image")

        res = self.theme_service.import_theme("evil.zip", zip_buf.getvalue())
        self.assertFalse(res.get("success"))
        self.assertIn("Security violation", res.get("error", ""))

    def test_forbidden_executable_in_zip_blocked(self):
        """Security: Verify archives containing .exe or scripts are rejected."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("cursor.png", b"\x89PNG...")
            zf.writestr("payload.exe", b"MZ fake executable")

        res = self.theme_service.import_theme("package_with_exe.zip", zip_buf.getvalue())
        self.assertFalse(res.get("success"))
        self.assertIn("Forbidden executable", res.get("error", ""))

    def test_cur_parser_hotspot_extraction(self):
        """Verify .cur parsing extracts image and hotspot."""
        cur_path = Path(os.environ.get("LOCALAPPDATA", "")) / "AURA" / "cursors" / "kawaii_cat_paw" / "Kawaii Pixel Cat Paw Animated Cursor--pointer--SweezyCursors.cur"
        if cur_path.exists():
            img, hotspot = self.theme_service._parse_cur_file(cur_path.read_bytes())
            self.assertIsNotNone(img)
            self.assertGreater(hotspot[0], 0)
            self.assertGreater(hotspot[1], 0)

    def test_ani_parser_frame_extraction(self):
        """Verify .ani parsing extracts frame list and display rate."""
        ani_path = Path(os.environ.get("LOCALAPPDATA", "")) / "AURA" / "cursors" / "kawaii_cat_paw" / "Kawaii Pixel Cat Paw Animated Cursor--cursor--SweezyCursors.ani"
        if ani_path.exists():
            frames, rates, hotspot, def_rate = self.theme_service._parse_ani_file(ani_path.read_bytes())
            self.assertEqual(len(frames), 10)
            self.assertEqual(def_rate, 10)

    def test_virtual_hand_broadcast_events(self):
        """Verify VirtualHandController broadcasts show, move, click, type, and hide events."""
        received_events = []

        class MockWebSocket:
            async def send_json(self, data):
                received_events.append(data)

        mock_ws = MockWebSocket()
        self.hand_controller.register_subscriber(mock_ws)

        # 1. Show
        self.hand_controller.show(100, 200, state="normal")
        # 2. Move
        with patch("backend.desktop.mouse_controller.mouse_controller.move_to"):
            self.hand_controller.move_to(300, 400, duration=0.45, state="pointer", sync_system_mouse=False)
        # 3. Click
        with patch("backend.desktop.mouse_controller.mouse_controller.click"):
            self.hand_controller.click(300, 400, button="left")
        # 4. Type
        with patch("backend.desktop.keyboard_controller.keyboard_controller.type_text"):
            self.hand_controller.type_text("hello aura")
        # 5. Hide
        self.hand_controller.hide()

        self.hand_controller.unregister_subscriber(mock_ws)

        # Verify event sequence
        types = [e.get("type") for e in received_events]
        self.assertIn("hand_show", types)
        self.assertIn("hand_move", types)
        self.assertIn("hand_click", types)
        self.assertIn("hand_type", types)
        self.assertIn("hand_hide", types)

    def test_user_cursor_never_permanently_altered(self):
        """Verify that user's system cursor scheme remains untouched."""
        status = windows_cursor_service.get_status()
        # Ensure system-wide active is False (user's normal cursor restored)
        self.assertFalse(status.get("system_wide_active"))

    def test_upload_endpoint_base64_decoding(self):
        """Verify that uploading base64-encoded cursor skins succeeds without NameError."""
        from fastapi.testclient import TestClient
        from backend.api.app import app
        import base64

        client = TestClient(app)
        raw_gif = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        b64_str = f"data:image/gif;base64,{base64.b64encode(raw_gif).decode('ascii')}"

        res = client.post("/api/virtual-hand/themes/upload", json={
            "filename": "unit_test_skin.gif",
            "custom_name": "Unit Test Skin",
            "content_base64": b64_str,
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"), f"Upload failed: {data}")
        theme_id = data["theme"]["id"]

        # Clean up uploaded test theme
        del_res = client.delete(f"/api/virtual-hand/themes/{theme_id}")
        self.assertEqual(del_res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
