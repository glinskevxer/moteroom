"""Check every foreign key has an index behind it.

Sqlite indexes the parent side of a foreign key and not the child side. So a
delete or a lookup that walks from the parent to its children scans the whole
child table, and nobody notices on a book with forty rows in it. On a book with
four hundred thousand they notice.

The rule is mechanical: for every foreign key, the child columns have to be the
leading columns of some index on that table. The primary key counts, because
sqlite indexes it.
"""

from __future__ import annotations

import sqlite3

from moteroom.tools.gate import Finding, run_gate

EXEMPT: set[tuple[str, str]] = set()


def _book() -> sqlite3.Connection:
    from moteroom.storage.migrations import migrate

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    migrate(connection)
    return connection


def tables(connection: sqlite3.Connection) -> list[str]:
    """Every table the migrations make, sqlite's own left out."""
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )
    return [str(row["name"]) for row in rows]


def leading_columns(connection: sqlite3.Connection, table: str) -> list[tuple[str, ...]]:
    """The leading columns of every index on a table, the primary key included."""
    found: list[tuple[str, ...]] = []
    primary = [
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table})")
        if row["pk"]
    ]
    if primary:
        found.append(tuple(primary))
    for index in connection.execute(f"PRAGMA index_list({table})"):
        columns = [
            str(row["name"])
            for row in connection.execute(f"PRAGMA index_info({index['name']})")
        ]
        found.append(tuple(columns))
    return found


def foreign_keys(connection: sqlite3.Connection, table: str) -> list[tuple[str, ...]]:
    """The child columns of every foreign key on a table, grouped by key."""
    grouped: dict[int, list[tuple[int, str]]] = {}
    for row in connection.execute(f"PRAGMA foreign_key_list({table})"):
        grouped.setdefault(int(row["id"]), []).append((int(row["seq"]), str(row["from"])))
    return [tuple(column for _, column in sorted(columns)) for columns in grouped.values()]


def run() -> tuple[list[Finding], int]:
    """Build a book and check every foreign key has something behind it."""
    findings: list[Finding] = []
    connection = _book()
    try:
        names = tables(connection)
        for table in names:
            indexes = leading_columns(connection, table)
            for key in foreign_keys(connection, table):
                if (table, ",".join(key)) in EXEMPT:
                    continue
                if not any(index[: len(key)] == key for index in indexes):
                    findings.append(
                        Finding(table, f"has no index behind the key on {', '.join(key)}")
                    )
    finally:
        connection.close()
    return findings, len(names)


def main() -> int:
    """Run the gate and give back a shell exit status."""
    return run_gate("check_indexes", run)


if __name__ == "__main__":
    raise SystemExit(main())
