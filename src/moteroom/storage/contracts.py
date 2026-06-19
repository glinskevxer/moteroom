"""Contracts and deliveries on disc.

A bale can only be delivered against one contract, which is a unique index
rather than a check in code, because two terminals writing at once will beat
any check in code.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.ids import BaleId
from moteroom.core.money import CentsPerPound
from moteroom.core.season import Season
from moteroom.settlement.contract import Contract, Fill, fill_of
from moteroom.storage import rows as read
from moteroom.storage.repository import Repository

COLUMNS = "number, season, buyer, signed_on, bales, delivery_from, delivery_to, price, basis"


class ContractRepository(Repository):
    """Forward contracts, keyed by number."""

    def add(self, contract: Contract, season: Season) -> None:
        """Write a contract, which cannot be written twice."""
        self.write(
            f"INSERT INTO contracts ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                contract.number,
                season.year,
                contract.buyer,
                contract.signed_on.isoformat(),
                contract.bales,
                contract.delivery_from.isoformat(),
                contract.delivery_to.isoformat(),
                None if contract.price is None else str(contract.price.cents),
                None if contract.basis is None else str(contract.basis.cents),
            ),
            lambda: ConflictError("contract", contract.number, "is already on the book"),
        )

    def get(self, number: str) -> Contract:
        """One contract by number."""
        row = self.one(f"SELECT {COLUMNS} FROM contracts WHERE number = ?", (number,))
        if row is None:
            raise NotFoundError("contract", number)
        return _contract(row)

    def for_season(self, season: Season) -> list[Contract]:
        """Every contract written for a season."""
        rows = self.rows(
            f"SELECT {COLUMNS} FROM contracts WHERE season = ? ORDER BY number", (season.year,)
        )
        return [_contract(row) for row in rows]

    def deliver(self, number: str, bale_id: BaleId, on: date, rate: CentsPerPound) -> None:
        """Deliver a bale against a contract."""
        self.get(number)
        self.write(
            "INSERT INTO deliveries (contract, bale_id, delivered_on, rate) "
            "VALUES (?, ?, ?, ?)",
            (number, str(bale_id), on.isoformat(), str(rate.cents)),
            lambda: ConflictError("bale", str(bale_id), "is already delivered"),
        )

    def deliveries(self, number: str) -> list[tuple[BaleId, date, CentsPerPound]]:
        """Every bale delivered against a contract, in delivery order."""
        rows = self.rows(
            "SELECT bale_id, delivered_on, rate FROM deliveries WHERE contract = ? "
            "ORDER BY delivered_on, bale_id",
            (number,),
        )
        return [
            (
                BaleId(row["bale_id"]),
                read.day(row, "delivered_on"),
                read.rate(row, "rate"),
            )
            for row in rows
        ]

    def fill(self, number: str) -> Fill:
        """How much of a contract has been delivered."""
        return fill_of(self.get(number), [1] * len(self.deliveries(number)))

    def contract_for(self, bale_id: BaleId) -> str | None:
        """Which contract a bale went against, if any."""
        row = self.one("SELECT contract FROM deliveries WHERE bale_id = ?", (str(bale_id),))
        return None if row is None else str(row["contract"])


def _contract(row: sqlite3.Row) -> Contract:
    return Contract(
        number=row["number"],
        buyer=row["buyer"],
        signed_on=read.day(row, "signed_on"),
        bales=int(row["bales"]),
        delivery_from=read.day(row, "delivery_from"),
        delivery_to=read.day(row, "delivery_to"),
        price=read.maybe_rate(row, "price"),
        basis=read.maybe_rate(row, "basis"),
    )
