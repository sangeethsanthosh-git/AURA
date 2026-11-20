"""
Reminder & Timer Service (Phase 10: Reminders, Timers & Windows Notifications)
Upgraded for Phase V1 Email Notifications & Reminder System.
Manages persistent countdown timers and reminders in SQLite, provides natural language
parsing for voice/text timer and email reminder commands (e.g., "remind me tomorrow at 9 AM about my assignment",
"email me a reminder two hours before my meeting", "remind me every Sunday to revise"),
and fires Windows toast notifications, earcon chimes, and Gmail email notifications on completion.
"""

from datetime import datetime, timedelta
import hashlib
import logging
import re
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ReminderService:
    """Manages active timers and scheduled reminders with local SQLite persistence and email dispatch."""

    def __init__(self, db_path: str = "aura.db"):
        self.db_path = str(Path(db_path).resolve())
        self._init_db()

    def _init_db(self) -> None:
        """Initialize reminders table in SQLite and perform safe schema migrations."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    target_time REAL NOT NULL,
                    duration_seconds REAL NOT NULL,
                    is_timer INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at REAL NOT NULL,
                    notification_type TEXT NOT NULL DEFAULT 'toast',
                    recurrence TEXT,
                    recurrence_day INTEGER,
                    email_to TEXT,
                    last_sent_at REAL,
                    idempotency_hash TEXT
                )
                """
            )
            # Safe schema migrations for existing databases
            columns_to_add = [
                ("notification_type", "TEXT NOT NULL DEFAULT 'toast'"),
                ("recurrence", "TEXT"),
                ("recurrence_day", "INTEGER"),
                ("email_to", "TEXT"),
                ("last_sent_at", "REAL"),
                ("idempotency_hash", "TEXT"),
            ]
            for col_name, col_def in columns_to_add:
                try:
                    cur.execute(f"ALTER TABLE reminders ADD COLUMN {col_name} {col_def}")
                except sqlite3.OperationalError:
                    pass

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status, target_time);
                """
            )
            conn.commit()

    # -------------------------------------------------------------------------
    # Natural Language Parsing
    # -------------------------------------------------------------------------

    def parse_command(self, text: str) -> Optional[Tuple[str, float, str, Dict[str, Any]]]:
        """
        Parse user command for timer/reminder action.
        Returns: (action_type, duration_seconds, title, metadata)
        action_type: 'create_timer' | 'create_reminder' | 'cancel_all' | 'cancel_id' | 'list'
        """
        t = text.lower().strip()

        # Cancel commands
        if re.search(r"\b(cancel|stop|clear|delete)\s+(all\s+)?(timers?|reminders?)\b", t):
            return ("cancel_all", 0.0, "", {})

        # Cancel specific ID
        m_cancel_id = re.search(r"\b(cancel|delete|stop)\s+(?:timer|reminder)\s+#?(\d+)\b", t)
        if m_cancel_id:
            return ("cancel_id", 0.0, "", {"id": int(m_cancel_id.group(2))})

        # List commands
        if re.search(r"\b(list|show|check|what are)\s+(?:my\s+)?(timers?|reminders?)\b", t):
            return ("list", 0.0, "", {})

        # Check if email is explicitly requested
        is_email = bool(re.search(r"\b(email|mail|send\s+(?:an?\s+)?email)\b", t))
        notification_type = "email" if is_email else "toast"

        # Check for recurrence: "every Sunday", "every day", "daily", "every weekday"
        recurrence = None
        recurrence_day = None
        m_rec = re.search(r"\bevery\s+(sunday|monday|tuesday|wednesday|thursday|friday|saturday|day|weekday|week|month)\b", t)
        if m_rec:
            unit = m_rec.group(1)
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            if unit in days:
                recurrence = "weekly"
                recurrence_day = days.index(unit)
            elif unit == "day":
                recurrence = "daily"
            elif unit == "weekday":
                recurrence = "weekdays"
            elif unit == "week":
                recurrence = "weekly"
            elif unit == "month":
                recurrence = "monthly"

        # Pattern: "remind me every Sunday to <title>"
        if recurrence:
            m_rec_title = re.search(r"\b(?:remind\s+(?:me\s+)?|email\s+(?:me\s+)?)(?:every\s+\w+\s+)?(?:to|about)\s+(.+)$", t)
            title = m_rec_title.group(1).strip() if m_rec_title else "Scheduled Task"
            target_time = self._compute_next_recurrence_time(recurrence, recurrence_day)
            dur = max(1.0, target_time - time.time())
            return (
                "create_reminder",
                dur,
                title,
                {
                    "notification_type": notification_type,
                    "recurrence": recurrence,
                    "recurrence_day": recurrence_day,
                    "target_time": target_time,
                },
            )

        # Pattern: "remind me tomorrow at <time> (to/about <title>)?"
        # Pattern: "remind me at <time> (tomorrow)? (to/about <title>)?"
        m_clock = re.search(
            r"\b(?:remind|email)\s+(?:me\s+)?(?:(tomorrow)\s+)?at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?(?:\s+(tomorrow))?(?:\s+(?:to|about)\s+(.+))?\b",
            t,
        )
        if m_clock:
            is_tomorrow = bool(m_clock.group(1) or m_clock.group(5))
            hour = int(m_clock.group(2))
            minute = int(m_clock.group(3) or 0)
            ampm = (m_clock.group(4) or "").lower()
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            title = (m_clock.group(6) or "Reminder").strip()

            target_dt = self._compute_target_datetime(hour, minute, force_tomorrow=is_tomorrow)
            target_time = target_dt.timestamp()
            dur = max(1.0, target_time - time.time())
            return (
                "create_reminder",
                dur,
                title,
                {
                    "notification_type": notification_type,
                    "target_time": target_time,
                    "recurrence": None,
                },
            )

        # Pattern: "remind me <X> <unit> before <event>" (e.g. "email me a reminder two hours before my meeting")
        m_before = re.search(
            r"\b(?:email|remind)\s+(?:me\s+)?(?:a\s+reminder\s+)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(hour|hours|minute|minutes)\s+before\s+(.+)$",
            t,
        )
        if m_before:
            amount_str = m_before.group(1)
            word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
            amount = float(word_to_num.get(amount_str, amount_str if amount_str.isdigit() else 1))
            unit = m_before.group(2)
            event_title = m_before.group(3).strip()
            secs = self._unit_to_seconds(amount, unit)
            # Default to firing in (secs) for relative test
            title = f"Upcoming: {event_title}"
            return (
                "create_reminder",
                secs,
                title,
                {
                    "notification_type": notification_type,
                    "recurrence": None,
                },
            )

        # Pattern 1: "remind me to <title> in <X> <unit>"
        m1 = re.search(
            r"\bremind\s+(?:me\s+)?to\s+(.+?)\s+in\s+(\d+(?:\.\d+)?)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours)\b",
            t,
        )
        if m1:
            title = m1.group(1).strip()
            amount = float(m1.group(2))
            unit = m1.group(3)
            secs = self._unit_to_seconds(amount, unit)
            return ("create_timer", secs, title, {"notification_type": notification_type})

        # Pattern 2: "timer for <X> <unit> (to <title>)?"
        m2 = re.search(
            r"\b(?:set\s+(?:a\s+)?)?timer\s+(?:for\s+)?(\d+(?:\.\d+)?)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours)(?:\s+(?:for|to)\s+(.+))?\b",
            t,
        )
        if m2:
            amount = float(m2.group(1))
            unit = m2.group(2)
            title = (m2.group(3) or "Timer").strip()
            secs = self._unit_to_seconds(amount, unit)
            return ("create_timer", secs, title, {"notification_type": "toast"})

        # Pattern 3: "remind me in <X> <unit> to <title>"
        m3 = re.search(
            r"\bremind\s+(?:me\s+)?in\s+(\d+(?:\.\d+)?)\s*(s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours)(?:\s+to\s+(.+))?\b",
            t,
        )
        if m3:
            amount = float(m3.group(1))
            unit = m3.group(2)
            title = (m3.group(3) or "Reminder").strip()
            secs = self._unit_to_seconds(amount, unit)
            return ("create_timer", secs, title, {"notification_type": notification_type})

        # Pattern 4: "email me about <title>"
        m4 = re.search(r"\b(?:send\s+me\s+an?\s+email|email\s+me)\s+(?:about|for)\s+(.+)$", t)
        if m4:
            title = m4.group(1).strip()
            # Set default 1 hour reminder or immediate
            return ("create_reminder", 3600.0, title, {"notification_type": "email"})

        return None

    def _compute_target_datetime(self, hour: int, minute: int, force_tomorrow: bool = False) -> datetime:
        """Calculate target datetime for hour:minute, pushing to tomorrow if already passed."""
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if force_tomorrow or target <= now:
            target += timedelta(days=1)
        return target

    def _compute_next_recurrence_time(self, recurrence: str, recurrence_day: Optional[int] = None) -> float:
        """Compute the next Unix timestamp for a recurring schedule."""
        now = datetime.now()
        if recurrence == "daily":
            target = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            return target.timestamp()
        elif recurrence == "weekly" and recurrence_day is not None:
            days_ahead = (recurrence_day - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            target = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
            return target.timestamp()
        elif recurrence == "weekdays":
            target = now + timedelta(days=1)
            while target.weekday() >= 5:  # Saturday or Sunday
                target += timedelta(days=1)
            target = target.replace(hour=9, minute=0, second=0, microsecond=0)
            return target.timestamp()
        elif recurrence == "monthly":
            target = (now + timedelta(days=30)).replace(hour=9, minute=0, second=0, microsecond=0)
            return target.timestamp()
        return (now + timedelta(days=1)).timestamp()

    def _unit_to_seconds(self, amount: float, unit: str) -> float:
        """Convert time unit string to seconds."""
        unit = unit.lower()
        if unit.startswith("s"):
            return amount
        elif unit.startswith("m"):
            return amount * 60.0
        elif unit.startswith("h"):
            return amount * 3600.0
        return amount

    # -------------------------------------------------------------------------
    # Creation & Management
    # -------------------------------------------------------------------------

    def create_timer(
        self,
        duration_seconds: float,
        title: str = "Timer",
        is_timer: bool = True,
        notification_type: str = "toast",
        recurrence: Optional[str] = None,
        recurrence_day: Optional[int] = None,
        email_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new countdown timer or reminder in database."""
        now = time.time()
        target_time = now + duration_seconds
        idem_hash = hashlib.sha256(f"{title}_{target_time}_{notification_type}".encode("utf-8")).hexdigest()[:16]

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO reminders (
                    title, target_time, duration_seconds, is_timer, status, created_at,
                    notification_type, recurrence, recurrence_day, email_to, idempotency_hash
                )
                VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    target_time,
                    duration_seconds,
                    1 if is_timer else 0,
                    now,
                    notification_type,
                    recurrence,
                    recurrence_day,
                    email_to,
                    idem_hash,
                ),
            )
            timer_id = cur.lastrowid
            conn.commit()

        logger.info(f"Created reminder #{timer_id}: '{title}' (target: {target_time}, type: {notification_type})")
        return {
            "id": timer_id,
            "title": title,
            "target_time": target_time,
            "duration_seconds": duration_seconds,
            "remaining_seconds": duration_seconds,
            "status": "active",
            "is_timer": is_timer,
            "notification_type": notification_type,
            "recurrence": recurrence,
            "email_to": email_to,
        }

    def list_active(self) -> List[Dict[str, Any]]:
        """List all currently active countdown timers and scheduled reminders."""
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, title, target_time, duration_seconds, is_timer, status, created_at,
                       notification_type, recurrence, email_to
                FROM reminders
                WHERE status = 'active'
                ORDER BY target_time ASC
                """
            )
            rows = cur.fetchall()

        results = []
        for r in rows:
            remaining = max(0.0, r["target_time"] - now)
            results.append({
                "id": r["id"],
                "title": r["title"],
                "target_time": r["target_time"],
                "duration_seconds": r["duration_seconds"],
                "remaining_seconds": round(remaining, 1),
                "status": r["status"],
                "is_timer": bool(r["is_timer"]),
                "notification_type": r["notification_type"],
                "recurrence": r["recurrence"],
                "email_to": r["email_to"],
            })
        return results

    def cancel_timer(self, timer_id: int) -> bool:
        """Cancel an active timer by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE reminders SET status = 'cancelled' WHERE id = ? AND status = 'active'", (timer_id,))
            affected = cur.rowcount
            conn.commit()
        return affected > 0

    cancel_reminder = cancel_timer

    def cancel_all(self) -> int:
        """Cancel all active timers."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE reminders SET status = 'cancelled' WHERE status = 'active'")
            affected = cur.rowcount
            conn.commit()
        return affected

    # -------------------------------------------------------------------------
    # Background Scheduler & Expiration Dispatch
    # -------------------------------------------------------------------------

    def check_and_complete_expired(self) -> List[Dict[str, Any]]:
        """
        Check for any timers or scheduled reminders whose target_time has passed.
        If recurring, advances to next recurrence timestamp and keeps active.
        If one-time, marks status as 'completed'.
        Dispatches email notifications if configured.
        """
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, title, target_time, duration_seconds, is_timer, created_at,
                       notification_type, recurrence, recurrence_day, email_to, idempotency_hash
                FROM reminders
                WHERE status = 'active' AND target_time <= ?
                """,
                (now,),
            )
            rows = cur.fetchall()
            if not rows:
                return []

            for r in rows:
                rid = r["id"]
                rec = r["recurrence"]
                rec_day = r["recurrence_day"]
                if rec:
                    # Advance to next scheduled recurrence
                    next_target = self._compute_next_recurrence_time(rec, rec_day)
                    cur.execute(
                        """
                        UPDATE reminders
                        SET target_time = ?, last_sent_at = ?
                        WHERE id = ?
                        """,
                        (next_target, now, rid),
                    )
                else:
                    cur.execute(
                        "UPDATE reminders SET status = 'completed', last_sent_at = ? WHERE id = ?",
                        (now, rid),
                    )
            conn.commit()

        expired = []
        for r in rows:
            item = {
                "id": r["id"],
                "title": r["title"],
                "duration_seconds": r["duration_seconds"],
                "is_timer": bool(r["is_timer"]),
                "notification_type": r["notification_type"],
                "recurrence": r["recurrence"],
                "email_to": r["email_to"],
                "idempotency_hash": r["idempotency_hash"],
            }
            expired.append(item)
            logger.info(f"Reminder #{r['id']} '{r['title']}' expired! Type: {r['notification_type']}")

            # Send Email if configured for email notification
            if r["notification_type"] in ("email", "both"):
                self._dispatch_email_notification(item)

        return expired

    def _dispatch_email_notification(self, reminder: Dict[str, Any]) -> None:
        """Helper to send email notification for an expired reminder."""
        try:
            from backend.services.email_service import email_service
            title = reminder.get("title", "Scheduled Reminder")
            to_addr = reminder.get("email_to")
            idempotency_hash = reminder.get("idempotency_hash")

            subject = f"⏰ AURA Reminder: {title}"
            body_text = (
                f"Hello!\n\n"
                f"This is your scheduled reminder from AURA:\n\n"
                f"• {title}\n\n"
                f"Scheduled delivery: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n"
            )
            email_service.send_email(
                to_email=to_addr,
                subject=subject,
                body_text=body_text,
                idempotency_hash=idempotency_hash,
            )
        except Exception as e:
            logger.error(f"Failed to dispatch email reminder for #{reminder.get('id')}: {e}")

    def send_windows_toast(self, title: str, message: str) -> None:
        """Display native Windows Toast Notification."""
        script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $textNodes = $template.GetElementsByTagName("text")
        $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
        $textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("AURA Assistant")
        $notifier.Show($toast)
        """
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=si,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as e:
            logger.debug(f"Could not fire Windows Toast: {e}")

    def execute_command(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Parse natural language command and execute the corresponding reminder action."""
        parsed = self.parse_command(prompt)
        if not parsed:
            return None

        cmd_type = parsed[0]
        if cmd_type in ("create_timer", "create_reminder"):
            secs, title = parsed[1], parsed[2]
            meta = parsed[3] if len(parsed) > 3 else {}
            notif_type = meta.get("notification_type", "toast")
            recurrence = meta.get("recurrence")
            recurrence_day = meta.get("recurrence_day")

            res = self.create_timer(
                secs,
                title=title,
                is_timer=(cmd_type == "create_timer"),
                notification_type=notif_type,
                recurrence=recurrence,
                recurrence_day=recurrence_day,
            )
            formatted_time = (
                f"{int(secs)} seconds"
                if secs < 60
                else f"{int(secs // 60)} minute{'s' if secs >= 120 else ''}"
            )
            rec_str = f" every {recurrence}" if recurrence else ""
            notif_str = " via email" if notif_type == "email" else ""
            spoken = f"I've set a reminder for {title}{rec_str}{notif_str}."
            return {
                "handled": True,
                "action": "create",
                "title": f"Reminder Set: {title}",
                "message": f"Active: {title}{rec_str} ({formatted_time})",
                "spoken_response": spoken,
                "data": res,
            }
        elif cmd_type in ("list", "list_timers"):
            active = self.list_active()
            if not active:
                return {
                    "handled": True,
                    "action": "list",
                    "title": "No Active Reminders",
                    "message": "You don't have any active timers or reminders right now.",
                    "spoken_response": "You don't have any active timers or reminders right now.",
                    "data": {"count": 0, "timers": []},
                }
            timer_names = [f"#{t['id']} {t['title']} ({int(t['remaining_seconds'])}s left)" for t in active]
            spoken = f"You have {len(active)} active item{'s' if len(active) > 1 else ''}: {', '.join(timer_names)}."
            return {
                "handled": True,
                "action": "list",
                "title": f"Active Reminders ({len(active)})",
                "message": ", ".join(timer_names),
                "spoken_response": spoken,
                "data": {"count": len(active), "timers": active},
            }
        elif cmd_type == "cancel_id":
            tid = parsed[3].get("id")
            ok = self.cancel_timer(tid)
            msg = f"Cancelled reminder #{tid}." if ok else f"Reminder #{tid} not found or already ended."
            return {
                "handled": True,
                "action": "cancel",
                "title": "Reminder Cancelled" if ok else "Reminder Not Found",
                "message": msg,
                "spoken_response": msg,
                "data": {"id": tid, "success": ok},
            }
        elif cmd_type == "cancel_all":
            count = self.cancel_all()
            msg = f"Cancelled all {count} active reminders."
            return {
                "handled": True,
                "action": "cancel",
                "title": "All Reminders Cancelled",
                "message": msg,
                "spoken_response": msg,
                "data": {"cancelled_count": count},
            }
        return None


# Global instance
reminder_service = ReminderService()
