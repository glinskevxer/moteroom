from datetime import date
from pathlib import Path

import pytest

from moteroom.cli.context import DEFAULT_BOOK, Session
from moteroom.core.errors import ValidationError
from moteroom.core.season import Season

DAY = date(2025, 10, 14)


def test_the_default_book_is_a_file_in_the_working_folder():
    assert DEFAULT_BOOK.endswith(".sqlite3")


def test_a_session_takes_the_season_it_is_given_or_the_one_open():
    assert Session.build(":memory:", "2024", DAY).season == Season(2024)
    assert Session.build(":memory:", None, DAY).season == Season(2025)


def test_a_season_that_will_not_read():
    with pytest.raises(ValidationError):
        Session.build(":memory:", "cotton", DAY)


def test_a_session_opens_its_book_once(tmp_path: Path) -> None:
    session = Session.build(tmp_path / "season.sqlite3", "2025", DAY)
    assert session.book() is session.book()
    session.close()


def test_closing_twice_is_not_an_error(tmp_path: Path) -> None:
    session = Session.build(tmp_path / "season.sqlite3", "2025", DAY)
    session.book()
    session.close()
    session.close()


def test_a_book_in_memory_always_exists():
    session = Session.build(":memory:", "2025", DAY)
    assert session.exists()
    session.close()


def test_requiring_a_book_that_is_not_there(tmp_path: Path) -> None:
    session = Session.build(tmp_path / "none.sqlite3", "2025", DAY)
    with pytest.raises(ValidationError):
        session.require_book()


def test_the_repositories_come_off_the_open_book(tmp_path: Path) -> None:
    session = Session.build(tmp_path / "season.sqlite3", "2025", DAY)
    repos = session.repos()
    assert repos.producers.count() == 0
    assert session.open_repos().connection is repos.connection
    session.close()


def test_writing_rolls_back_when_it_raises(tmp_path: Path) -> None:
    session = Session.build(tmp_path / "season.sqlite3", "2025", DAY)
    session.book()
    with pytest.raises(ValueError), session.writing() as repos:
        repos.connection.execute("INSERT INTO producers VALUES ('BLYTHE', 'Blythe Farms')")
        raise ValueError("no")
    assert session.repos().producers.count() == 0
    session.close()


def test_writing_makes_the_book_when_it_is_told_to(tmp_path: Path) -> None:
    path = tmp_path / "season.sqlite3"
    session = Session.build(path, "2025", DAY)
    with session.writing(make=True) as repos:
        assert repos.producers.count() == 0
    assert path.exists()
    session.close()


def test_the_trail_records_through_the_session(tmp_path: Path) -> None:
    session = Session.build(tmp_path / "season.sqlite3", "2025", DAY)
    session.book()
    session.record("weigh", "HW-004181", "ticket 1")
    assert session.repos().audit.count(Season(2025)) == 1
    session.close()
