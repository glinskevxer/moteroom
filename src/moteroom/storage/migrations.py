"""Migrations.

The book is a sqlite file that lives on the office machine and gets copied
onto a memory stick at the end of the season, so it has to be able to move
forward from whatever version it was left at. Every migration is a numbered
list of statements, applied in one transaction, and the version it reached is
written into the file itself.

Migrations are append only. Editing one that has shipped means two books with
the same version number and different shapes, which is the one thing this
module exists to prevent.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from moteroom.core.errors import MoteroomError


class MigrationError(MoteroomError):
    """The book is at a version this build cannot work with."""


@dataclass(frozen=True)
class Migration:
    """One numbered step, with the statements that make it."""

    version: int
    description: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        description="producers, farms and the ticket book",
        statements=(
            """
            CREATE TABLE producers (
                code        TEXT PRIMARY KEY,
                name        TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE farms (
                number      TEXT NOT NULL,
                tract       TEXT NOT NULL,
                producer    TEXT NOT NULL REFERENCES producers(code),
                acres       TEXT NOT NULL,
                PRIMARY KEY (number, tract)
            )
            """,
            """
            CREATE TABLE tickets (
                number      INTEGER NOT NULL,
                season      INTEGER NOT NULL,
                module      TEXT NOT NULL,
                producer    TEXT NOT NULL REFERENCES producers(code),
                farm        TEXT NOT NULL,
                weighed_on  TEXT NOT NULL,
                gross       INTEGER NOT NULL,
                tare        INTEGER NOT NULL,
                moisture    TEXT NOT NULL,
                voids       INTEGER,
                PRIMARY KEY (season, number)
            )
            """,
            "CREATE INDEX tickets_by_producer ON tickets (season, producer)",
            "CREATE UNIQUE INDEX tickets_by_module ON tickets (season, module, number)",
        ),
    ),
    Migration(
        version=2,
        description="gin lots and the bales pressed off them",
        statements=(
            """
            CREATE TABLE lots (
                season      INTEGER NOT NULL,
                number      INTEGER NOT NULL,
                ginned_on   TEXT NOT NULL,
                seed_cotton INTEGER NOT NULL,
                lint        INTEGER NOT NULL,
                seed        INTEGER NOT NULL,
                motes       INTEGER NOT NULL,
                closed      INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (season, number)
            )
            """,
            """
            CREATE TABLE lot_tickets (
                season      INTEGER NOT NULL,
                lot         INTEGER NOT NULL,
                ticket      INTEGER NOT NULL,
                PRIMARY KEY (season, lot, ticket),
                FOREIGN KEY (season, lot) REFERENCES lots(season, number),
                FOREIGN KEY (season, ticket) REFERENCES tickets(season, number)
            )
            """,
            """
            CREATE TABLE bales (
                bale_id     TEXT PRIMARY KEY,
                season      INTEGER NOT NULL,
                lot         INTEGER NOT NULL,
                number      INTEGER NOT NULL,
                pressed_on  TEXT NOT NULL,
                gross       INTEGER NOT NULL,
                tare        INTEGER NOT NULL,
                moisture    TEXT NOT NULL,
                FOREIGN KEY (season, lot) REFERENCES lots(season, number)
            )
            """,
            "CREATE INDEX bales_by_lot ON bales (season, lot)",
            "CREATE UNIQUE INDEX bales_by_number ON bales (season, number)",
        ),
    ),
    Migration(
        version=3,
        description="classing cards and their extraneous findings",
        statements=(
            """
            CREATE TABLE cards (
                bale_id     TEXT PRIMARY KEY REFERENCES bales(bale_id),
                classed_on  TEXT NOT NULL,
                office      TEXT NOT NULL,
                micronaire  TEXT NOT NULL,
                staple      INTEGER NOT NULL,
                strength    TEXT NOT NULL,
                uniformity  TEXT NOT NULL,
                color       INTEGER NOT NULL,
                leaf        INTEGER NOT NULL,
                trash       TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE card_extraneous (
                bale_id     TEXT NOT NULL REFERENCES cards(bale_id),
                code        TEXT NOT NULL,
                PRIMARY KEY (bale_id, code)
            )
            """,
            "CREATE INDEX cards_by_grade ON cards (color, leaf)",
        ),
    ),
    Migration(
        version=4,
        description="warehouse receipts and shipping orders",
        statements=(
            """
            CREATE TABLE receipts (
                number      TEXT PRIMARY KEY,
                warehouse   TEXT NOT NULL,
                bale_id     TEXT NOT NULL REFERENCES bales(bale_id),
                received_on TEXT NOT NULL,
                net         INTEGER NOT NULL,
                holder      TEXT NOT NULL,
                electronic  INTEGER NOT NULL DEFAULT 1,
                released_on TEXT
            )
            """,
            "CREATE INDEX receipts_by_bale ON receipts (bale_id)",
            "CREATE INDEX receipts_by_holder ON receipts (holder, released_on)",
            """
            CREATE TABLE orders (
                number      TEXT PRIMARY KEY,
                warehouse   TEXT NOT NULL,
                ordered_on  TEXT NOT NULL,
                buyer       TEXT NOT NULL,
                ship_by     TEXT
            )
            """,
            """
            CREATE TABLE order_receipts (
                order_number TEXT NOT NULL REFERENCES orders(number),
                receipt      TEXT NOT NULL REFERENCES receipts(number),
                position     INTEGER NOT NULL,
                PRIMARY KEY (order_number, receipt)
            )
            """,
        ),
    ),
    Migration(
        version=5,
        description="settlements and the advances that come off them",
        statements=(
            """
            CREATE TABLE statements (
                season          INTEGER NOT NULL,
                producer        TEXT NOT NULL REFERENCES producers(code),
                bales           INTEGER NOT NULL,
                lint            INTEGER NOT NULL,
                lint_proceeds   TEXT NOT NULL,
                gin_charges     TEXT NOT NULL,
                seed_credit     TEXT NOT NULL,
                settled_on      TEXT NOT NULL,
                PRIMARY KEY (season, producer)
            )
            """,
            """
            CREATE TABLE advances (
                season      INTEGER NOT NULL,
                producer    TEXT NOT NULL REFERENCES producers(code),
                reference   TEXT NOT NULL,
                amount      TEXT NOT NULL,
                paid_on     TEXT NOT NULL,
                PRIMARY KEY (season, producer, reference)
            )
            """,
            "CREATE INDEX advances_by_producer ON advances (season, producer)",
        ),
    ),
    Migration(
        version=6,
        description="plant settings, such as the gin code and the season's rates",
        statements=(
            """
            CREATE TABLE settings (
                name        TEXT PRIMARY KEY,
                value       TEXT NOT NULL,
                changed_on  TEXT NOT NULL
            )
            """,
        ),
    ),
)

LATEST = MIGRATIONS[-1].version


def current_version(connection: sqlite3.Connection) -> int:
    """What version the file is at, which is zero for an empty one."""
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0])


def pending(connection: sqlite3.Connection) -> list[Migration]:
    """The migrations this file has not had yet."""
    at = current_version(connection)
    if at > LATEST:
        raise MigrationError(f"the book is at version {at} and this build knows {LATEST}")
    return [step for step in MIGRATIONS if step.version > at]


def migrate(connection: sqlite3.Connection) -> list[int]:
    """Bring a book up to date, returning the versions applied."""
    applied: list[int] = []
    for step in pending(connection):
        with connection:
            for statement in step.statements:
                connection.execute(statement)
            connection.execute(f"PRAGMA user_version = {step.version}")
        applied.append(step.version)
    return applied


def check_migrations() -> None:
    """Refuse a build whose migrations are numbered wrongly."""
    versions = [step.version for step in MIGRATIONS]
    if versions != sorted(versions):
        raise MigrationError("migrations are out of order")
    if len(set(versions)) != len(versions):
        raise MigrationError("two migrations share a version")
    if versions and versions[0] != 1:
        raise MigrationError("migrations start at one")
    for earlier, later in zip(versions, versions[1:], strict=False):
        if later != earlier + 1:
            raise MigrationError(f"a version is missing between {earlier} and {later}")
