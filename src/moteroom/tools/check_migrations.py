"""Check the migrations still make a book this build can use.

Migrations are the one part of the package that cannot be fixed by editing,
because a book already migrated has kept the shape the old statement made. So
this gate refuses a renumbering, refuses a gap, and applies the whole list to a
fresh file to be certain the statements still run in order.
"""

from __future__ import annotations

import sqlite3

from moteroom.core.errors import MoteroomError
from moteroom.storage.migrations import (
    LATEST,
    MIGRATIONS,
    check_migrations,
    current_version,
    migrate,
)
from moteroom.tools.gate import Finding, run_gate

EXPECTED_TABLES = {
    "producers",
    "farms",
    "tickets",
    "lots",
    "lot_tickets",
    "bales",
    "cards",
    "card_extraneous",
    "receipts",
    "orders",
    "order_receipts",
    "statements",
    "advances",
    "settings",
    "season_rates",
    "contracts",
    "deliveries",
    "audit",
    "cheques",
    "haulers",
    "hauls",
    "haul_tickets",
    "byproduct_sales",
}


def run() -> tuple[list[Finding], int]:
    """Apply every migration to a fresh book and look at what came out."""
    findings: list[Finding] = []
    try:
        check_migrations()
    except MoteroomError as exc:
        findings.append(Finding("MIGRATIONS", str(exc)))
        return findings, len(MIGRATIONS)

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    applied = migrate(connection)
    if applied != [step.version for step in MIGRATIONS]:
        findings.append(Finding("MIGRATIONS", "a migration did not apply"))
    if current_version(connection) != LATEST:
        findings.append(Finding("MIGRATIONS", "the book did not reach the latest version"))
    if migrate(connection):
        findings.append(Finding("MIGRATIONS", "migrating twice was not a no-op"))

    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    tables = {str(row["name"]) for row in rows if not str(row["name"]).startswith("sqlite_")}
    for missing in sorted(EXPECTED_TABLES - tables):
        findings.append(Finding(missing, "is expected and the migrations do not make it"))
    for extra in sorted(tables - EXPECTED_TABLES):
        findings.append(Finding(extra, "is made and this gate does not know about it"))

    for table in sorted(tables):
        columns = connection.execute(f"PRAGMA table_info({table})").fetchall()
        if not any(column["pk"] for column in columns):
            findings.append(Finding(table, "has no primary key"))

    problems = connection.execute("PRAGMA foreign_key_check").fetchall()
    if problems:
        findings.append(Finding("MIGRATIONS", "a foreign key does not resolve"))
    connection.close()
    return findings, len(MIGRATIONS)


def main() -> int:
    """Run the gate and give back a shell exit status."""
    return run_gate("check_migrations", run)


if __name__ == "__main__":
    raise SystemExit(main())
