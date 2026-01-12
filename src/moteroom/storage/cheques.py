"""The cheque register on disc."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.settlement.cheque import Cheque, Register
from moteroom.storage.repository import Repository

COLUMNS = "number, season, payee, amount, issued_on, cleared_on, voided_on, void_reason"


class ChequeRepository(Repository):
    """Cheques written against a season."""

    def issue(self, cheque: Cheque, season: Season) -> None:
        """Write a cheque into the register."""
        self.write(
            f"INSERT INTO cheques ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                cheque.number,
                season.year,
                cheque.payee,
                str(cheque.amount.amount),
                cheque.issued_on.isoformat(),
                None if cheque.cleared_on is None else cheque.cleared_on.isoformat(),
                None if cheque.voided_on is None else cheque.voided_on.isoformat(),
                cheque.void_reason,
            ),
            lambda: ConflictError("cheque", cheque.number, "will not go in the register"),
        )

    def get(self, number: str) -> Cheque:
        """One cheque by number."""
        row = self.one(f"SELECT {COLUMNS} FROM cheques WHERE number = ?", (number,))
        if row is None:
            raise NotFoundError("cheque", number)
        return _cheque(row)

    def clear(self, number: str, on: date) -> Cheque:
        """Mark a cheque cleared."""
        cleared = self.get(number).clear(on)
        self.connection.execute(
            "UPDATE cheques SET cleared_on = ? WHERE number = ?", (on.isoformat(), number)
        )
        return cleared

    def void(self, number: str, on: date, reason: str) -> Cheque:
        """Void a cheque, keeping why."""
        voided = self.get(number).void(on, reason)
        self.connection.execute(
            "UPDATE cheques SET voided_on = ?, void_reason = ? WHERE number = ?",
            (on.isoformat(), voided.void_reason, number),
        )
        return voided

    def register(self, season: Season) -> Register:
        """Rebuild a season's register out of the book."""
        made = Register()
        rows = self.rows(
            f"SELECT {COLUMNS} FROM cheques WHERE season = ? ORDER BY number", (season.year,)
        )
        made.extend(_cheque(row) for row in rows)
        return made

    def for_payee(self, season: Season, payee: str) -> list[Cheque]:
        """Every cheque written to one producer."""
        rows = self.rows(
            f"SELECT {COLUMNS} FROM cheques WHERE season = ? AND payee = ? ORDER BY number",
            (season.year, payee),
        )
        return [_cheque(row) for row in rows]


def _cheque(row: sqlite3.Row) -> Cheque:
    cleared = row["cleared_on"]
    voided = row["voided_on"]
    return Cheque(
        number=row["number"],
        payee=row["payee"],
        amount=Money(Decimal(row["amount"])),
        issued_on=date.fromisoformat(row["issued_on"]),
        cleared_on=None if cleared is None else date.fromisoformat(cleared),
        voided_on=None if voided is None else date.fromisoformat(voided),
        void_reason=str(row["void_reason"]),
    )
