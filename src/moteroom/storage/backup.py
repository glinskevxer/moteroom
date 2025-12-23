"""Copying the book and checking the copy.

The office keeps the season on one machine and copies it onto a stick at the
end of the week. Copying the file while something is writing to it produces a
file that opens fine and is missing a page, so the copy goes through sqlite's
own backup rather than through the filesystem.

A copy is only worth having if it was checked, so verifying is a separate step
that opens the copy and asks sqlite what it thinks of it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from moteroom.core.errors import ValidationError
from moteroom.storage.book import Book
from moteroom.storage.migrations import LATEST, current_version


@dataclass(frozen=True)
class Verdict:
    """What sqlite thinks of a book."""

    path: str
    integrity: str
    foreign_keys: int
    version: int
    tables: int

    @property
    def is_sound(self) -> bool:
        return self.integrity == "ok" and self.foreign_keys == 0 and self.version == LATEST

    def __str__(self) -> str:
        if self.is_sound:
            return f"{self.path} is sound at schema {self.version}, {self.tables} tables"
        return f"{self.path} is not sound: {self.integrity}, {self.foreign_keys} broken keys"


def backup(book: Book, target: Path) -> Path:
    """Copy an open book to a file, through sqlite rather than the filesystem."""
    if target.exists():
        raise ValidationError("target", f"{target} is already there")
    target.parent.mkdir(parents=True, exist_ok=True)
    copy = sqlite3.connect(str(target))
    try:
        book.connection.backup(copy)
    finally:
        copy.close()
    return target


def verify(path: Path) -> Verdict:
    """Open a book and ask sqlite whether it is intact."""
    if not path.exists():
        raise ValidationError("path", f"{path} is not there")
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        broken = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        version = current_version(connection)
        rows = connection.execute(
            "SELECT count(*) AS n FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchone()
        tables = int(rows["n"])
    finally:
        connection.close()
    return Verdict(str(path), integrity, broken, version, tables)


def restore(source: Path, target: Path) -> Path:
    """Put a checked copy back, refusing to write over a book already there."""
    verdict = verify(source)
    if not verdict.is_sound:
        raise ValidationError("source", f"{source} will not verify")
    if target.exists():
        raise ValidationError("target", f"{target} is already there")
    with Book.open(source) as opened:
        return backup(opened, target)
