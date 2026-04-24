from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Optional


@dataclass
class ReadingStats:
    total_pages: int
    total_entries: int
    pages_today: int
    streak_days: int
    current_book: Optional[str]


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        if self.db_path.parent:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS reading_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    book TEXT NOT NULL,
                    pages INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reminders (
                    user_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    time_local TEXT NOT NULL,
                    timezone TEXT NOT NULL DEFAULT 'UTC',
                    message TEXT NOT NULL,
                    last_sent_date TEXT
                );
                """
            )

            # Lightweight migration for earlier schema versions.
            cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(reminders)").fetchall()
            }
            if "time_local" not in cols and "time_utc" in cols:
                conn.execute("ALTER TABLE reminders RENAME COLUMN time_utc TO time_local")
            if "timezone" not in cols:
                conn.execute("ALTER TABLE reminders ADD COLUMN timezone TEXT NOT NULL DEFAULT 'UTC'")

    def add_reading_log(self, user_id: str, book: str, pages: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO reading_logs (user_id, book, pages, created_at) VALUES (?, ?, ?, ?)",
                (user_id, book, pages, now),
            )

    def get_reading_stats(self, user_id: str) -> ReadingStats:
        today = datetime.now(timezone.utc).date().isoformat()

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(pages), 0) AS total_pages,
                    COUNT(*) AS total_entries
                FROM reading_logs
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            today_row = conn.execute(
                """
                SELECT COALESCE(SUM(pages), 0) AS pages_today
                FROM reading_logs
                WHERE user_id = ? AND DATE(created_at) = ?
                """,
                (user_id, today),
            ).fetchone()

            latest_book_row = conn.execute(
                """
                SELECT book
                FROM reading_logs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

            day_rows = conn.execute(
                """
                SELECT DISTINCT DATE(created_at) AS reading_day
                FROM reading_logs
                WHERE user_id = ?
                ORDER BY reading_day DESC
                """,
                (user_id,),
            ).fetchall()

        streak_days = self._calculate_streak([r["reading_day"] for r in day_rows])

        return ReadingStats(
            total_pages=int(row["total_pages"]),
            total_entries=int(row["total_entries"]),
            pages_today=int(today_row["pages_today"]),
            streak_days=streak_days,
            current_book=latest_book_row["book"] if latest_book_row else None,
        )

    def _calculate_streak(self, days_desc: list[str]) -> int:
        if not days_desc:
            return 0

        today = datetime.now(timezone.utc).date()
        parsed_days = [datetime.fromisoformat(d).date() for d in days_desc]

        if parsed_days[0] == today:
            expected = today
        elif parsed_days[0] == today.fromordinal(today.toordinal() - 1):
            expected = today.fromordinal(today.toordinal() - 1)
        else:
            return 0

        streak = 0
        for day in parsed_days:
            if day == expected:
                streak += 1
                expected = expected.fromordinal(expected.toordinal() - 1)
            elif day > expected:
                continue
            else:
                break
        return streak

    def set_reminder(
        self,
        user_id: str,
        channel_id: str,
        time_local: str,
        timezone: str,
        message: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO reminders (user_id, channel_id, time_local, timezone, message, last_sent_date)
                VALUES (?, ?, ?, ?, ?, NULL)
                ON CONFLICT(user_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    time_local = excluded.time_local,
                    timezone = excluded.timezone,
                    message = excluded.message
                """,
                (user_id, channel_id, time_local, timezone, message),
            )

    def get_all_reminders(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT user_id, channel_id, time_local, timezone, message, last_sent_date
                FROM reminders
                """,
            ).fetchall()

    def clear_reminder(self, user_id: str) -> bool:
        with self._connect() as conn:
            result = conn.execute(
                "DELETE FROM reminders WHERE user_id = ?",
                (user_id,),
            )
            return result.rowcount > 0

    def mark_reminder_sent(self, user_id: str, date_iso: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE reminders SET last_sent_date = ? WHERE user_id = ?",
                (date_iso, user_id),
            )
