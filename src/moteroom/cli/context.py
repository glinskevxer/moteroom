"""What every command needs before it can do anything.

One book, one season, and a way to open the book once rather than in every
command. The season is resolved when the session is made, so a command that
runs over midnight on the first of August still works against the season it
started in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from moteroom.core.errors import ValidationError
from moteroom.core.season import Season
from moteroom.storage.book import Book

DEFAULT_BOOK = "moteroom.sqlite3"


@dataclass
class Session:
    """The open book and the season the commands are working in."""

    book_path: Path
    season: Season
    _book: Book | None = field(default=None, repr=False)

    @classmethod
    def build(cls, book_path: Path | str, season: str | None, today: date) -> Session:
        """Make a session, reading the season off the argument or off the date."""
        resolved = Season.parse(season) if season else Season.for_date(today)
        return cls(Path(book_path), resolved)

    def book(self) -> Book:
        if self._book is None:
            self._book = Book.open(self.book_path)
        return self._book

    def exists(self) -> bool:
        return self.book_path.exists() or str(self.book_path) == ":memory:"

    def require_book(self) -> Book:
        """Open a book that has to be there already."""
        if not self.exists():
            raise ValidationError("book", f"{self.book_path} does not exist yet")
        return self.book()

    def close(self) -> None:
        if self._book is not None:
            self._book.close()
            self._book = None
