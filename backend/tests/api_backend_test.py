"""Regression tests for the REST API backend layer."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.auth import AuthService
from backend.api.database import connect, migrate
from backend.api.errors import ApiError
from backend.api.repositories import AuditRepository, UserRepository
from backend.api.security import decode_token


class ApiBackendTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self.tmp.name) / "test.sqlite3")
        migrate(self.conn)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_register_hashes_password_and_returns_public_user(self) -> None:
        result = AuthService(self.conn).register("User@Example.com", "pass1234!", "User")
        self.assertIn("access_token", result)
        self.assertNotIn("password_hash", result["user"])
        stored = UserRepository(self.conn).get_by_email("user@example.com")
        self.assertIsNotNone(stored)
        self.assertNotEqual(stored["password_hash"], "pass1234!")

    def test_login_rejects_invalid_password(self) -> None:
        auth = AuthService(self.conn)
        auth.register("user@example.com", "pass1234!", None)
        with self.assertRaises(ApiError) as raised:
            auth.login("user@example.com", "wrong")
        self.assertEqual(raised.exception.status, 401)

    def test_refresh_tokens_are_rotated(self) -> None:
        auth = AuthService(self.conn)
        first = auth.register("user@example.com", "pass1234!", None)
        second = auth.refresh(first["refresh_token"])
        self.assertNotEqual(first["refresh_token"], second["refresh_token"])
        with self.assertRaises(ApiError):
            auth.refresh(first["refresh_token"])

    def test_access_token_authenticates_user(self) -> None:
        auth = AuthService(self.conn)
        result = auth.register("user@example.com", "pass1234!", None)
        user = auth.authenticate(f"Bearer {result['access_token']}")
        self.assertEqual(user["email"], "user@example.com")

    def test_audit_log_is_persisted(self) -> None:
        AuditRepository(self.conn).record("test.action", metadata={"ok": True}, request_id="req")
        row = self.conn.execute("SELECT action, request_id FROM audit_logs").fetchone()
        self.assertEqual(row["action"], "test.action")
        self.assertEqual(row["request_id"], "req")


if __name__ == "__main__":
    unittest.main()
