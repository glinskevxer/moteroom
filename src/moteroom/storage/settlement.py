"""Settlements and advances on disc.

An advance is written when the cheque goes out, months before the settlement
exists. So advances stand on their own and the settlement picks them up when it
is built, rather than the settlement owning them.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.settlement.statement import Advance, Statement
from moteroom.storage.repository import Repository

COLUMNS = "season, producer, bales, lint, lint_proceeds, gin_charges, seed_credit, settled_on"


class AdvanceRepository(Repository):
    """Money paid out during the season, by producer."""

    def add(self, season: Season, producer: str, advance: Advance, paid_on: date) -> None:
        try:
            self.connection.execute(
                "INSERT INTO advances (season, producer, reference, amount, paid_on) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    season.year,
                    producer,
                    advance.reference,
                    str(advance.amount.amount),
                    paid_on.isoformat(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ConflictError(
                "advance", advance.reference, "will not go in the book"
            ) from exc

    def for_producer(self, season: Season, producer: str) -> tuple[Advance, ...]:
        rows = self.connection.execute(
            "SELECT reference, amount FROM advances WHERE season = ? AND producer = ? "
            "ORDER BY paid_on, reference",
            (season.year, producer),
        )
        return tuple(Advance(row["reference"], Money(Decimal(row["amount"]))) for row in rows)

    def total(self, season: Season, producer: str) -> Money:
        advances = self.for_producer(season, producer)
        return Money(sum((a.amount.amount for a in advances), Decimal("0.00")))


class StatementRepository(Repository):
    """Settlements, one per producer per season."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        self.advances = AdvanceRepository(connection)

    def save(self, statement: Statement, settled_on: date) -> None:
        try:
            self.connection.execute(
                f"INSERT INTO statements ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    statement.season.year,
                    statement.producer,
                    statement.bales,
                    statement.lint.pounds,
                    str(statement.lint_proceeds.amount),
                    str(statement.gin_charges.amount),
                    str(statement.seed_credit.amount),
                    settled_on.isoformat(),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ConflictError(
                "statement", statement.producer, "is already settled for this season"
            ) from exc

    def get(self, season: Season, producer: str) -> Statement:
        row = self.connection.execute(
            f"SELECT {COLUMNS} FROM statements WHERE season = ? AND producer = ?",
            (season.year, producer),
        ).fetchone()
        if row is None:
            raise NotFoundError("statement", producer)
        return self._read(row)

    def for_season(self, season: Season) -> list[Statement]:
        rows = self.connection.execute(
            f"SELECT {COLUMNS} FROM statements WHERE season = ? ORDER BY producer",
            (season.year,),
        )
        return [self._read(row) for row in rows.fetchall()]

    def settled_on(self, season: Season, producer: str) -> date:
        row = self.connection.execute(
            "SELECT settled_on FROM statements WHERE season = ? AND producer = ?",
            (season.year, producer),
        ).fetchone()
        if row is None:
            raise NotFoundError("statement", producer)
        return date.fromisoformat(row["settled_on"])

    def _read(self, row: sqlite3.Row) -> Statement:
        season = Season(int(row["season"]))
        return Statement(
            producer=row["producer"],
            season=season,
            bales=int(row["bales"]),
            lint=Weight(int(row["lint"])),
            lint_proceeds=Money(Decimal(row["lint_proceeds"])),
            gin_charges=Money(Decimal(row["gin_charges"])),
            seed_credit=Money(Decimal(row["seed_credit"])),
            advances=self.advances.for_producer(season, row["producer"]),
        )
