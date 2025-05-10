import sqlite3

import pytest

from moteroom.storage.migrations import (
    LATEST,
    MIGRATIONS,
    MigrationError,
    check_migrations,
    current_version,
    migrate,
    pending,
)


def connection() -> sqlite3.Connection:
    made = sqlite3.connect(":memory:")
    made.row_factory = sqlite3.Row
    return made


def test_an_empty_file_is_at_version_zero():
    assert current_version(connection()) == 0


def test_migrating_brings_the_file_up_to_date():
    conn = connection()
    applied = migrate(conn)
    assert applied == [step.version for step in MIGRATIONS]
    assert current_version(conn) == LATEST


def test_migrating_twice_does_nothing_the_second_time():
    conn = connection()
    migrate(conn)
    assert migrate(conn) == []
    assert pending(conn) == []


def test_the_tables_the_first_migration_makes():
    conn = connection()
    migrate(conn)
    names = {
        row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"producers", "farms", "tickets"} <= names


def test_a_book_from_a_later_build_is_refused():
    conn = connection()
    conn.execute(f"PRAGMA user_version = {LATEST + 1}")
    with pytest.raises(MigrationError):
        pending(conn)


def test_a_failed_migration_leaves_nothing_behind():
    conn = connection()
    conn.execute("CREATE TABLE producers (code TEXT)")
    with pytest.raises(sqlite3.OperationalError):
        migrate(conn)
    assert current_version(conn) == 0


def test_the_migration_list_is_numbered_properly():
    check_migrations()


def test_every_migration_carries_statements_and_a_description():
    for step in MIGRATIONS:
        assert step.statements
        assert step.description.strip()
