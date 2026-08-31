"""Repository layer for API persistence."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime
from typing import Any

from backend.api.security import iso, utcnow


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


class UserRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, email: str, password_hash: str, display_name: str | None, role: str = "USER") -> dict[str, Any]:
        now = iso(utcnow())
        user_id = secrets.token_urlsafe(16)
        self.conn.execute(
            "INSERT INTO users(id,email,password_hash,role,display_name,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (user_id, email.lower(), password_hash, role, display_name, now, now),
        )
        self.conn.commit()
        return self.get_by_id(user_id) or {}

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        return _row(self.conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone())

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        return _row(self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())


class SessionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @staticmethod
    def digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(self, user_id: str, refresh_token: str, expires_at: datetime) -> None:
        self.conn.execute(
            "INSERT INTO refresh_sessions(id,user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?,?)",
            (secrets.token_urlsafe(16), user_id, self.digest(refresh_token), iso(expires_at), iso(utcnow())),
        )
        self.conn.commit()

    def active_for_token(self, refresh_token: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM refresh_sessions WHERE token_hash = ? AND revoked_at IS NULL",
            (self.digest(refresh_token),),
        ).fetchone()
        item = _row(row)
        if not item:
            return None
        if datetime.fromisoformat(item["expires_at"]) <= utcnow():
            return None
        return item

    def revoke(self, refresh_token: str) -> None:
        self.conn.execute(
            "UPDATE refresh_sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
            (iso(utcnow()), self.digest(refresh_token)),
        )
        self.conn.commit()


class AuditRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def record(self, action: str, user_id: str | None = None, metadata: dict[str, Any] | None = None, request_id: str | None = None) -> None:
        self.conn.execute(
            "INSERT INTO audit_logs(id,user_id,action,metadata,request_id,created_at) VALUES(?,?,?,?,?,?)",
            (secrets.token_urlsafe(16), user_id, action, json.dumps(metadata or {}), request_id, iso(utcnow())),
        )
        self.conn.commit()

