"""HTTP REST server for the AURA backend."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from backend.api.auth import AuthService, public_user
from backend.api.config import settings
from backend.api.database import connect, migrate
from backend.api.errors import ApiError, failure, success
from backend.api.openapi import OPENAPI_DOCUMENT
from backend.api.repositories import AuditRepository
from backend.api.validators import require_object, require_string
from backend.services.weather_service import WeatherService
from backend.web.search import CompositeSearchProvider
from ui.controller.aura_controller import AuraController

LOGGER = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self) -> None:
        self.hits: dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        now = time.time()
        window = now - 60
        hits = [ts for ts in self.hits.get(key, []) if ts >= window]
        if len(hits) >= settings.rate_limit_per_minute:
            raise ApiError(429, "RATE_LIMITED", "Too many requests. Please try again shortly.")
        hits.append(now)
        self.hits[key] = hits


class AuraApiServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, AuraHandler)
        self.conn = connect()
        migrate(self.conn)
        self.controller = AuraController()
        self.rate_limiter = RateLimiter()
        self.db_lock = threading.RLock()


class AuraHandler(BaseHTTPRequestHandler):
    server: AuraApiServer

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)

    def do_OPTIONS(self) -> None:
        self._send(204, None)

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def _handle(self) -> None:
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        try:
            self.server.rate_limiter.check(self.client_address[0])
            data, status = self._route(request_id)
            self._send(status, data, request_id)
        except ApiError as exc:
            self._send(exc.status, failure(exc.code, exc.message, exc.details), request_id)
        except Exception:
            LOGGER.exception("Unhandled API error")
            message = "Internal server error." if not settings.debug else "Unhandled API error."
            self._send(500, failure("INTERNAL_SERVER_ERROR", message), request_id)
        finally:
            LOGGER.info(
                "request_id=%s method=%s path=%s status_done duration_ms=%.2f",
                request_id,
                self.command,
                self.path,
                (time.perf_counter() - started) * 1000,
            )

    def _route(self, request_id: str) -> tuple[dict[str, Any], int]:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        body = self._json_body()
        auth = AuthService(self.server.conn)

        if self.command == "GET" and path == "/api/v1/health":
            return success({"status": "ok", "backend": "READY"}), 200
        if self.command == "GET" and path == "/api/v1/openapi.json":
            return OPENAPI_DOCUMENT, 200
        if self.command == "POST" and path == "/api/v1/auth/register":
            payload = require_object(body)
            with self.server.db_lock:
                result = auth.register(require_string(payload, "email"), require_string(payload, "password", min_len=8, max_len=128), payload.get("display_name"))
            return success(result, "Account created."), 201
        if self.command == "POST" and path == "/api/v1/auth/login":
            payload = require_object(body)
            with self.server.db_lock:
                result = auth.login(require_string(payload, "email"), require_string(payload, "password", min_len=1, max_len=128))
            return success(result, "Authenticated."), 200
        if self.command == "POST" and path == "/api/v1/auth/refresh":
            payload = require_object(body)
            with self.server.db_lock:
                result = auth.refresh(require_string(payload, "refresh_token", min_len=20, max_len=4096))
            return success(result, "Token refreshed."), 200
        if self.command == "POST" and path == "/api/v1/auth/logout":
            payload = require_object(body) if body else {}
            with self.server.db_lock:
                user = self._optional_user(auth)
                result = auth.logout(payload.get("refresh_token"), user.get("id") if user else None)
            return success(result, "Logged out."), 200

        with self.server.db_lock:
            user = auth.authenticate(self.headers.get("Authorization"))
        audit = AuditRepository(self.server.conn)

        if self.command == "GET" and path == "/api/v1/me":
            return success(public_user(user)), 200
        if self.command == "POST" and path == "/api/v1/aura/message":
            payload = require_object(body)
            response = self.server.controller.process_user_message(require_string(payload, "message", max_len=8000))
            with self.server.db_lock:
                audit.record("aura.message", user["id"], {"success": response.success, "intent": response.intent}, request_id)
            return success(response.__dict__), 200
        if self.command == "GET" and path == "/api/v1/memories":
            return success(self.server.controller.list_memories()), 200
        if self.command == "POST" and path == "/api/v1/memories/forget":
            payload = require_object(body)
            response = self.server.controller.forget_memory(require_string(payload, "content", max_len=2000))
            with self.server.db_lock:
                audit.record("memory.forget", user["id"], {"success": response.success}, request_id)
            return success(response.__dict__), 200
        if self.command == "GET" and path == "/api/v1/dashboard/summary":
            return success({"providers": self.server.controller.provider_status(), "memory_count": len(self.server.controller.list_memories()), "recent_activity_count": len(self.server.controller.activities)}), 200
        if self.command == "GET" and path == "/api/v1/dashboard/activity":
            return success([item.__dict__ for item in self.server.controller.activities[:50]]), 200
        if self.command == "POST" and path == "/api/v1/weather/current":
            payload = require_object(body)
            return success(WeatherService().current_weather(str(payload.get("location", "")).strip() or None)), 200
        if self.command == "POST" and path == "/api/v1/web/search":
            payload = require_object(body)
            query = require_string(payload, "query", max_len=500)
            limit = int(payload.get("limit", 5) or 5)
            results = CompositeSearchProvider().search(query, max(1, min(limit, 10)))
            return success({"query": query, "results": [item.to_source(False) for item in results]}), 200
        raise ApiError(404, "NOT_FOUND", "Endpoint was not found.")

    def _json_body(self) -> Any:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > settings.max_body_bytes:
            raise ApiError(413, "PAYLOAD_TOO_LARGE", "Request body is too large.")
        if length == 0:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError(400, "BAD_JSON", "Request body must be valid JSON.") from exc

    def _optional_user(self, auth: AuthService) -> dict[str, Any] | None:
        try:
            return auth.authenticate(self.headers.get("Authorization"))
        except ApiError:
            return None

    def _send(self, status: int, payload: Any, request_id: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Access-Control-Allow-Origin", settings.cors_origin)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        if request_id:
            self.send_header("X-Request-ID", request_id)
        self.end_headers()
        if status == HTTPStatus.NO_CONTENT:
            return
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    server = AuraApiServer((settings.host, settings.port))
    LOGGER.info("AURA API listening on http://%s:%s", settings.host, settings.port)
    server.serve_forever()


if __name__ == "__main__":
    run()
