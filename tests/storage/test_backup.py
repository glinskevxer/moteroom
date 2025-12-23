import sqlite3
from pathlib import Path

import pytest

from moteroom.core.errors import ValidationError
from moteroom.receiving.party import Producer
from moteroom.storage.backup import backup, restore, verify
from moteroom.storage.book import Book
from moteroom.storage.migrations import LATEST
from moteroom.storage.producers import ProducerRepository


def seeded(path: Path) -> Book:
    book = Book.open(path)
    ProducerRepository(book.connection).add(Producer("BLYTHE", "Blythe Farms"))
    book.connection.commit()
    return book


def test_a_backup_carries_the_rows(tmp_path):
    book = seeded(tmp_path / "season.sqlite3")
    copy = backup(book, tmp_path / "copy.sqlite3")
    book.close()
    with Book.open(copy) as reopened:
        assert ProducerRepository(reopened.connection).count() == 1


def test_a_backup_will_not_write_over_something(tmp_path):
    book = seeded(tmp_path / "season.sqlite3")
    backup(book, tmp_path / "copy.sqlite3")
    with pytest.raises(ValidationError):
        backup(book, tmp_path / "copy.sqlite3")
    book.close()


def test_a_backup_makes_the_folder_it_needs(tmp_path):
    book = seeded(tmp_path / "season.sqlite3")
    copy = backup(book, tmp_path / "sticks" / "copy.sqlite3")
    assert copy.exists()
    book.close()


def test_a_good_book_verifies(tmp_path):
    path = tmp_path / "season.sqlite3"
    seeded(path).close()
    verdict = verify(path)
    assert verdict.is_sound
    assert verdict.version == LATEST
    assert verdict.tables > 10
    assert "is sound" in str(verdict)


def test_a_book_that_is_not_there(tmp_path):
    with pytest.raises(ValidationError):
        verify(tmp_path / "none.sqlite3")


def test_a_book_from_an_older_schema_is_not_sound(tmp_path):
    path = tmp_path / "old.sqlite3"
    connection = sqlite3.connect(str(path))
    connection.execute("PRAGMA user_version = 1")
    connection.close()
    verdict = verify(path)
    assert not verdict.is_sound
    assert "not sound" in str(verdict)


def test_a_restore_puts_a_checked_copy_back(tmp_path):
    source = tmp_path / "season.sqlite3"
    seeded(source).close()
    put = restore(source, tmp_path / "restored.sqlite3")
    with Book.open(put) as reopened:
        assert ProducerRepository(reopened.connection).count() == 1


def test_a_restore_will_not_write_over_a_book(tmp_path):
    source = tmp_path / "season.sqlite3"
    seeded(source).close()
    target = tmp_path / "restored.sqlite3"
    restore(source, target)
    with pytest.raises(ValidationError):
        restore(source, target)


def test_a_restore_refuses_a_copy_that_will_not_verify(tmp_path):
    source = tmp_path / "old.sqlite3"
    connection = sqlite3.connect(str(source))
    connection.execute("PRAGMA user_version = 1")
    connection.close()
    with pytest.raises(ValidationError):
        restore(source, tmp_path / "restored.sqlite3")
