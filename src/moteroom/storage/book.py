"""The book itself.

Everything the office keys in lands in one sqlite file. Opening it migrates it
forward, turns foreign keys on, and hands back a connection that returns rows
by name rather than by position, because a repository indexing columns by
number is a repository that breaks the next time a migration adds one.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from types import TracebackType
from typing import Self

from moteroom.storage.migrations import current_version, migrate

MEMORY = ":memory:"
BUSY_TIMEOUT_MS = 5_000


class Book:
    """An open book, with a transaction helper and nothing else clever."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @classmethod
    def open(cls, path: Path | str = MEMORY) -> Self:
        """Open or create a book and bring it up to date."""
        target = str(path)
        connection = sqlite3.connect(target)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
        migrate(connection)
        return cls(connection)

    @property
    def version(self) -> int:
        return current_version(self.connection)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run a unit of work, rolling the whole thing back if it raises."""
        with self.connection:
            yield self.connection

    def tables(self) -> list[str]:
        rows = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        )
        return [str(row["name"]) for row in rows if not str(row["name"]).startswith("sqlite_")]

    def count(self, table: str) -> int:
        if table not in self.tables():
            raise KeyError(table)
        row = self.connection.execute(f"SELECT count(*) AS n FROM {table}").fetchone()
        return int(row["n"])

    def analyse(self) -> None:
        """Let sqlite look at the tables and remember what it found.

        The planner guesses at row counts until somebody tells it. On a book
        with one lot in it that costs nothing either way, and on a book with a
        season in it the difference is a report that returns and one that
        walks every bale for every line.
        """
        self.connection.execute("ANALYZE")
        self.connection.commit()

    def close(self) -> None:
        """Close the book, letting sqlite tidy up on the way out."""
        with suppress(sqlite3.ProgrammingError):
            self.connection.execute("PRAGMA optimize")
        self.connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
