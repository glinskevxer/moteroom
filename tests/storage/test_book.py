import pytest

from moteroom.storage.book import Book
from moteroom.storage.migrations import LATEST


def test_a_new_book_opens_at_the_latest_version():
    with Book.open() as book:
        assert book.version == LATEST


def test_a_book_on_disc_survives_being_closed(tmp_path):
    path = tmp_path / "season.sqlite3"
    with Book.open(path) as book:
        book.connection.execute("INSERT INTO producers VALUES ('BLYTHE', 'Blythe Farms')")
        book.connection.commit()
    with Book.open(path) as reopened:
        assert reopened.count("producers") == 1


def test_opening_an_existing_book_does_not_migrate_it_again(tmp_path):
    path = tmp_path / "season.sqlite3"
    Book.open(path).close()
    with Book.open(path) as book:
        assert book.version == LATEST


def test_foreign_keys_are_on():
    with Book.open() as book:
        row = book.connection.execute("PRAGMA foreign_keys").fetchone()
        assert row[0] == 1


def test_a_row_reads_back_by_name():
    with Book.open() as book:
        book.connection.execute("INSERT INTO producers VALUES ('BLYTHE', 'Blythe Farms')")
        row = book.connection.execute("SELECT * FROM producers").fetchone()
        assert row["name"] == "Blythe Farms"


def test_a_transaction_rolls_back_when_it_raises():
    with Book.open() as book:
        with pytest.raises(ValueError), book.transaction() as conn:
            conn.execute("INSERT INTO producers VALUES ('BLYTHE', 'Blythe Farms')")
            raise ValueError("no")
        assert book.count("producers") == 0


def test_a_transaction_commits_when_it_does_not():
    with Book.open() as book:
        with book.transaction() as conn:
            conn.execute("INSERT INTO producers VALUES ('BLYTHE', 'Blythe Farms')")
        assert book.count("producers") == 1


def test_the_book_lists_its_own_tables():
    with Book.open() as book:
        assert "tickets" in book.tables()
        assert all(not name.startswith("sqlite_") for name in book.tables())


def test_counting_a_table_nobody_made():
    with Book.open() as book, pytest.raises(KeyError):
        book.count("nothing")


def test_a_book_waits_rather_than_failing_when_another_is_writing(tmp_path):
    path = tmp_path / "season.sqlite3"
    with Book.open(path) as book:
        row = book.connection.execute("PRAGMA busy_timeout").fetchone()
        assert row[0] >= 1_000


def test_analysing_leaves_sqlite_something_to_read(tmp_path):
    path = tmp_path / "season.sqlite3"
    with Book.open(path) as book:
        book.connection.execute("INSERT INTO producers VALUES ('BLYTHE', 'Blythe Farms')")
        book.analyse()
        rows = book.connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'sqlite_stat1'"
        ).fetchall()
        assert rows


def test_analysing_an_empty_book_is_not_an_error():
    with Book.open() as book:
        book.analyse()
        assert book.count("producers") == 0


def test_closing_twice_does_not_raise(tmp_path):
    book = Book.open(tmp_path / "season.sqlite3")
    book.close()
    book.close()


def test_a_closed_book_stays_readable_on_disc(tmp_path):
    path = tmp_path / "season.sqlite3"
    book = Book.open(path)
    book.connection.execute("INSERT INTO producers VALUES ('BLYTHE', 'Blythe Farms')")
    book.connection.commit()
    book.close()
    with Book.open(path) as reopened:
        assert reopened.count("producers") == 1


def test_two_books_can_read_the_same_file(tmp_path):
    path = tmp_path / "season.sqlite3"
    with Book.open(path) as first, Book.open(path) as second:
        first.connection.execute("INSERT INTO producers VALUES ('BLYTHE', 'Blythe Farms')")
        first.connection.commit()
        assert second.count("producers") == 1
