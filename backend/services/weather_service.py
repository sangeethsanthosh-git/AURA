"""Open-Meteo weather service adapter with detailed diagnostics."""

from __future__ import annotations

import logging
import time
from typing import Any

from backend.config.config import Settings, settings
from backend.services.location_service import LocationService
from backend.utils.http_client import HttpClient, HttpClientError
from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


class LocationDetectionError(RuntimeError):
    """Raised when automatic location detection cannot provide coordinates."""


class WeatherService:
    """Provides current weather and forecasts via Open-Meteo."""

    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    USER_FRIENDLY_FAILURE = "Sorry, I couldn't retrieve the live weather."

    WEATHER_CODES = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
    }

    def __init__(
        self,
        config: Settings = settings,
        http_client: HttpClient | None = None,
        location_service: LocationService | None = None,
    ) -> None:
        self.config = config
        self.http_client = http_client or HttpClient(
            timeout=config.request_timeout,
            retry_attempts=config.retry_attempts,
            retry_backoff_seconds=config.retry_backoff_seconds,
        )
        self.location_service = location_service or LocationService(config, self.http_client)

    def current_weather(self, location: str | None = None) -> dict[str, Any]:
        """Return current weather for a city or for the detected current location."""
        started_at = time.perf_counter()
        diagnostics: dict[str, Any] = {"requested_location": location}
        LOGGER.info("Weather step 1: receive city name. city=%r", location)

        try:
            place = self._resolve_place(location, diagnostics)
            latitude = place["latitude"]
            longitude = place["longitude"]
            diagnostics["latitude"] = latitude
            diagnostics["longitude"] = longitude
            LOGGER.info("Weather step 3: latitude=%s longitude=%s", latitude, longitude)

            if not self._valid_coordinates(latitude, longitude):
                LOGGER.error("Invalid coordinates. place=%s", place)
                return self._failure("Invalid coordinates.", diagnostics, started_at)

            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                "timezone": "auto",
            }
            LOGGER.info("Weather step 4: call Open-Meteo. params=%s", params)

            try:
                http_response = self.http_client.get_json_response(self.FORECAST_URL, params=params)
            except HttpClientError as exc:
                if "timed out" in str(exc).lower():
                    LOGGER.exception("Open-Meteo request timed out.")
                elif "json parsing failed" in str(exc).lower():
                    LOGGER.exception("JSON parsing failed.")
                else:
                    LOGGER.exception("Open-Meteo request failed.")
                return self._failure(str(exc), diagnostics, started_at, exc)

            diagnostics.update(
                {
                    "url": http_response.url,
                    "http_status": http_response.status_code,
                    "json_response": http_response.json_data,
                }
            )
            LOGGER.info("Weather step 5: HTTP status=%s", http_response.status_code)
            LOGGER.info("Weather step 6: parse JSON succeeded.")

            current = http_response.json_data.get("current")
            if not current:
                LOGGER.error("No weather data returned. response=%s", http_response.json_data)
                return self._failure("No weather data returned.", diagnostics, started_at)

            weather = self._format_current_weather(place, current)
            diagnostics["execution_time_seconds"] = round(time.perf_counter() - started_at, 2)
            self._log_debug(diagnostics)
            LOGGER.info("Weather step 7: return formatted weather. message=%s", weather["message"])
            return success_response(
                "weather",
                "current_weather",
                {
                    "location": place,
                    "current_weather": current,
                    "formatted_weather": weather,
                    "debug": diagnostics if self.config.debug else {},
                },
                message=weather["message"],
            )
        except Exception as exc:
            if isinstance(exc, LocationDetectionError):
                LOGGER.error("Location detection failed: %s", exc)
                return error_response(
                    "weather",
                    "current_weather",
                    str(exc),
                    details=diagnostics if self.config.debug else None,
                )
            LOGGER.exception("Weather service failed unexpectedly.")
            return self._failure("Unexpected weather service error.", diagnostics, started_at, exc)

    def forecast(self, location: str, days: int = 3) -> dict[str, Any]:
        """Return a daily forecast for a human-readable location."""
        diagnostics: dict[str, Any] = {"requested_location": location, "days": days}
        started_at = time.perf_counter()
        try:
            place = self._resolve_place(location, diagnostics)
            if not self._valid_coordinates(place["latitude"], place["longitude"]):
                LOGGER.error("Invalid coordinates for forecast. place=%s", place)
                return self._failure("Invalid coordinates.", diagnostics, started_at)

            http_response = self.http_client.get_json_response(
                self.FORECAST_URL,
                params={
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "forecast_days": days,
                    "timezone": "auto",
                },
            )
            LOGGER.info("Open-Meteo forecast HTTP status=%s", http_response.status_code)
            return success_response(
                "weather",
                "forecast",
                {"location": place, "forecast": http_response.json_data.get("daily", {}), "raw": http_response.json_data},
            )
        except Exception as exc:
            LOGGER.exception("Open-Meteo forecast failed.")
            return self._failure("Forecast request failed.", diagnostics, started_at, exc)

    def _resolve_place(self, location: str | None, diagnostics: dict[str, Any]) -> dict[str, Any]:
        city = (location or "").strip()
        if city:
            diagnostics["city"] = city
            LOGGER.info("Weather step 2: call geocoding service. city=%s", city)
            return self._geocode(city, diagnostics)

        LOGGER.info("Weather step 2: no city supplied; detecting current location.")
        detected = self.location_service.current_location()
        if not detected.get("ok"):
            LOGGER.error("Location detection failed. response=%s", detected)
            raise LocationDetectionError(
                "I couldn't determine your location. Which city would you like the weather for?"
            )

        data = detected["data"]
        place = {
            "name": data.get("city"),
            "state": data.get("state"),
            "country": data.get("country"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "timezone": None,
        }
        diagnostics.update({"city": place["name"], "location_source": "current_location"})
        return place

    def _geocode(self, location: str, diagnostics: dict[str, Any]) -> dict[str, Any]:
        params: dict[str, Any] = {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json",
        }
        if self.config.default_country_code:
            params["countryCode"] = self.config.default_country_code

        try:
            http_response = self.http_client.get_json_response(self.GEOCODE_URL, params=params)
            LOGGER.info("Geocoding HTTP status=%s", http_response.status_code)
            diagnostics["geocoding_url"] = http_response.url
            diagnostics["geocoding_http_status"] = http_response.status_code
            diagnostics["geocoding_response"] = http_response.json_data
        except HttpClientError as exc:
            LOGGER.exception("Geocoding failed.")
            raise RuntimeError("Geocoding failed.") from exc

        results = http_response.json_data.get("results", [])
        if not results:
            LOGGER.error("Geocoding failed. No result for city=%s response=%s", location, http_response.json_data)
            raise RuntimeError("Geocoding failed.")

        first = results[0]
        return {
            "name": first.get("name"),
            "state": first.get("admin1"),
            "country": first.get("country"),
            "latitude": first.get("latitude"),
            "longitude": first.get("longitude"),
            "timezone": first.get("timezone"),
        }

    def _format_current_weather(self, place: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        temperature = current.get("temperature_2m")
        condition = self.WEATHER_CODES.get(current.get("weather_code"), "Unknown conditions")
        wind_speed = current.get("wind_speed_10m")
        humidity = current.get("relative_humidity_2m")
        feels_like = current.get("apparent_temperature")
        location_name = ", ".join(
            str(part)
            for part in (place.get("name"), place.get("state"), place.get("country"))
            if part
        )

        details = [
            f"Weather for {location_name}",
            f"Temperature: {temperature} deg C",
            f"Condition: {condition}",
            f"Wind speed: {wind_speed} km/h",
        ]
        if humidity is not None:
            details.append(f"Humidity: {humidity}%")
        if feels_like is not None:
            details.append(f"Feels like: {feels_like} deg C")

        return {
            "temperature": temperature,
            "condition": condition,
            "wind_speed": wind_speed,
            "humidity": humidity,
            "feels_like": feels_like,
            "message": "\n".join(details),
        }

    def _failure(
        self,
        reason: str,
        diagnostics: dict[str, Any],
        started_at: float,
        exc: Exception | None = None,
    ) -> dict[str, Any]:
        diagnostics["failure_step"] = reason
        diagnostics["execution_time_seconds"] = round(time.perf_counter() - started_at, 2)
        if exc is not None:
            diagnostics["exception"] = repr(exc)
        self._log_debug(diagnostics)
        return error_response(
            "weather",
            "current_weather",
            self.USER_FRIENDLY_FAILURE,
            details=diagnostics if self.config.debug else None,
        )

    def _log_debug(self, diagnostics: dict[str, Any]) -> None:
        if not self.config.debug:
            return
        LOGGER.debug(
            "Weather DEBUG | City=%s | Latitude=%s | Longitude=%s | URL=%s | "
            "HTTP Status=%s | Execution Time=%s | JSON Response=%s",
            diagnostics.get("city"),
            diagnostics.get("latitude"),
            diagnostics.get("longitude"),
            diagnostics.get("url"),
            diagnostics.get("http_status"),
            diagnostics.get("execution_time_seconds"),
            diagnostics.get("json_response"),
        )

    @staticmethod
    def _valid_coordinates(latitude: Any, longitude: Any) -> bool:
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError):
            return False
        return -90 <= lat <= 90 and -180 <= lon <= 180
