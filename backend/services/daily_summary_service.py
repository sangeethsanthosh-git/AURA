"""
AURA Daily Summary Service (Phase V1 Email Notifications)
Compiles upcoming reminders, deadlines, and saved important notes into a daily email digest.
Delivers automatically at the user's configured morning time (default: 08:00) using the background scheduler,
with zero continuous LLM polling.
"""

from datetime import datetime, date
import logging
from typing import Any, Dict, List, Optional

from backend.services.email_service import email_service
from backend.services.important_notes_service import important_notes_service
from backend.services.reminder_service import reminder_service

logger = logging.getLogger(__name__)


class DailySummaryService:
    """Orchestrates daily morning summaries of reminders and important notes."""

    def check_and_send_daily_summary(self) -> Optional[Dict[str, Any]]:
        """
        Called periodically by the background scheduler loop.
        Checks if the daily summary is enabled, matches the configured time, and hasn't been sent today.
        """
        if not email_service.is_enabled() or not email_service.get_daily_summary_enabled():
            return None

        if not email_service.is_connected():
            return None

        target_time_str = email_service.get_daily_summary_time() or "08:00"
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")

        # Check if the minute matches
        if current_time_str != target_time_str:
            return None

        # Check if already sent today
        today_str = date.today().isoformat()
        last_sent = email_service.get_setting("daily_summary_last_sent_date")
        if last_sent == today_str:
            return None

        # Execute daily summary delivery
        logger.info(f"Triggering scheduled daily summary email for {today_str} at {current_time_str}")
        res = self.send_summary_now()
        if res.get("success"):
            email_service.set_setting("daily_summary_last_sent_date", today_str)
        return res

    def send_summary_now(self, to_email: Optional[str] = None) -> Dict[str, Any]:
        """Compile and send the daily summary digest immediately."""
        target = to_email or email_service.get_destination_email()
        if not target:
            return {"success": False, "error": "No destination email configured."}

        # 1. Fetch active reminders
        active_reminders = reminder_service.list_active()

        # 2. Fetch pending important notes
        notes = important_notes_service.list_notes(only_unemailed=True, limit=20)
        if not notes:
            # Fallback to recent notes
            notes = important_notes_service.list_notes(limit=10)

        # Build text & HTML bodies
        today_formatted = datetime.now().strftime("%A, %B %d, %Y")
        subject = f"🌅 AURA Daily Summary & Reminders – {today_formatted}"

        text_lines = [
            f"Good morning! Here is your AURA Daily Summary for {today_formatted}.",
            "",
            "==================================================",
            "⏰ UPCOMING REMINDERS & DEADLINES",
            "==================================================",
        ]

        if active_reminders:
            for r in active_reminders[:10]:
                rec_str = f" [Recurs: {r['recurrence']}]" if r.get("recurrence") else ""
                text_lines.append(f"• {r['title']}{rec_str}")
        else:
            text_lines.append("• No pending reminders scheduled for today.")

        text_lines.extend([
            "",
            "==================================================",
            "📝 IMPORTANT NOTES & SAVED INFORMATION",
            "==================================================",
        ])

        if notes:
            for n in notes[:10]:
                text_lines.append(f"• {n['content']}")
        else:
            text_lines.append("• No new notes saved.")

        text_lines.extend([
            "",
            "Have a productive day!",
            "Sent from your AURA Desktop Assistant.",
        ])

        body_text = "\n".join(text_lines)

        # Build rich HTML email
        reminders_html = "".join([
            f"<li style='margin-bottom: 8px;'><strong>{r['title']}</strong>"
            f"<span style='color: #64748b; font-size: 13px;'>{' (' + r['recurrence'] + ')' if r.get('recurrence') else ''}</span></li>"
            for r in active_reminders[:10]
        ]) if active_reminders else "<li style='color: #94a3b8;'>No pending reminders scheduled for today.</li>"

        notes_html = "".join([
            f"<li style='margin-bottom: 8px; color: #334155;'>{n['content']}</li>"
            for n in notes[:10]
        ]) if notes else "<li style='color: #94a3b8;'>No new notes saved.</li>"

        body_html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 580px; margin: 0 auto; padding: 28px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
            <div style="border-bottom: 2px solid #f1f5f9; padding-bottom: 16px; margin-bottom: 24px;">
                <h2 style="color: #0f172a; margin: 0 0 6px 0; font-size: 20px;">🌅 AURA Daily Summary</h2>
                <span style="color: #64748b; font-size: 14px;">{today_formatted}</span>
            </div>

            <div style="margin-bottom: 24px;">
                <h3 style="color: #4f46e5; margin: 0 0 12px 0; font-size: 16px; display: flex; align-items: center;">
                    ⏰ Upcoming Reminders & Deadlines
                </h3>
                <ul style="margin: 0; padding-left: 20px; color: #1e293b; font-size: 14px; line-height: 1.6;">
                    {reminders_html}
                </ul>
            </div>

            <div style="margin-bottom: 24px;">
                <h3 style="color: #0ea5e9; margin: 0 0 12px 0; font-size: 16px;">
                    📝 Important Notes & Information
                </h3>
                <ul style="margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.6;">
                    {notes_html}
                </ul>
            </div>

            <div style="border-top: 1px solid #f1f5f9; padding-top: 16px; margin-top: 28px; text-align: center; color: #94a3b8; font-size: 12px;">
                Generated locally by your AURA Desktop Assistant &bull; Offline Privacy First
            </div>
        </div>
        """

        res = email_service.send_email(
            to_email=target,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

        if res.get("success"):
            # Mark the notes as emailed
            note_ids = [n["id"] for n in notes]
            important_notes_service.mark_emailed(note_ids)

        return res


# Global instance
daily_summary_service = DailySummaryService()
