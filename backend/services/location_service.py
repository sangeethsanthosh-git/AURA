"""Current-location detection for AURA.

The implementation uses IP-based geolocation because the current CLI has no
desktop permission flow for GPS. The service is intentionally isolated behind a
small class so Electron can later replace it with OS/browser location APIs.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.config.config import Settings, settings
from backend.utils.http_client import HttpClient, HttpClientError
from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


class LocationService:
    """Detects the user's approximate current location."""

    def __init__(
        self,
        config: Settings = settings,
        http_client: HttpClient | None = None,
    ) -> None:
        self.config = config
        self.http_client = http_client or HttpClient(
            timeout=config.request_timeout,
            retry_attempts=config.retry_attempts,
            retry_backoff_seconds=config.retry_backoff_seconds,
        )

    def current_location(self) -> dict[str, Any]:
        """Return city, state, country, latitude, and longitude."""
        LOGGER.info("LocationService: detecting current location.")
        try:
            raw = self.http_client.get_json(self.config.location_api_url)
            location = {
                "city": raw.get("city"),
                "state": raw.get("region"),
                "country": raw.get("country_name"),
                "latitude": raw.get("latitude"),
                "longitude": raw.get("longitude"),
            }
            if not location["latitude"] or not location["longitude"]:
                LOGGER.error("Location detection failed: missing coordinates. Response=%s", raw)
                return error_response("location", "current_location", "Current location has no coordinates.", details=raw)
            return success_response("location", "current_location", location)
        except HttpClientError as exc:
            LOGGER.exception("Location detection failed.")
            return error_response("location", "current_location", str(exc), exc.status_code, exc.details)
