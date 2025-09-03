"""What every repository in this package has in common.

Ten repositories were each holding a connection, each wrapping a write in the
same try block to turn a sqlite integrity error into a conflict, and each
reading a count with the same four lines. That is not ten decisions, it is one
decision written ten times, so it lives here and the repositories say what is
actually different about them.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterable, Sequence
from typing import Any

ConflictNamer = Callable[[], Exception]


class Repository:
    """A table, a connection and the handful of things every table needs."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def one(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        """The first row a query returns, or nothing."""
        row: sqlite3.Row | None = self.connection.execute(sql, tuple(params)).fetchone()
        return row

    def rows(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        """Every row a query returns, read out before anything else runs."""
        return self.connection.execute(sql, tuple(params)).fetchall()

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> int:
        """A single number off a query, which is nothing when there are no rows."""
        row = self.one(sql, params)
        if row is None or row[0] is None:
            return 0
        return int(row[0])

    def exists(self, sql: str, params: Sequence[Any] = ()) -> bool:
        return self.one(sql, params) is not None

    def write(self, sql: str, params: Sequence[Any], on_conflict: ConflictNamer) -> None:
        """Run a write, turning a constraint into an error that names the record."""
        try:
            self.connection.execute(sql, tuple(params))
        except sqlite3.IntegrityError as exc:
            raise on_conflict() from exc

    def write_many(
        self, sql: str, rows: Iterable[Sequence[Any]], on_conflict: ConflictNamer
    ) -> None:
        try:
            self.connection.executemany(sql, [tuple(row) for row in rows])
        except sqlite3.IntegrityError as exc:
            raise on_conflict() from exc

    def changed(self, sql: str, params: Sequence[Any] = ()) -> int:
        """How many rows a statement touched, which is how an update reports."""
        return int(self.connection.execute(sql, tuple(params)).rowcount)
