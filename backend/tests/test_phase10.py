import time
import unittest
from pathlib import Path
from backend.services.reminder_service import ReminderService


class TestPhase10Reminders(unittest.TestCase):
    def setUp(self):
        self.test_db = "backend/data/test_reminders.db"
        self.service = ReminderService(db_path=self.test_db)

    def tearDown(self):
        test_db_path = Path(self.test_db)
        if test_db_path.exists():
            try:
                test_db_path.unlink()
            except Exception:
                pass

    def test_01_parse_timer_commands(self):
        cmd1 = self.service.parse_command("set a timer for 5 minutes")
        self.assertIsNotNone(cmd1)
        self.assertEqual(cmd1[0], "create_timer")
        self.assertEqual(cmd1[1], 300.0)

        cmd2 = self.service.parse_command("remind me to stretch in 30 seconds")
        self.assertIsNotNone(cmd2)
        self.assertEqual(cmd2[0], "create_timer")
        self.assertEqual(cmd2[1], 30.0)
        self.assertEqual(cmd2[2], "stretch")

        cmd3 = self.service.parse_command("cancel all timers")
        self.assertIsNotNone(cmd3)
        self.assertEqual(cmd3[0], "cancel_all")

        cmd4 = self.service.parse_command("show my timers")
        self.assertIsNotNone(cmd4)
        self.assertEqual(cmd4[0], "list")

    def test_02_create_and_expire_timer(self):
        timer = self.service.create_timer(duration_seconds=0.1, title="Quick Test")
        self.assertEqual(timer["status"], "active")

        # Wait for expiration
        time.sleep(0.15)
        expired = self.service.check_and_complete_expired()
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0]["title"], "Quick Test")

        # Now active list should be empty
        active = self.service.list_active()
        self.assertEqual(len(active), 0)

    def test_03_cancel_timer(self):
        timer = self.service.create_timer(duration_seconds=60.0, title="Long Timer")
        cancelled = self.service.cancel_timer(timer["id"])
        self.assertTrue(cancelled)

        active = self.service.list_active()
        self.assertEqual(len(active), 0)


if __name__ == "__main__":
    unittest.main()
