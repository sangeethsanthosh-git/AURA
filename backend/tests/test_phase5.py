"""
Unit tests for Phase 5 Conversation Improvements (Storage, History, Cancellation).
"""

from pathlib import Path
import unittest
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.conversation.storage import ConversationStorage
from backend.services.audio_service import AudioService
from backend.api.app import app, wake_word_service


class TestPhase5(unittest.TestCase):
    def setUp(self):
        test_db = PROJECT_ROOT / "assets" / "test_aura.db"
        self.storage = ConversationStorage(db_path=test_db)
        self.session_id = self.storage.create_session("Test Session")
        self.client = TestClient(app)

    def tearDown(self):
        wake_word_service.stop()
        test_db = PROJECT_ROOT / "assets" / "test_aura.db"
        if test_db.exists():
            try:
                test_db.unlink()
            except Exception:
                pass

    def test_01_session_creation(self):
        self.assertIsInstance(self.session_id, int)
        self.assertGreater(self.session_id, 0)

    def test_02_add_and_retrieve_messages(self):
        self.storage.add_message(self.session_id, "user", "What is quantum mechanics?")
        self.storage.add_message(self.session_id, "assistant", "Quantum mechanics is fundamental physics.")

        messages = self.storage.get_recent_messages(self.session_id, limit=6)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "What is quantum mechanics?")
        self.assertEqual(messages[1]["role"], "assistant")

    def test_03_context_window_limit(self):
        # Insert 10 messages
        for i in range(10):
            self.storage.add_message(self.session_id, "user" if i % 2 == 0 else "assistant", f"Message {i}")

        # Limit to 6 (3 turns)
        recent = self.storage.get_recent_messages(self.session_id, limit=6)
        self.assertEqual(len(recent), 6)
        self.assertEqual(recent[0]["content"], "Message 4")
        self.assertEqual(recent[-1]["content"], "Message 9")

    def test_04_persistent_settings(self):
        self.storage.set_setting("theme", "dark")
        self.assertEqual(self.storage.get_setting("theme"), "dark")
        self.storage.set_setting("theme", "midnight")
        self.assertEqual(self.storage.get_setting("theme"), "midnight")

    def test_05_frontend_dist_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('<div id="root"></div>', response.text)

    def test_06_websocket_new_conversation_and_cancel(self):
        with self.client.websocket_connect("/ws") as ws:
            initial = ws.receive_json()
            self.assertEqual(initial.get("type"), "state_change")
            old_session = initial.get("session_id")

            # Request new conversation
            ws.send_json({"type": "new_conversation"})
            cleared = ws.receive_json()
            self.assertEqual(cleared.get("type"), "conversation_cleared")
            self.assertGreater(cleared.get("session_id"), old_session)

            # Drain state_change back to IDLE
            state_msg = ws.receive_json()
            self.assertEqual(state_msg.get("state"), "IDLE")

            # Send cancel command
            ws.send_json({"type": "cancel"})
            cancel_state = ws.receive_json()
            self.assertEqual(cancel_state.get("state"), "IDLE")

    def test_07_audio_stop_sets_cancel_event(self):
        audio = AudioService()
        self.assertFalse(audio._cancel_record_event.is_set())
        audio.stop()
        self.assertTrue(audio._cancel_record_event.is_set())


if __name__ == "__main__":
    unittest.main()
