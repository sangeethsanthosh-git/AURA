"""Authentication and authorization service."""

from __future__ import annotations

import sqlite3
from datetime import timedelta
from typing import Any

from backend.api.config import settings
from backend.api.errors import ApiError
from backend.api.repositories import AuditRepository, SessionRepository, UserRepository
from backend.api.security import create_token, decode_token, hash_password, utcnow, verify_password
from backend.api.validators import validate_email, validate_password


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "display_name": user.get("display_name"),
        "email_verified": bool(user.get("email_verified")),
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


class AuthService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.users = UserRepository(conn)
        self.sessions = SessionRepository(conn)
        self.audit = AuditRepository(conn)

    def register(self, email: str, password: str, display_name: str | None = None) -> dict[str, Any]:
        email = validate_email(email)
        validate_password(password)
        if self.users.get_by_email(email):
            raise ApiError(409, "EMAIL_IN_USE", "An account already exists for that email.")
        user = self.users.create(email, hash_password(password), display_name)
        self.audit.record("auth.register", user["id"])
        return self._issue_pair(user)

    def login(self, email: str, password: str) -> dict[str, Any]:
        user = self.users.get_by_email(validate_email(email))
        if not user or not verify_password(password, user["password_hash"]):
            raise ApiError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
        self.audit.record("auth.login", user["id"])
        return self._issue_pair(user)

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        session = self.sessions.active_for_token(refresh_token)
        if not session:
            raise ApiError(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired.")
        user = self.users.get_by_id(session["user_id"])
        if not user:
            raise ApiError(401, "INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired.")
        self.sessions.revoke(refresh_token)
        self.audit.record("auth.refresh", user["id"])
        return self._issue_pair(user)

    def logout(self, refresh_token: str | None, user_id: str | None = None) -> dict[str, bool]:
        if refresh_token:
            self.sessions.revoke(refresh_token)
        self.audit.record("auth.logout", user_id)
        return {"logged_out": True}

    def authenticate(self, authorization: str | None) -> dict[str, Any]:
        if not authorization or not authorization.startswith("Bearer "):
            raise ApiError(401, "UNAUTHORIZED", "Bearer authentication is required.")
        claims = decode_token(authorization.removeprefix("Bearer ").strip(), settings.access_token_secret)
        user = self.users.get_by_id(str(claims.get("sub", "")))
        if not user:
            raise ApiError(401, "UNAUTHORIZED", "User no longer exists.")
        return user

    def require_role(self, user: dict[str, Any], roles: set[str]) -> None:
        if user.get("role") not in roles:
            raise ApiError(403, "FORBIDDEN", "Your account is not allowed to perform this action.")

    def _issue_pair(self, user: dict[str, Any]) -> dict[str, Any]:
        claims = {"sub": user["id"], "role": user["role"]}
        access = create_token(claims, settings.access_token_secret, timedelta(minutes=settings.access_token_minutes))
        refresh = create_token(claims, settings.refresh_token_secret, timedelta(days=settings.refresh_token_days))
        self.sessions.create(user["id"], refresh, utcnow() + timedelta(days=settings.refresh_token_days))
        return {
            "user": public_user(user),
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "Bearer",
            "expires_in": settings.access_token_minutes * 60,
        }

