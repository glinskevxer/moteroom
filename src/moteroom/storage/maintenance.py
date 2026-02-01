"""Keeping the book a reasonable size.

A season's book grows all autumn and then stops. Deleting nothing is the right
default, so it only ever grows, and the pages a voided ticket used are not
handed back until somebody asks. Compacting is that asking.

Sizes are reported in pages as well as bytes, because the page count is what
tells you whether compacting will do anything: a book with no free pages is
already as small as it goes and vacuuming it just rewrites the file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from moteroom.core.errors import ValidationError
from moteroom.storage.book import Book

BYTES_IN_KB = 1024


@dataclass(frozen=True)
class Size:
    """How big a book is and how much of it is empty."""

    path: str
    bytes: int
    pages: int
    free_pages: int
    page_size: int

    @property
    def free_bytes(self) -> int:
        return self.free_pages * self.page_size

    @property
    def worth_compacting(self) -> bool:
        """Whether there is enough free space in it to bother."""
        return self.pages > 0 and self.free_pages * 10 >= self.pages

    def reads(self) -> str:
        """The size the way somebody says it out loud."""
        if self.bytes < BYTES_IN_KB:
            return f"{self.bytes} bytes"
        if self.bytes < BYTES_IN_KB * BYTES_IN_KB:
            return f"{self.bytes / BYTES_IN_KB:.1f} kB"
        return f"{self.bytes / (BYTES_IN_KB * BYTES_IN_KB):.1f} MB"

    def __str__(self) -> str:
        return f"{self.path} {self.reads()}, {self.free_pages} of {self.pages} pages free"


def measure(book: Book, path: Path) -> Size:
    """Read a book's size off the file and off sqlite's own counters."""
    if not path.exists():
        raise ValidationError("path", f"{path} is not there")
    pages = int(book.connection.execute("PRAGMA page_count").fetchone()[0])
    free = int(book.connection.execute("PRAGMA freelist_count").fetchone()[0])
    page_size = int(book.connection.execute("PRAGMA page_size").fetchone()[0])
    return Size(str(path), path.stat().st_size, pages, free, page_size)


def compact(book: Book, path: Path) -> tuple[Size, Size]:
    """Vacuum the book, returning the size before and after."""
    before = measure(book, path)
    book.connection.execute("VACUUM")
    book.connection.commit()
    return before, measure(book, path)


def table_sizes(book: Book) -> dict[str, int]:
    """Rows per table, biggest first, which is where the size went."""
    counted = {table: book.count(table) for table in book.tables()}
    return dict(sorted(counted.items(), key=lambda pair: (-pair[1], pair[0])))
