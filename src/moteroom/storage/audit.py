"""The audit trail.

Somebody voided a ticket in March and nobody remembers why. The trail is
append only and it is written inside the same transaction as the change it
records, so a change that rolls back takes its own trail entry with it and
there is no entry for something that did not happen.

It records what was done and to what, never the whole record. A trail that
copies every field is a second book that drifts from the first.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from moteroom.core.errors import ValidationError
from moteroom.core.season import Season
from moteroom.storage.repository import Repository

MAX_DETAIL = 400


@dataclass(frozen=True)
class Entry:
    """One line of the trail."""

    at: datetime
    season: Season
    action: str
    subject: str
    detail: str

    def __str__(self) -> str:
        return f"{self.at.isoformat(sep=' ', timespec='seconds')} {self.action} {self.subject}"


class AuditRepository(Repository):
    """Everything that has written to this book."""

    def record(
        self, season: Season, action: str, subject: str, detail: str, at: datetime
    ) -> None:
        """Write one line, refusing anything that names nothing."""
        if not action.strip():
            raise ValidationError("action", "is blank")
        if not subject.strip():
            raise ValidationError("subject", "is blank")
        if len(detail) > MAX_DETAIL:
            raise ValidationError("detail", f"is longer than {MAX_DETAIL} characters")
        self.connection.execute(
            "INSERT INTO audit (at, season, action, subject, detail) VALUES (?, ?, ?, ?, ?)",
            (
                at.isoformat(timespec="seconds"),
                season.year,
                action.strip(),
                subject.strip(),
                detail,
            ),
        )

    def entries(self, season: Season, limit: int = 50) -> list[Entry]:
        """The most recent lines for a season, newest first."""
        if limit < 1:
            raise ValidationError("limit", "must be at least one")
        rows = self.rows(
            "SELECT at, season, action, subject, detail FROM audit WHERE season = ? "
            "ORDER BY id DESC LIMIT ?",
            (season.year, limit),
        )
        return [_entry(row) for row in rows]

    def for_subject(self, subject: str) -> list[Entry]:
        """Everything ever done to one thing, oldest first."""
        rows = self.rows(
            "SELECT at, season, action, subject, detail FROM audit WHERE subject = ? "
            "ORDER BY id",
            (subject,),
        )
        return [_entry(row) for row in rows]

    def actions(self, season: Season) -> dict[str, int]:
        """How many times each action was run, most used first."""
        rows = self.rows(
            "SELECT action, count(*) AS n FROM audit WHERE season = ? GROUP BY action",
            (season.year,),
        )
        counted = {str(row["action"]): int(row["n"]) for row in rows}
        return dict(sorted(counted.items(), key=lambda pair: (-pair[1], pair[0])))

    def count(self, season: Season) -> int:
        return self.scalar("SELECT count(*) FROM audit WHERE season = ?", (season.year,))


def _entry(row: sqlite3.Row) -> Entry:
    return Entry(
        at=datetime.fromisoformat(row["at"]),
        season=Season(int(row["season"])),
        action=str(row["action"]),
        subject=str(row["subject"]),
        detail=str(row["detail"]),
    )
