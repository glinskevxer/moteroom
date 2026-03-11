import sqlite3

import pytest

from moteroom.core.errors import ConflictError
from moteroom.storage.book import Book
from moteroom.storage.repository import Repository


@pytest.fixture()
def repo():
    with Book.open() as book:
        yield Repository(book.connection)


def refusal() -> ConflictError:
    return ConflictError("producer", "BLYTHE", "is already on the book")


def test_one_row_or_nothing(repo):
    assert repo.one("SELECT 1 AS n") is not None
    assert repo.one("SELECT 1 WHERE 0") is None


def test_rows_come_back_as_a_list(repo):
    rows = repo.rows("SELECT name FROM sqlite_master WHERE type = 'table'")
    assert isinstance(rows, list)
    assert rows


def test_a_scalar_reads_a_number_and_nothing_reads_as_zero(repo):
    assert repo.scalar("SELECT count(*) FROM producers") == 0
    assert repo.scalar("SELECT max(rowid) FROM producers") == 0
    assert repo.scalar("SELECT 7") == 7


def test_exists_answers_the_question(repo):
    assert repo.exists("SELECT 1")
    assert not repo.exists("SELECT 1 WHERE 0")


def test_a_write_turns_a_constraint_into_a_refusal(repo):
    repo.write("INSERT INTO producers VALUES (?, ?)", ("BLYTHE", "Blythe Farms"), refusal)
    with pytest.raises(ConflictError) as caught:
        repo.write("INSERT INTO producers VALUES (?, ?)", ("BLYTHE", "Again"), refusal)
    assert caught.value.key == "BLYTHE"


def test_a_write_many_refuses_the_same_way(repo):
    rows = [("BLYTHE", "Blythe Farms"), ("BLYTHE", "Again")]
    with pytest.raises(ConflictError):
        repo.write_many("INSERT INTO producers VALUES (?, ?)", rows, refusal)


def test_a_write_that_is_not_a_constraint_still_raises(repo):
    with pytest.raises(sqlite3.OperationalError):
        repo.write("INSERT INTO nothing VALUES (1)", (), refusal)


def test_changed_counts_the_rows_a_statement_touched(repo):
    repo.write("INSERT INTO producers VALUES (?, ?)", ("BLYTHE", "Blythe Farms"), refusal)
    assert repo.changed("UPDATE producers SET name = 'x'") == 1
    assert repo.changed("UPDATE producers SET name = 'x' WHERE code = 'NOBODY'") == 0


def test_a_savepoint_rolls_its_own_writes_back(repo):
    repo.write("INSERT INTO producers VALUES (?, ?)", ("BLYTHE", "Blythe Farms"), refusal)
    with pytest.raises(ValueError), repo.atomic():
        repo.write("INSERT INTO producers VALUES (?, ?)", ("MERRITT", "Merritt"), refusal)
        raise ValueError("no")
    assert repo.scalar("SELECT count(*) FROM producers") == 1


def test_a_savepoint_that_finishes_keeps_its_writes(repo):
    with repo.atomic():
        repo.write("INSERT INTO producers VALUES (?, ?)", ("BLYTHE", "Blythe Farms"), refusal)
    assert repo.scalar("SELECT count(*) FROM producers") == 1


def test_savepoints_nest(repo):
    with repo.atomic():
        repo.write("INSERT INTO producers VALUES (?, ?)", ("BLYTHE", "Blythe Farms"), refusal)
        with pytest.raises(ValueError), repo.atomic():
            repo.write("INSERT INTO producers VALUES (?, ?)", ("MERRITT", "Merritt"), refusal)
            raise ValueError("no")
    assert repo.scalar("SELECT count(*) FROM producers") == 1
