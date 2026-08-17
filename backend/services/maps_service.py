"""OpenStreetMap Nominatim service adapter."""

from __future__ import annotations

import logging
import time
from typing import Any

from backend.config.config import Settings, settings
from backend.utils.http_client import HttpClient, HttpClientError
from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


class MapsService:
    """Provides location search and reverse geocoding with polite rate limiting."""

    BASE_URL = "https://nominatim.openstreetmap.org"

    def __init__(
        self,
        config: Settings = settings,
        http_client: HttpClient | None = None,
        min_interval_seconds: float = 1.0,
    ) -> None:
        self.config = config
        self.http_client = http_client or HttpClient(
            timeout=config.request_timeout,
            retry_attempts=config.retry_attempts,
            retry_backoff_seconds=config.retry_backoff_seconds,
        )
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at = 0.0

    def search_location(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Search Nominatim for locations matching a query."""
        self._respect_rate_limit()
        try:
            raw = self.http_client.get_json(
                f"{self.BASE_URL}/search",
                params={"q": query, "format": "jsonv2", "limit": limit, "addressdetails": 1},
                headers=self._headers(),
            )
            results = [self._clean_location(item) for item in raw]
            return success_response("maps", "search_location", {"query": query, "results": results})
        except HttpClientError as exc:
            LOGGER.exception("Nominatim search failed.")
            return error_response("maps", "search_location", str(exc), exc.status_code, exc.details)

    def reverse_geocode(self, latitude: float, longitude: float) -> dict[str, Any]:
        """Resolve coordinates into a human-readable address."""
        self._respect_rate_limit()
        try:
            raw = self.http_client.get_json(
                f"{self.BASE_URL}/reverse",
                params={"lat": latitude, "lon": longitude, "format": "jsonv2", "addressdetails": 1},
                headers=self._headers(),
            )
            return success_response("maps", "reverse_geocode", self._clean_location(raw))
        except HttpClientError as exc:
            LOGGER.exception("Nominatim reverse geocode failed.")
            return error_response("maps", "reverse_geocode", str(exc), exc.status_code, exc.details)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.config.nominatim_user_agent}

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()

    @staticmethod
    def _clean_location(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "display_name": item.get("display_name"),
            "latitude": item.get("lat"),
            "longitude": item.get("lon"),
            "category": item.get("category"),
            "type": item.get("type"),
            "importance": item.get("importance"),
            "address": item.get("address", {}),
        }
