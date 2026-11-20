"""
Unit tests for Wikipedia Deep Search & Image Discovery integration.
"""

from pathlib import Path
import unittest
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.services.wikipedia_service import WikipediaService
from backend.api.app import app, wake_word_service, _sanitize_llm_history


class TestWikipediaDeepSearch(unittest.TestCase):
    def setUp(self):
        self.wiki = WikipediaService()
        self.client = TestClient(app)

    def tearDown(self):
        wake_word_service.stop()

    def test_01_query_detection_and_greeting_filter(self):
        # Casual, math, and coding/writing prompts must stay 100% local
        self.assertEqual(self.wiki.should_search("hi", deep_search_enabled=True), (False, ""))
        self.assertEqual(self.wiki.should_search("How are you?", deep_search_enabled=True), (False, ""))
        self.assertEqual(self.wiki.should_search("What is 2 + 2?", deep_search_enabled=True), (False, ""))
        self.assertEqual(self.wiki.should_search("Tell me a joke", deep_search_enabled=True), (False, ""))
        self.assertEqual(
            self.wiki.should_search("write a simple python program to add two numbers", deep_search_enabled=True),
            (False, ""),
        )
        self.assertEqual(
            self.wiki.should_search("write a xml file for a android app", deep_search_enabled=True),
            (False, ""),
        )
        self.assertEqual(
            self.wiki.should_search("can you write a script for me", deep_search_enabled=True),
            (False, ""),
        )

        # Factual knowledge questions trigger Wikipedia when enabled
        should_run, query = self.wiki.should_search("Who is Alan Turing?", deep_search_enabled=True)
        self.assertTrue(should_run)
        self.assertEqual(query, "Alan Turing")

        should_saturn, q_saturn = self.wiki.should_search("Tell me about Saturn", deep_search_enabled=True)
        self.assertTrue(should_saturn)
        self.assertEqual(q_saturn, "Saturn")

        # When auto deep search is disabled, only explicit triggers run
        self.assertEqual(self.wiki.should_search("Tell me about Mars", deep_search_enabled=False)[0], False)
        explicit_run, explicit_query = self.wiki.should_search(
            "show me images of the Eiffel Tower", deep_search_enabled=False
        )
        self.assertTrue(explicit_run)
        self.assertEqual(explicit_query, "Eiffel Tower")

    def test_02_deep_search_articles_and_images(self):
        result = self.wiki.deep_search("Apollo 11", max_articles=3, max_images=4)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result["articles"]), 1)
        self.assertGreaterEqual(len(result["images"]), 1)
        for img in result["images"]:
            self.assertTrue(img["url"].startswith("https://"))

        context = self.wiki.format_context_for_llm(result)
        self.assertIn("Apollo 11", context)

    def test_03_graceful_fallback_on_empty_or_nonsense(self):
        self.assertIsNone(self.wiki.deep_search(""))
        self.assertIsNone(self.wiki.deep_search("zzzzxqwkjfhalskdjfh123456789"))

    def test_04_websocket_deep_search_toggle(self):
        with self.client.websocket_connect("/ws") as ws:
            initial = ws.receive_json()
            self.assertIn("deep_search_active", initial)
            orig_state = initial["deep_search_active"]

            ws.send_json({"type": "toggle_deep_search", "enabled": not orig_state})
            toggled = ws.receive_json()
            self.assertEqual(toggled.get("type"), "deep_search_status")
            self.assertEqual(toggled.get("active"), not orig_state)

            # Restore original state
            ws.send_json({"type": "toggle_deep_search", "enabled": orig_state})
            restored = ws.receive_json()
            self.assertEqual(restored.get("active"), orig_state)

    def test_05_history_sanitization(self):
        # Orphaned user message followed by new user query should drop the unpaired user turn
        corrupted = [
            {"role": "user", "content": "write a simple python program"},
            {"role": "user", "content": "Show me images of the Taj Mahal"},
        ]
        cleaned = _sanitize_llm_history(corrupted)
        self.assertEqual(cleaned, [{"role": "user", "content": "Show me images of the Taj Mahal"}])

        # Valid alternating pair + new query preserved
        valid = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "Tell me about Mars"},
        ]
        self.assertEqual(_sanitize_llm_history(valid), valid)

    def test_06_wiki_image_proxy_and_allowlist(self):
        # Disallowed external host should return 404
        blocked = self.client.get("/api/wiki-image", params={"url": "https://example.com/test.jpg"})
        self.assertEqual(blocked.status_code, 404)

        # Real Wikimedia URL returned by deep_search should proxy cleanly with 200 image/*
        res = self.wiki.deep_search("Apollo 11", max_articles=1, max_images=1)
        if res and res["images"]:
            img_url = res["images"][0]["url"]
            proxied = self.client.get("/api/wiki-image", params={"url": img_url})
            self.assertEqual(proxied.status_code, 200)
            self.assertTrue(proxied.headers.get("content-type", "").startswith("image/"))


if __name__ == "__main__":
    unittest.main()
