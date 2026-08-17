"""Regression tests for weather routing and current-location behavior."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app import normalize_cli_command
from backend.router.intent_classifier import IntentClassifier
from backend.services.weather_service import WeatherService
from backend.utils.responses import error_response, success_response


class FakeLocationService:
    """Deterministic current-location provider for weather tests."""

    def current_location(self) -> dict[str, Any]:
        return success_response(
            "location",
            "current_location",
            {
                "city": "Test City",
                "state": "Test State",
                "country": "Test Country",
                "latitude": 10.0,
                "longitude": 20.0,
            },
        )


class FailingLocationService:
    """Location provider that simulates permission/network failure."""

    def current_location(self) -> dict[str, Any]:
        return error_response("location", "current_location", "location unavailable")


class FakeHttpClient:
    """Minimal HTTP fake that returns Open-Meteo-like current weather JSON."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    def get_json_response(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        self.urls.append(url)

        class Response:
            status_code = 200
            json_data = {
                "current": {
                    "temperature_2m": 28.5,
                    "relative_humidity_2m": 70,
                    "apparent_temperature": 31.0,
                    "weather_code": 1,
                    "wind_speed_10m": 8.4,
                }
            }

            def __init__(self, final_url: str) -> None:
                self.url = final_url
                self.text = ""

        return Response(url)


def main() -> int:
    classifier = IntentClassifier()
    checks = [
        (normalize_cli_command("/weather"), ("Weather", "Current weather")),
        (classifier.classify("What's the weather?").query, ""),
        (classifier.classify("Current weather").query, ""),
        (classifier.classify("What's the weather in Mumbai?").query, "Mumbai"),
    ]

    failures = 0
    for actual, expected in checks:
        if actual != expected:
            print(f"FAIL expected {expected!r}, got {actual!r}")
            failures += 1

    service = WeatherService(http_client=FakeHttpClient(), location_service=FakeLocationService())
    response = service.current_weather("")
    if not response["ok"] or "Weather for Test City" not in str(response.get("message")):
        print("FAIL current-location weather did not return formatted weather")
        failures += 1

    failing_service = WeatherService(http_client=FakeHttpClient(), location_service=FailingLocationService())
    failed = failing_service.current_weather("")
    if failed["ok"] or "Which city" not in str((failed.get("error") or {}).get("message")):
        print("FAIL failed location detection did not ask for a city")
        failures += 1

    if failures:
        return 1
    print("PASS weather routing and current-location behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
