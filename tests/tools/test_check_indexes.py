import sqlite3

from moteroom.tools.check_indexes import (
    _book,
    foreign_keys,
    leading_columns,
    main,
    run,
    tables,
)


def test_every_foreign_key_has_an_index_behind_it():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 15


def test_the_gate_exits_clean():
    assert main() == 0


def test_the_book_it_builds_carries_the_tables():
    connection = _book()
    try:
        assert "tickets" in tables(connection)
        assert not any(name.startswith("sqlite_") for name in tables(connection))
    finally:
        connection.close()


def test_a_primary_key_counts_as_an_index():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE thing (a TEXT, b TEXT, PRIMARY KEY (a, b))")
    assert ("a", "b") in leading_columns(connection, "thing")
    connection.close()


def test_the_child_columns_of_a_key_come_back_in_order():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE parent (a TEXT, b TEXT, PRIMARY KEY (a, b))")
    connection.execute(
        "CREATE TABLE child (x TEXT, y TEXT, FOREIGN KEY (x, y) REFERENCES parent(a, b))"
    )
    assert foreign_keys(connection, "child") == [("x", "y")]
    connection.close()


def test_a_key_with_nothing_behind_it_is_caught():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE parent (a TEXT PRIMARY KEY)")
    connection.execute("CREATE TABLE child (x TEXT REFERENCES parent(a))")
    indexes = leading_columns(connection, "child")
    assert not any(index[:1] == ("x",) for index in indexes)
    connection.close()


def test_a_table_with_no_keys_has_nothing_to_check():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE alone (a TEXT PRIMARY KEY)")
    assert foreign_keys(connection, "alone") == []
    connection.close()
