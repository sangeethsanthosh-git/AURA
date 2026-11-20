"""
Unit tests for Phase 3 Desktop Interface & WebSocket backend.
"""

from pathlib import Path
import unittest
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.api.app import app


class TestPhase3(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        from backend.api.app import wake_word_service
        wake_word_service.stop()

    def test_01_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "online")
        self.assertTrue(data.get("ollama_connected"))
        self.assertTrue(data.get("tts_ready"))

    def test_02_websocket_handshake(self):
        with self.client.websocket_connect("/ws") as ws:
            # First message received is current state
            data = ws.receive_json()
            self.assertEqual(data.get("type"), "state_change")
            self.assertIn(data.get("state"), ["IDLE", "LISTENING", "THINKING", "SPEAKING", "ERROR"])

    def test_03_websocket_state_query(self):
        with self.client.websocket_connect("/ws") as ws:
            # Drain initial state
            _ = ws.receive_json()
            # Send get_state query
            ws.send_json({"type": "get_state"})
            response = ws.receive_json()
            self.assertEqual(response.get("type"), "state_change")
            self.assertIsNotNone(response.get("model"))


if __name__ == "__main__":
    unittest.main()
