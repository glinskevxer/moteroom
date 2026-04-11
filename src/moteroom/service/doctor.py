"""Everything that can be checked about a book, in one pass.

The office manager opens the book in the morning and wants one answer: is
anything wrong. Not a report of the season, not a list of exceptions in the
cotton, but whether the book itself is sound and set up to be used. Missing
settings, unposted rates, a schema older than this build, a bale nobody can
place, receipts that do not line up with the press.

Each check is separate and each one either passes or says what to do about it.
Nothing here writes, so it is safe to run on a copy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from moteroom.core.season import Season
from moteroom.service import closing, inventory
from moteroom.storage.backup import verify
from moteroom.storage.book import Book
from moteroom.storage.migrations import LATEST
from moteroom.storage.registry import Repositories
from moteroom.storage.settings import KNOWN

WRONG = "wrong"
MISSING = "missing"
FINE = "fine"


@dataclass(frozen=True)
class Note:
    """One thing looked at, and what to do if it is not right."""

    check: str
    state: str
    detail: str

    @property
    def is_fine(self) -> bool:
        return self.state == FINE

    def __str__(self) -> str:
        return f"{self.state:<7} {self.check}: {self.detail}"


def look(book: Book, season: Season, path: Path | None, as_of: date) -> list[Note]:
    """Look at everything and say what is not right."""
    repos = Repositories(book.connection)
    notes = [
        _schema(book),
        _settings(repos),
        _rates(repos, season),
        _placed(book, season),
        _closing(book, season),
        _store(book, as_of),
    ]
    if path is not None and path.exists():
        notes.insert(0, _file(path))
    return notes


def _file(path: Path) -> Note:
    verdict = verify(path)
    if verdict.is_sound:
        return Note("file", FINE, f"{verdict.tables} tables, {verdict.integrity}")
    return Note("file", WRONG, str(verdict))


def _schema(book: Book) -> Note:
    if book.version == LATEST:
        return Note("schema", FINE, f"at {LATEST}")
    return Note("schema", WRONG, f"at {book.version} and this build makes {LATEST}")


def _settings(repos: Repositories) -> Note:
    missing = repos.settings.missing()
    if not missing:
        return Note("settings", FINE, f"all {len(KNOWN)} set")
    return Note("settings", MISSING, f"{', '.join(missing)} not set")


def _rates(repos: Repositories, season: Season) -> Note:
    if repos.rates.posted(season):
        return Note("rates", FINE, f"posted for {season}")
    return Note("rates", MISSING, f"nothing posted for {season}, the defaults would be used")


def _placed(book: Book, season: Season) -> Note:
    taken = inventory.take(book, season)
    if taken.balances:
        return Note("bales", FINE, str(taken))
    return Note("bales", WRONG, f"{len(taken.orphans)} do not add up")


def _closing(book: Book, season: Season) -> Note:
    made = closing.check(book, season)
    if made.can_close:
        return Note("season", FINE, "nothing outstanding")
    names = ", ".join(one.name for one in made.outstanding)
    return Note("season", MISSING, f"{names} still open")


def _store(book: Book, as_of: date) -> Note:
    """Bales sitting in store, which is somebody paying storage on them."""
    repos = Repositories(book.connection)
    held = [one for one in repos.receipts.outstanding() if one.received_on <= as_of]
    if not held:
        return Note("store", FINE, "nothing in store")
    oldest = min(one.days_stored(as_of) for one in held)
    longest = max(one.days_stored(as_of) for one in held)
    return Note(
        "store",
        FINE,
        f"{len(held)} bales in store, {oldest} to {longest} days",
    )


def worst(notes: list[Note]) -> str:
    """The worst state anything reached, which is what a status line prints."""
    if any(note.state == WRONG for note in notes):
        return WRONG
    if any(note.state == MISSING for note in notes):
        return MISSING
    return FINE


def is_sound(notes: list[Note]) -> bool:
    """Whether anything is actually wrong, as against merely unfinished."""
    return not any(note.state == WRONG for note in notes)
