"""Tests for the RSS-backed news service."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.services.news_service import NewsService


class FakeResponse:
    def __init__(self, body: bytes | None = None):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self) -> bytes:
        return self._body or b"""<?xml version="1.0"?>
        <rss><channel>
          <item>
            <title>Daily AURA headline</title>
            <link>https://example.com/news</link>
            <description><![CDATA[<p>Fresh source-backed update.</p>]]></description>
            <pubDate>Thu, 27 Aug 2026 12:00:00 GMT</pubDate>
          </item>
        </channel></rss>"""


class NewsServiceTest(unittest.TestCase):
    def test_headlines_parse_public_rss_shape(self) -> None:
        fake_settings = SimpleNamespace(request_timeout=1, newsapi_key=None, newsapi_country="in")
        with (
            patch("backend.services.news_service.settings", fake_settings),
            patch("backend.services.news_service.urlopen", return_value=FakeResponse()),
        ):
            response = NewsService(timeout=1).headlines(limit=1)

        self.assertTrue(response["ok"])
        article = response["data"]["articles"][0]
        self.assertEqual(article["title"], "Daily AURA headline")
        self.assertEqual(article["url"], "https://example.com/news")
        self.assertEqual(article["excerpt"], "Fresh source-backed update.")
        self.assertEqual(response["data"]["source"], "Public RSS feeds")

    def test_headlines_use_newsapi_header_when_key_is_configured(self) -> None:
        body = b"""{
          "status": "ok",
          "articles": [
            {
              "source": {"name": "NewsAPI Source"},
              "title": "Live API headline",
              "description": "Current source-backed update.",
              "url": "https://example.com/api-news",
              "publishedAt": "2026-08-27T12:00:00Z"
            }
          ]
        }"""
        captured_headers: dict[str, str] = {}

        def fake_urlopen(request, timeout=1):
            captured_headers.update(dict(request.header_items()))
            return FakeResponse(body)

        fake_settings = SimpleNamespace(request_timeout=1, newsapi_key="test-key", newsapi_country="in")
        with (
            patch("backend.services.news_service.settings", fake_settings),
            patch("backend.services.news_service.urlopen", side_effect=fake_urlopen),
        ):
            response = NewsService(timeout=1).headlines(category="Technology", limit=1)

        self.assertTrue(response["ok"])
        self.assertEqual(response["data"]["source"], "NewsAPI.org")
        self.assertEqual(response["data"]["articles"][0]["title"], "Live API headline")
        self.assertEqual(captured_headers["X-api-key"], "test-key")

    def test_headlines_fall_back_to_rss_when_newsapi_fails(self) -> None:
        calls = {"count": 0}

        def fake_urlopen(_request, timeout=1):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("api down")
            return FakeResponse()

        fake_settings = SimpleNamespace(request_timeout=1, newsapi_key="test-key", newsapi_country="in")
        with (
            patch("backend.services.news_service.settings", fake_settings),
            patch("backend.services.news_service.urlopen", side_effect=fake_urlopen),
        ):
            response = NewsService(timeout=1).headlines(limit=1)

        self.assertTrue(response["ok"])
        self.assertEqual(response["data"]["source"], "Public RSS feeds")
        self.assertEqual(response["data"]["articles"][0]["title"], "Daily AURA headline")


if __name__ == "__main__":
    unittest.main()
