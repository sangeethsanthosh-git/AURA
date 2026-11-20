"""
AURA Email Service (V1)
Lightweight email notification system using the official Gmail REST API with the minimal
'https://www.googleapis.com/auth/gmail.send' OAuth scope.
Handles OAuth authentication, secure token storage via SecretStore, token refresh,
MIME RFC 2822 formatting, test emails, and delivery audit logging in SQLite.
"""

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import logging
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional
import urllib.parse

import requests

from backend.security.secret_store import SecretStore

logger = logging.getLogger(__name__)

# Minimum scope strictly limited to sending emails (no inbox reading, calendar, drive, etc.)
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_SEND_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"


class EmailService:
    """Manages Gmail API credentials, sending notifications, and tracking delivery history."""

    def __init__(self, db_path: str = "aura.db"):
        self.db_path = str(Path(db_path).resolve())
        self.secret_store = SecretStore()
        self._init_db()

    def _init_db(self) -> None:
        """Create email_logs and email_settings tables if they do not exist."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'sent',
                    error_message TEXT,
                    idempotency_hash TEXT,
                    sent_at REAL NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS email_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_email_logs_sent ON email_logs(sent_at DESC);
                """
            )
            conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetch a persistent setting from SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM email_settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Store a persistent setting in SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO email_settings (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
            conn.commit()

    # -------------------------------------------------------------------------
    # Settings & Status
    # -------------------------------------------------------------------------

    def is_enabled(self) -> bool:
        """Master toggle for email notifications."""
        val = self.get_setting("email_notifications_enabled", "true")
        return val.lower() in ("true", "1", "yes")

    def set_enabled(self, enabled: bool) -> None:
        self.set_setting("email_notifications_enabled", "true" if enabled else "false")

    def get_destination_email(self) -> Optional[str]:
        return self.get_setting("destination_email", "")

    def set_destination_email(self, email: str) -> None:
        self.set_setting("destination_email", email.strip())

    def get_daily_summary_enabled(self) -> bool:
        val = self.get_setting("daily_summary_enabled", "false")
        return val.lower() in ("true", "1", "yes")

    def set_daily_summary_enabled(self, enabled: bool) -> None:
        self.set_setting("daily_summary_enabled", "true" if enabled else "false")

    def get_daily_summary_time(self) -> str:
        return self.get_setting("daily_summary_time", "08:00")

    def set_daily_summary_time(self, time_str: str) -> None:
        self.set_setting("daily_summary_time", time_str.strip())

    def is_connected(self) -> bool:
        """Returns True if a Gmail refresh token is securely stored."""
        token = self.secret_store.get_secret("gmail_refresh_token")
        return bool(token and len(token) > 5)

    def get_connected_email(self) -> Optional[str]:
        """Returns the authenticated Google account email, if known."""
        return self.get_setting("gmail_connected_account", "")

    def get_status(self) -> Dict[str, Any]:
        """Aggregate configuration and authentication status for the UI."""
        return {
            "is_connected": self.is_connected(),
            "connected_account": self.get_connected_email(),
            "destination_email": self.get_destination_email(),
            "notifications_enabled": self.is_enabled(),
            "daily_summary_enabled": self.get_daily_summary_enabled(),
            "daily_summary_time": self.get_daily_summary_time(),
            "has_client_credentials": bool(
                self.secret_store.get_secret("gmail_client_id")
                and self.secret_store.get_secret("gmail_client_secret")
            ),
        }

    # -------------------------------------------------------------------------
    # OAuth Authentication Flow
    # -------------------------------------------------------------------------

    def set_oauth_client_credentials(self, client_id: str, client_secret: str) -> None:
        """Store Google OAuth Client ID and Secret in secure local SecretStore."""
        self.secret_store.set_secret("gmail_client_id", client_id.strip())
        self.secret_store.set_secret("gmail_client_secret", client_secret.strip())

    def get_oauth_client_id(self) -> Optional[str]:
        return self.secret_store.get_secret("gmail_client_id")

    def get_oauth_client_secret(self) -> Optional[str]:
        return self.secret_store.get_secret("gmail_client_secret")

    def generate_auth_url(self, redirect_uri: str = "http://127.0.0.1:8000/api/email/oauth/callback") -> Dict[str, Any]:
        """Generate Google OAuth consent URL requesting minimal gmail.send permission."""
        client_id = self.get_oauth_client_id()
        if not client_id:
            return {
                "success": False,
                "error": "Google OAuth Client ID is not configured. Please provide Client ID in Settings.",
            }

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GMAIL_SEND_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
        url = f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"
        return {"success": True, "auth_url": url}

    def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str = "http://127.0.0.1:8000/api/email/oauth/callback",
    ) -> Dict[str, Any]:
        """Exchange one-time authorization code for access and refresh tokens."""
        client_id = self.get_oauth_client_id()
        client_secret = self.get_oauth_client_secret()

        if not client_id or not client_secret:
            return {"success": False, "error": "Missing OAuth client credentials"}

        try:
            resp = requests.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=10,
            )
            data = resp.json()
            if resp.status_code != 200 or "error" in data:
                err_desc = data.get("error_description", data.get("error", "Token exchange failed"))
                logger.error(f"OAuth token exchange error: {err_desc}")
                return {"success": False, "error": err_desc}

            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 3600)
            expiry_timestamp = time.time() + float(expires_in) - 60

            if access_token:
                self.secret_store.set_secret("gmail_access_token", access_token)
                self.secret_store.set_secret("gmail_token_expiry", str(expiry_timestamp))

            if refresh_token:
                self.secret_store.set_secret("gmail_refresh_token", refresh_token)

            # Try to fetch user's email profile using token
            user_email = self._fetch_user_email(access_token)
            if user_email:
                self.set_setting("gmail_connected_account", user_email)
                if not self.get_destination_email():
                    self.set_destination_email(user_email)

            return {
                "success": True,
                "connected_account": user_email or "Connected",
                "message": "Gmail account successfully connected.",
            }
        except Exception as e:
            logger.error(f"Error during OAuth code exchange: {e}")
            return {"success": False, "error": str(e)}

    def _fetch_user_email(self, access_token: str) -> Optional[str]:
        """Fetch profile email using userinfo endpoint or tokeninfo."""
        try:
            resp = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
            if resp.status_code == 200:
                return resp.json().get("email")
        except Exception:
            pass
        return None

    def refresh_access_token(self) -> Optional[str]:
        """Refresh and return a valid access token using the stored refresh token."""
        refresh_token = self.secret_store.get_secret("gmail_refresh_token")
        client_id = self.get_oauth_client_id()
        client_secret = self.get_oauth_client_secret()

        if not refresh_token or not client_id or not client_secret:
            return None

        # Check existing token expiry
        exp_str = self.secret_store.get_secret("gmail_token_expiry")
        current_access = self.secret_store.get_secret("gmail_access_token")
        if exp_str and current_access:
            try:
                if float(exp_str) > time.time() + 60:
                    return current_access
            except ValueError:
                pass

        try:
            resp = requests.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=10,
            )
            data = resp.json()
            if resp.status_code == 200 and "access_token" in data:
                new_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self.secret_store.set_secret("gmail_access_token", new_token)
                self.secret_store.set_secret("gmail_token_expiry", str(time.time() + expires_in - 60))
                return new_token
            else:
                logger.error(f"Token refresh failed: {data}")
                return None
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None

    def disconnect(self) -> Dict[str, Any]:
        """Revoke / disconnect connected Gmail account and clear stored tokens."""
        self.secret_store.set_secret("gmail_access_token", "")
        self.secret_store.set_secret("gmail_refresh_token", "")
        self.secret_store.set_secret("gmail_token_expiry", "0")
        self.set_setting("gmail_connected_account", "")
        return {"success": True, "message": "Gmail account disconnected."}

    # -------------------------------------------------------------------------
    # Email Delivery (Gmail REST API)
    # -------------------------------------------------------------------------

    def send_email(
        self,
        to_email: Optional[str] = None,
        subject: str = "AURA Notification",
        body_text: str = "",
        body_html: Optional[str] = None,
        idempotency_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends an email via the official Gmail API (POST https://gmail.googleapis.com/gmail/v1/users/me/messages/send).
        Payload is encoded as base64url RFC 2822 MIME message.
        """
        if not self.is_enabled():
            return {"success": False, "error": "Email notifications are disabled in settings."}

        target = to_email or self.get_destination_email()
        if not target or "@" not in target:
            return {"success": False, "error": "No valid destination email configured."}

        # Check duplicate idempotency hash within last 1 hour
        if idempotency_hash:
            if self._is_duplicate(idempotency_hash):
                logger.info(f"Duplicate email suppressed for idempotency hash: {idempotency_hash}")
                return {"success": True, "suppressed": True, "message": "Duplicate email suppressed."}

        access_token = self.refresh_access_token()
        if not access_token:
            err = "Gmail account is not connected or token could not be refreshed."
            self._log_delivery(target, subject, status="failed", error=err, idempotency_hash=idempotency_hash)
            return {"success": False, "error": err}

        # Build RFC 2822 MIME Message
        msg = MIMEMultipart("alternative")
        msg["To"] = target
        sender = self.get_connected_email() or "me"
        msg["From"] = f"AURA Desktop Assistant <{sender}>"
        msg["Subject"] = subject

        # Plaintext fallback
        msg.attach(MIMEText(body_text or "", "plain", "utf-8"))

        # HTML body
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        else:
            # Default clean styled HTML
            html_content = self._format_default_html(subject, body_text)
            msg.attach(MIMEText(html_content, "html", "utf-8"))

        raw_bytes = msg.as_bytes()
        raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("ascii")

        try:
            resp = requests.post(
                GMAIL_SEND_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"raw": raw_b64},
                timeout=12,
            )

            if resp.status_code in (200, 202):
                data = resp.json()
                msg_id = data.get("id")
                logger.info(f"Email sent successfully to {target}. Gmail Message ID: {msg_id}")
                self._log_delivery(target, subject, status="sent", idempotency_hash=idempotency_hash)
                return {
                    "success": True,
                    "recipient": target,
                    "subject": subject,
                    "gmail_id": msg_id,
                    "message": f"Email successfully sent to {target}.",
                }
            else:
                err_text = resp.text
                logger.error(f"Gmail send API error ({resp.status_code}): {err_text}")
                self._log_delivery(target, subject, status="failed", error=err_text, idempotency_hash=idempotency_hash)
                return {
                    "success": False,
                    "error": f"Gmail API error ({resp.status_code}): {err_text}",
                }
        except Exception as e:
            logger.error(f"Exception sending email: {e}")
            self._log_delivery(target, subject, status="failed", error=str(e), idempotency_hash=idempotency_hash)
            return {"success": False, "error": str(e)}

    def send_test_email(self, to_email: Optional[str] = None) -> Dict[str, Any]:
        """Send a test notification to verify Gmail integration."""
        target = to_email or self.get_destination_email()
        subject = "✨ AURA Test Email Notification"
        text = (
            "Hello from AURA!\n\n"
            "This is a test notification confirming that your Gmail integration and destination email "
            "are working properly.\n\n"
            "You can now receive scheduled reminders, important notes, and daily summaries."
        )
        html = (
            "<div style='font-family: sans-serif; max-width: 520px; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fafafa;'>"
            "<h2 style='color: #4f46e5; margin-top: 0;'>✨ AURA Desktop Assistant</h2>"
            "<p style='font-size: 15px; color: #334155; line-height: 1.6;'>This is a test notification confirming that your Gmail integration and email destination are functioning properly!</p>"
            "<div style='background: #fff; padding: 14px 18px; border-radius: 8px; border-left: 4px solid #4f46e5; margin: 18px 0;'>"
            "<strong style='color: #1e293b;'>Ready for:</strong>"
            "<ul style='margin: 8px 0 0 18px; padding: 0; color: #475569; font-size: 14px;'>"
            "<li>Scheduled & recurring reminders</li>"
            "<li>Saved important notes</li>"
            "<li>Daily morning summaries</li>"
            "</ul>"
            "</div>"
            "<p style='font-size: 12px; color: #94a3b8; margin-bottom: 0;'>Sent securely from your local AURA desktop assistant.</p>"
            "</div>"
        )
        return self.send_email(to_email=target, subject=subject, body_text=text, body_html=html)

    def _format_default_html(self, title: str, text: str) -> str:
        """Create clean responsive HTML card for notifications."""
        escaped_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
        return (
            "<div style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif; max-width: 540px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;'>"
            f"<h3 style='color: #0f172a; margin-top: 0; margin-bottom: 12px; font-size: 18px;'>{title}</h3>"
            f"<div style='font-size: 15px; color: #334155; line-height: 1.6; background-color: #f8fafc; padding: 16px; border-radius: 8px; border-left: 4px solid #3b82f6;'>{escaped_text}</div>"
            "<hr style='border: none; border-top: 1px solid #f1f5f9; margin: 20px 0;'/>"
            "<div style='font-size: 12px; color: #94a3b8; text-align: right;'>AURA Desktop Assistant &bull; Local Notification</div>"
            "</div>"
        )

    def _is_duplicate(self, idempotency_hash: str) -> bool:
        """Check if an email with the same idempotency hash was sent within the past 1 hour."""
        one_hour_ago = time.time() - 3600
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM email_logs WHERE idempotency_hash = ? AND status = 'sent' AND sent_at > ?",
                (idempotency_hash, one_hour_ago),
            )
            return cur.fetchone() is not None

    def _log_delivery(
        self,
        recipient: str,
        subject: str,
        status: str = "sent",
        error: Optional[str] = None,
        idempotency_hash: Optional[str] = None,
    ) -> None:
        """Record email delivery in SQLite log table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO email_logs (recipient, subject, status, error_message, idempotency_hash, sent_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (recipient, subject, status, error, idempotency_hash, time.time()),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging email delivery: {e}")

    def get_delivery_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent email delivery logs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, recipient, subject, status, error_message, sent_at
                FROM email_logs
                ORDER BY sent_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]


# Global singleton instance
email_service = EmailService()
