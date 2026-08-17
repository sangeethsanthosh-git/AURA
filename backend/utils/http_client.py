"""Small HTTP client with retries for stdlib-only service adapters."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)
DEFAULT_USER_AGENT = "AURA-MCA-MiniProject/1.0"


class HttpClientError(RuntimeError):
    """Raised when an HTTP request fails after retry handling."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


@dataclass(frozen=True)
class HttpJsonResponse:
    """JSON response plus diagnostics needed by debug-heavy services."""

    url: str
    status_code: int
    json_data: Any
    text: str


@dataclass(frozen=True)
class HttpClient:
    """Minimal JSON HTTP client with exponential backoff.

    A shared client keeps timeout, retry, and JSON parsing behavior consistent
    across providers while avoiding a heavyweight dependency for the mini
    project stage.
    """

    timeout: int = 30
    retry_attempts: int = 3
    retry_backoff_seconds: float = 1.0

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"
        return self._request_json("GET", url, headers=headers)

    def get_json_response(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpJsonResponse:
        """GET JSON and return HTTP diagnostics with the parsed body."""
        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"
        return self._request_json_response("GET", url, headers=headers)

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> Any:
        data = json.dumps(payload).encode("utf-8")
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        return self._request_json("POST", url, data=data, headers=request_headers)

    def stream_post_json_lines(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ):
        data = json.dumps(payload).encode("utf-8")
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        request = Request(url, data=data, headers=request_headers, method="POST")

        try:
            with urlopen(request, timeout=self.timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if line:
                        yield line
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HttpClientError(
                f"HTTP error {exc.code}",
                status_code=exc.code,
                details=detail,
            ) from exc
        except URLError as exc:
            raise HttpClientError(f"Network error: {exc.reason}") from exc

    def _request_json(
        self,
        method: str,
        url: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        last_error: HttpClientError | None = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                request_headers = {"User-Agent": DEFAULT_USER_AGENT, **(headers or {})}
                request = Request(url, data=data, headers=request_headers, method=method)
                with urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8", errors="replace")
                return json.loads(body) if body else {}
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = HttpClientError(
                    f"HTTP error {exc.code}",
                    status_code=exc.code,
                    details=detail,
                )
                if exc.code < 500 and exc.code not in {408, 429}:
                    raise last_error from exc
            except URLError as exc:
                last_error = HttpClientError(f"Network error: {exc.reason}")
            except TimeoutError as exc:
                last_error = HttpClientError("Request timed out")
            except json.JSONDecodeError as exc:
                raise HttpClientError("Response was not valid JSON") from exc

            LOGGER.warning(
                "HTTP %s failed for %s on attempt %s/%s: %s",
                method,
                url,
                attempt,
                self.retry_attempts,
                last_error,
            )
            if attempt < self.retry_attempts:
                time.sleep(self.retry_backoff_seconds * attempt)

        raise last_error or HttpClientError("Request failed")

    def _request_json_response(
        self,
        method: str,
        url: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpJsonResponse:
        last_error: HttpClientError | None = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                request_headers = {"User-Agent": DEFAULT_USER_AGENT, **(headers or {})}
                request = Request(url, data=data, headers=request_headers, method=method)
                with urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8", errors="replace")
                    status_code = response.status
                    final_url = response.geturl()
                try:
                    parsed = json.loads(body) if body else {}
                except json.JSONDecodeError as exc:
                    raise HttpClientError(
                        "JSON parsing failed.",
                        status_code=status_code,
                        details=body,
                    ) from exc
                return HttpJsonResponse(final_url, status_code, parsed, body)
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = HttpClientError(
                    f"HTTP error {exc.code}",
                    status_code=exc.code,
                    details=detail,
                )
                if exc.code < 500 and exc.code not in {408, 429}:
                    raise last_error from exc
            except URLError as exc:
                last_error = HttpClientError(f"Network error: {exc.reason}")
            except TimeoutError:
                last_error = HttpClientError("Request timed out")

            LOGGER.warning(
                "HTTP %s failed for %s on attempt %s/%s: %s",
                method,
                url,
                attempt,
                self.retry_attempts,
                last_error,
            )
            if attempt < self.retry_attempts:
                time.sleep(self.retry_backoff_seconds * attempt)

        raise last_error or HttpClientError("Request failed")
