"""Producers and farms in the book."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.receiving.party import Farm, Producer
from moteroom.storage.repository import Repository


class ProducerRepository(Repository):
    """Growers, keyed by the code the office types."""

    def add(self, producer: Producer) -> None:
        """Put a grower on the book."""
        self.write(
            "INSERT INTO producers (code, name) VALUES (?, ?)",
            (producer.code, producer.name),
            lambda: ConflictError("producer", producer.code, "is already on the book"),
        )

    def rename(self, code: str, name: str) -> None:
        """Change a grower's name without touching anything hanging off it."""
        if self.changed("UPDATE producers SET name = ? WHERE code = ?", (name, code)) == 0:
            raise NotFoundError("producer", code)

    def get(self, code: str) -> Producer:
        """One grower by code."""
        row = self.one("SELECT code, name FROM producers WHERE code = ?", (code,))
        if row is None:
            raise NotFoundError("producer", code)
        return Producer(row["code"], row["name"])

    def has(self, code: str) -> bool:
        """Whether the book knows this grower."""
        return self.exists("SELECT 1 FROM producers WHERE code = ?", (code,))

    def all(self) -> list[Producer]:
        """Every grower, in code order."""
        rows = self.rows("SELECT code, name FROM producers ORDER BY code")
        return [Producer(row["code"], row["name"]) for row in rows]

    def count(self) -> int:
        """How many growers are on the book."""
        return self.scalar("SELECT count(*) FROM producers")


class FarmRepository(Repository):
    """Farms and tracts, which hang off a producer."""

    COLUMNS = "number, tract, producer, acres"

    def add(self, farm: Farm) -> None:
        """Add a farm and tract to a grower already on the book."""
        self.write(
            f"INSERT INTO farms ({self.COLUMNS}) VALUES (?, ?, ?, ?)",
            (farm.number, farm.tract, farm.producer, str(farm.acres)),
            lambda: ConflictError("farm", farm.key, "is already on the book"),
        )

    def get(self, number: str, tract: str) -> Farm:
        """One farm and tract."""
        row = self.one(
            f"SELECT {self.COLUMNS} FROM farms WHERE number = ? AND tract = ?",
            (number, tract),
        )
        if row is None:
            raise NotFoundError("farm", f"{number}-{tract}")
        return _farm(row)

    def for_producer(self, code: str) -> list[Farm]:
        """Every farm a grower gins off."""
        rows = self.rows(
            f"SELECT {self.COLUMNS} FROM farms WHERE producer = ? ORDER BY number, tract",
            (code,),
        )
        return [_farm(row) for row in rows]

    def all(self) -> list[Farm]:
        """Every farm on the book."""
        rows = self.rows(f"SELECT {self.COLUMNS} FROM farms ORDER BY number, tract")
        return [_farm(row) for row in rows]

    def acres_for(self, code: str) -> Decimal:
        """Acres a grower has on the book, which is what FSA asks."""
        return sum((farm.acres for farm in self.for_producer(code)), start=Decimal("0.00"))


def _farm(row: sqlite3.Row) -> Farm:
    return Farm(row["number"], row["tract"], row["producer"], Decimal(row["acres"]))
