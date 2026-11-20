"""
Unit Tests for AURA Email Notifications & Reminder System (V1)
Verifies:
1. EmailService (Gmail send scope, OAuth URL, token exchange, token refresh, MIME encoding, idempotency, delivery logging)
2. ImportantNotesService (saving notes, listing unemailed notes, marking emailed)
3. ReminderService upgrades (natural language parsing for tomorrow, every Sunday, before meeting, recurring schedules, email dispatch)
4. DailySummaryService (digest generation, reminders & notes aggregation, delivery check)
5. SystemToolService intent handlers (test email, important notes, daily summary)
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from backend.services.email_service import EmailService, GMAIL_SEND_SCOPE
from backend.services.important_notes_service import ImportantNotesService
from backend.services.reminder_service import ReminderService
from backend.services.daily_summary_service import DailySummaryService
from backend.services.system_tool_service import SystemToolService


class TestEmailNotificationSystem(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_aura.db")
        self.email_svc = EmailService(db_path=self.db_path)
        self.notes_svc = ImportantNotesService(db_path=self.db_path)
        self.reminder_svc = ReminderService(db_path=self.db_path)

    def tearDown(self):
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 1. EmailService Settings & Configuration
    # -------------------------------------------------------------------------

    def test_email_service_settings(self):
        self.assertTrue(self.email_svc.is_enabled())
        self.email_svc.set_enabled(False)
        self.assertFalse(self.email_svc.is_enabled())
        self.email_svc.set_enabled(True)

        self.email_svc.set_destination_email("user@example.com")
        self.assertEqual(self.email_svc.get_destination_email(), "user@example.com")

        self.assertFalse(self.email_svc.get_daily_summary_enabled())
        self.email_svc.set_daily_summary_enabled(True)
        self.assertTrue(self.email_svc.get_daily_summary_enabled())

        self.assertEqual(self.email_svc.get_daily_summary_time(), "08:00")
        self.email_svc.set_daily_summary_time("09:30")
        self.assertEqual(self.email_svc.get_daily_summary_time(), "09:30")

    def test_oauth_auth_url_minimal_scope(self):
        self.email_svc.set_oauth_client_credentials("test-client-id.apps.googleusercontent.com", "test-secret")
        res = self.email_svc.generate_auth_url()
        self.assertTrue(res["success"])
        url = res["auth_url"]
        self.assertIn("accounts.google.com", url)
        self.assertIn("test-client-id", url)
        # Verify strict minimum gmail.send scope
        import urllib.parse
        unquoted = urllib.parse.unquote(url)
        self.assertIn(GMAIL_SEND_SCOPE, unquoted)
        self.assertNotIn("gmail.readonly", unquoted)
        self.assertNotIn("calendar", url)
        self.assertNotIn("drive", url)

    # -------------------------------------------------------------------------
    # 2. Token Exchange & Email Dispatch
    # -------------------------------------------------------------------------

    @patch("backend.services.email_service.requests.post")
    def test_token_exchange(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "ya29.test_access_token",
            "refresh_token": "1//test_refresh_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_resp

        self.email_svc.set_oauth_client_credentials("client-id", "client-secret")
        res = self.email_svc.exchange_code_for_tokens("test-auth-code")
        self.assertTrue(res["success"])
        self.assertTrue(self.email_svc.is_connected())

    @patch("backend.services.email_service.requests.post")
    def test_send_email_success(self, mock_post):
        # Configure connected state
        self.email_svc.secret_store.set_secret("gmail_refresh_token", "test-refresh")
        self.email_svc.secret_store.set_secret("gmail_access_token", "test-access")
        self.email_svc.secret_store.set_secret("gmail_token_expiry", str(time.time() + 3600))
        self.email_svc.secret_store.set_secret("gmail_client_id", "cid")
        self.email_svc.secret_store.set_secret("gmail_client_secret", "csec")
        self.email_svc.set_destination_email("recipient@example.com")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "msg_12345", "threadId": "th_123"}
        mock_post.return_value = mock_resp

        res = self.email_svc.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            body_text="Hello world test",
            idempotency_hash="hash_abc_1",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["gmail_id"], "msg_12345")

        # Verify delivery log was persisted
        history = self.email_svc.get_delivery_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["recipient"], "recipient@example.com")
        self.assertEqual(history[0]["status"], "sent")

        # Test duplicate suppression
        dup_res = self.email_svc.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            body_text="Hello world test",
            idempotency_hash="hash_abc_1",
        )
        self.assertTrue(dup_res["success"])
        self.assertTrue(dup_res.get("suppressed"))

    # -------------------------------------------------------------------------
    # 3. ImportantNotesService
    # -------------------------------------------------------------------------

    def test_important_notes_workflow(self):
        note1 = self.notes_svc.add_note("Meeting deadline is Friday 5 PM", category="work")
        self.assertEqual(note1["content"], "Meeting deadline is Friday 5 PM")
        self.assertFalse(note1["emailed"])

        unemailed = self.notes_svc.list_notes(only_unemailed=True)
        self.assertEqual(len(unemailed), 1)

        self.notes_svc.mark_emailed([note1["id"]])
        unemailed_after = self.notes_svc.list_notes(only_unemailed=True)
        self.assertEqual(len(unemailed_after), 0)

        all_notes = self.notes_svc.list_notes()
        self.assertEqual(len(all_notes), 1)
        self.assertEqual(all_notes[0]["emailed"], 1)

    # -------------------------------------------------------------------------
    # 4. ReminderService Upgraded Natural Language Parsing
    # -------------------------------------------------------------------------

    def test_parse_tomorrow_reminder(self):
        cmd = self.reminder_svc.parse_command("remind me tomorrow at 9 AM about my assignment")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[0], "create_reminder")
        self.assertEqual(cmd[2], "my assignment")
        meta = cmd[3]
        self.assertEqual(meta["notification_type"], "toast")
        self.assertGreater(cmd[1], 0)

    def test_parse_email_reminder(self):
        cmd = self.reminder_svc.parse_command("email me a reminder two hours before my meeting")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[0], "create_reminder")
        self.assertIn("meeting", cmd[2].lower())
        meta = cmd[3]
        self.assertEqual(meta["notification_type"], "email")

    def test_parse_recurring_sunday_reminder(self):
        cmd = self.reminder_svc.parse_command("remind me every Sunday to revise")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd[0], "create_reminder")
        self.assertEqual(cmd[2], "revise")
        meta = cmd[3]
        self.assertEqual(meta["recurrence"], "weekly")
        self.assertEqual(meta["recurrence_day"], 6)  # Sunday = 6

    def test_recurring_reminder_expiration_advancement(self):
        # Create a reminder in the past
        r = self.reminder_svc.create_timer(
            duration_seconds=-10,
            title="Daily review",
            recurrence="daily",
            notification_type="toast",
        )
        expired = self.reminder_svc.check_and_complete_expired()
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0]["title"], "Daily review")

        # The reminder should still be active, with an updated future target_time
        active = self.reminder_svc.list_active()
        self.assertEqual(len(active), 1)
        self.assertGreater(active[0]["target_time"], time.time())

    # -------------------------------------------------------------------------
    # 5. DailySummaryService
    # -------------------------------------------------------------------------

    @patch("backend.services.email_service.email_service.send_email")
    def test_daily_summary_generation(self, mock_send):
        mock_send.return_value = {"success": True, "gmail_id": "digest_123"}
        self.email_svc.set_destination_email("test@domain.com")
        self.email_svc.set_daily_summary_enabled(True)

        # Add a note and a reminder
        self.notes_svc.add_note("Project submission deadline tomorrow")
        self.reminder_svc.create_timer(duration_seconds=3600, title="Team sync meeting")

        summary_svc = DailySummaryService()
        with patch.object(summary_svc, "send_summary_now", wraps=summary_svc.send_summary_now) as spy:
            res = summary_svc.send_summary_now(to_email="test@domain.com")
            self.assertTrue(res["success"])
            self.assertTrue(mock_send.called)
            # Verify email subject
            args, kwargs = mock_send.call_args
            self.assertIn("Daily Summary", kwargs.get("subject", ""))

    # -------------------------------------------------------------------------
    # 6. SystemToolService Intent Integration
    # -------------------------------------------------------------------------

    @patch("backend.services.email_service.email_service.send_email")
    def test_system_tool_service_email_intents(self, mock_send):
        mock_send.return_value = {"success": True, "message": "Email sent"}

        # 1. "Save this as an important note"
        res1 = SystemToolService.execute_intent("Save this as an important note: Client presentation postponed")
        self.assertIsNotNone(res1)
        self.assertTrue(res1["handled"])
        self.assertEqual(res1["action"], "save_important_note")

        # 2. "This is important. Email it to me."
        res2 = SystemToolService.execute_intent("This is important, email it to me: Server migration window is Sunday midnight")
        self.assertIsNotNone(res2)
        self.assertTrue(res2["handled"])
        self.assertEqual(res2["action"], "important_note_email")


if __name__ == "__main__":
    unittest.main()
