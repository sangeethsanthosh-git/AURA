"""Wikipedia API service adapter."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from backend.config.config import Settings, settings
from backend.utils.http_client import HttpClient, HttpClientError
from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


class WikipediaService:
    """Provides search, summary, page, and disambiguation helpers."""

    API_URL = "https://en.wikipedia.org/w/api.php"
    SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"

    def __init__(
        self,
        config: Settings = settings,
        http_client: HttpClient | None = None,
    ) -> None:
        self.http_client = http_client or HttpClient(
            timeout=config.request_timeout,
            retry_attempts=config.retry_attempts,
            retry_backoff_seconds=config.retry_backoff_seconds,
        )

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Search Wikipedia pages by title and snippet."""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }
        try:
            raw = self.http_client.get_json(self.API_URL, params=params)
            results = [
                {
                    "title": item.get("title"),
                    "pageid": item.get("pageid"),
                    "snippet": item.get("snippet"),
                }
                for item in raw.get("query", {}).get("search", [])
            ]
            return success_response("wikipedia", "search", {"query": query, "results": results})
        except HttpClientError as exc:
            LOGGER.exception("Wikipedia search failed.")
            return error_response("wikipedia", "search", str(exc), exc.status_code, exc.details)

    def summary(self, title: str) -> dict[str, Any]:
        """Fetch the public REST summary for a page title."""
        try:
            safe_title = quote(title.replace(" ", "_"), safe="")
            raw = self.http_client.get_json(f"{self.SUMMARY_URL}/{safe_title}")
            if raw.get("type") == "disambiguation":
                return self.handle_disambiguation(title)
            return success_response(
                "wikipedia",
                "summary",
                {
                    "title": raw.get("title"),
                    "extract": raw.get("extract"),
                    "url": raw.get("content_urls", {}).get("desktop", {}).get("page"),
                    "raw": raw,
                },
                message=raw.get("extract"),
            )
        except HttpClientError as exc:
            LOGGER.exception("Wikipedia summary failed.")
            return error_response("wikipedia", "summary", str(exc), exc.status_code, exc.details)

    def page(self, title: str) -> dict[str, Any]:
        """Fetch plain text extracts and canonical metadata for a page."""
        params = {
            "action": "query",
            "prop": "extracts|info",
            "explaintext": 1,
            "inprop": "url",
            "redirects": 1,
            "titles": title,
            "format": "json",
            "utf8": 1,
        }
        try:
            raw = self.http_client.get_json(self.API_URL, params=params)
            pages = raw.get("query", {}).get("pages", {})
            page_data = next(iter(pages.values()), {})
            if page_data.get("missing") == "":
                return error_response("wikipedia", "page", f"No Wikipedia page found for '{title}'.")
            return success_response(
                "wikipedia",
                "page",
                {
                    "title": page_data.get("title"),
                    "pageid": page_data.get("pageid"),
                    "extract": page_data.get("extract"),
                    "url": page_data.get("fullurl"),
                },
            )
        except HttpClientError as exc:
            LOGGER.exception("Wikipedia page fetch failed.")
            return error_response("wikipedia", "page", str(exc), exc.status_code, exc.details)

    def handle_disambiguation(self, title: str) -> dict[str, Any]:
        """Return search suggestions when a title resolves to a disambiguation page."""
        response = self.search(title, limit=10)
        if not response["ok"]:
            return response
        return success_response(
            "wikipedia",
            "handle_disambiguation",
            {
                "title": title,
                "suggestions": response["data"]["results"],
            },
            message=f"'{title}' is ambiguous. Choose one of the suggestions.",
        )
