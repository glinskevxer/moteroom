"""Hauling and byproduct sales on disc.

Both of these reach a producer's settlement, so both have to be in the book
rather than typed in again at settlement time. They are kept as what happened
rather than as what it came to: the load and its miles, the sale and its price.
The money is worked out from those every time, so a rate corrected in December
corrects every statement that has not been run yet.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.byproduct import ByproductLedger, Sale
from moteroom.receiving.freight import FreightLedger, Haul, Rate
from moteroom.storage.repository import Repository

RATE_COLUMNS = "season, hauler, per_module, per_mile, minimum"
SALE_COLUMNS = "season, kind, sold_on, weight, price_per_ton, buyer"


class FreightRepository(Repository):
    """Hauliers, their rates and the loads they brought in."""

    def post(self, season: Season, rate: Rate) -> None:
        """Post a hauler's rates for a season."""
        self.write(
            f"INSERT INTO haulers ({RATE_COLUMNS}) VALUES (?, ?, ?, ?, ?)",
            (
                season.year,
                rate.hauler,
                str(rate.per_module.amount),
                str(rate.per_mile.amount),
                str(rate.minimum.amount),
            ),
            lambda: ConflictError("hauler", rate.hauler, "already has rates for this season"),
        )

    def rates(self, season: Season) -> list[Rate]:
        """Every hauler posted for a season."""
        rows = self.rows(
            f"SELECT {RATE_COLUMNS} FROM haulers WHERE season = ? ORDER BY hauler",
            (season.year,),
        )
        return [_rate(row) for row in rows]

    def rate(self, season: Season, hauler: str) -> Rate:
        row = self.one(
            f"SELECT {RATE_COLUMNS} FROM haulers WHERE season = ? AND hauler = ?",
            (season.year, hauler),
        )
        if row is None:
            raise NotFoundError("hauler", hauler)
        return _rate(row)

    def haul(self, season: Season, load: Haul) -> int:
        """Record a load, which has to name a hauler with rates posted."""
        self.rate(season, load.hauler)
        refuse = _refusing(load)
        with self.atomic():
            self.write(
                "INSERT INTO hauls (season, hauler, hauled_on, miles) VALUES (?, ?, ?, ?)",
                (season.year, load.hauler, load.hauled_on.isoformat(), load.miles),
                refuse,
            )
            made = self.scalar("SELECT max(id) FROM hauls")
            self.write_many(
                "INSERT INTO haul_tickets (haul, season, ticket) VALUES (?, ?, ?)",
                [(made, season.year, ticket) for ticket in load.tickets],
                refuse,
            )
        return made

    def hauls(self, season: Season) -> list[Haul]:
        """Every load brought in this season, oldest first."""
        rows = self.rows(
            "SELECT id, hauler, hauled_on, miles FROM hauls WHERE season = ? "
            "ORDER BY hauled_on, id",
            (season.year,),
        )
        return [
            Haul(
                hauler=str(row["hauler"]),
                hauled_on=date.fromisoformat(row["hauled_on"]),
                tickets=self._tickets(int(row["id"])),
                miles=int(row["miles"]),
            )
            for row in rows
        ]

    def ledger(self, season: Season) -> FreightLedger:
        """Rebuild the season's freight out of the book."""
        made = FreightLedger(self.rates(season))
        for load in self.hauls(season):
            made.haul(load)
        return made

    def _tickets(self, haul: int) -> tuple[int, ...]:
        rows = self.rows(
            "SELECT ticket FROM haul_tickets WHERE haul = ? ORDER BY ticket", (haul,)
        )
        return tuple(int(row["ticket"]) for row in rows)


class ByproductRepository(Repository):
    """What the motes and the gin trash sold for."""

    def sell(self, season: Season, sale: Sale) -> None:
        """Record a load leaving the plant."""
        self.write(
            f"INSERT INTO byproduct_sales ({SALE_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?)",
            (
                season.year,
                sale.kind,
                sale.sold_on.isoformat(),
                sale.weight.pounds,
                str(sale.price_per_ton.amount),
                sale.buyer,
            ),
            lambda: ConflictError("sale", sale.kind, "will not go in the book"),
        )

    def sales(self, season: Season) -> list[Sale]:
        """Every load sold this season, oldest first."""
        rows = self.rows(
            f"SELECT {SALE_COLUMNS} FROM byproduct_sales WHERE season = ? ORDER BY sold_on, id",
            (season.year,),
        )
        return [
            Sale(
                kind=str(row["kind"]),
                sold_on=date.fromisoformat(row["sold_on"]),
                weight=Weight(int(row["weight"])),
                price_per_ton=Money(Decimal(row["price_per_ton"])),
                buyer=str(row["buyer"]),
            )
            for row in rows
        ]

    def ledger(self, season: Season) -> ByproductLedger:
        """Rebuild the season's byproduct ledger out of the book."""
        made = ByproductLedger()
        made.extend(self.sales(season))
        return made


def _rate(row: sqlite3.Row) -> Rate:
    return Rate(
        hauler=str(row["hauler"]),
        per_module=Money(Decimal(row["per_module"])),
        per_mile=Money(Decimal(row["per_mile"])),
        minimum=Money(Decimal(row["minimum"])),
    )


def _refusing(load: Haul) -> Callable[[], Exception]:
    """The error a load that will not go in the book comes back as."""
    return lambda: ConflictError(
        "haul", load.hauler, "names a module this season has no ticket for"
    )
