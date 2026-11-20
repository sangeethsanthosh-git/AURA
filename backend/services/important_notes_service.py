"""
AURA Important Notes Service (Phase V1 Email & Reminders)
Captures important user notes, key meeting points, or deadline information locally in SQLite.
Supports natural language triggers ("Save this as an important note", "This is important, email it to me",
"Send me this information tonight") and feeds into daily email summaries.
"""

import logging
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ImportantNotesService:
    """Manages persistent important notes in SQLite."""

    def __init__(self, db_path: str = "aura.db"):
        self.db_path = str(Path(db_path).resolve())
        self._init_db()

    def _init_db(self) -> None:
        """Create important_notes table in SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS important_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    created_at REAL NOT NULL,
                    emailed INTEGER NOT NULL DEFAULT 0,
                    emailed_at REAL,
                    status TEXT NOT NULL DEFAULT 'active'
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_important_notes_status ON important_notes(status, emailed);
                """
            )
            conn.commit()

    def add_note(self, content: str, category: str = "general", emailed: bool = False) -> Dict[str, Any]:
        """Save a new important note."""
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO important_notes (content, category, created_at, emailed, emailed_at, status)
                VALUES (?, ?, ?, ?, ?, 'active')
                """,
                (content.strip(), category, now, 1 if emailed else 0, now if emailed else None),
            )
            note_id = cur.lastrowid
            conn.commit()

        return {
            "id": note_id,
            "content": content.strip(),
            "category": category,
            "created_at": now,
            "emailed": emailed,
            "status": "active",
        }

    def list_notes(self, only_unemailed: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
        """List active important notes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if only_unemailed:
                cur.execute(
                    """
                    SELECT id, content, category, created_at, emailed, emailed_at, status
                    FROM important_notes
                    WHERE status = 'active' AND emailed = 0
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, content, category, created_at, emailed, emailed_at, status
                    FROM important_notes
                    WHERE status = 'active'
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            return [dict(row) for row in cur.fetchall()]

    def mark_emailed(self, note_ids: List[int]) -> None:
        """Mark a list of notes as emailed."""
        if not note_ids:
            return
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            placeholders = ",".join("?" for _ in note_ids)
            cur.execute(
                f"""
                UPDATE important_notes
                SET emailed = 1, emailed_at = ?
                WHERE id IN ({placeholders})
                """,
                [now] + note_ids,
            )
            conn.commit()

    def delete_note(self, note_id: int) -> bool:
        """Soft-delete an important note."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE important_notes SET status = 'deleted' WHERE id = ?",
                (note_id,),
            )
            conn.commit()
            return cur.rowcount > 0


# Global instance
important_notes_service = ImportantNotesService()
