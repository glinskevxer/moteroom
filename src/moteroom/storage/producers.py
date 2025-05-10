"""Producers and farms in the book."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.receiving.party import Farm, Producer


class ProducerRepository:
    """Growers, keyed by the code the office types."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def add(self, producer: Producer) -> None:
        try:
            self.connection.execute(
                "INSERT INTO producers (code, name) VALUES (?, ?)",
                (producer.code, producer.name),
            )
        except sqlite3.IntegrityError as exc:
            raise ConflictError("producer", producer.code, "is already on the book") from exc

    def rename(self, code: str, name: str) -> None:
        updated = self.connection.execute(
            "UPDATE producers SET name = ? WHERE code = ?", (name, code)
        )
        if updated.rowcount == 0:
            raise NotFoundError("producer", code)

    def get(self, code: str) -> Producer:
        row = self.connection.execute(
            "SELECT code, name FROM producers WHERE code = ?", (code,)
        ).fetchone()
        if row is None:
            raise NotFoundError("producer", code)
        return Producer(row["code"], row["name"])

    def exists(self, code: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM producers WHERE code = ?", (code,)
        ).fetchone()
        return row is not None

    def all(self) -> list[Producer]:
        rows = self.connection.execute("SELECT code, name FROM producers ORDER BY code")
        return [Producer(row["code"], row["name"]) for row in rows]

    def count(self) -> int:
        row = self.connection.execute("SELECT count(*) AS n FROM producers").fetchone()
        return int(row["n"])


class FarmRepository:
    """Farms and tracts, which hang off a producer."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def add(self, farm: Farm) -> None:
        try:
            self.connection.execute(
                "INSERT INTO farms (number, tract, producer, acres) VALUES (?, ?, ?, ?)",
                (farm.number, farm.tract, farm.producer, str(farm.acres)),
            )
        except sqlite3.IntegrityError as exc:
            raise ConflictError("farm", farm.key, "is already on the book") from exc

    def get(self, number: str, tract: str) -> Farm:
        row = self.connection.execute(
            "SELECT number, tract, producer, acres FROM farms WHERE number = ? AND tract = ?",
            (number, tract),
        ).fetchone()
        if row is None:
            raise NotFoundError("farm", f"{number}-{tract}")
        return self._read(row)

    def for_producer(self, code: str) -> list[Farm]:
        rows = self.connection.execute(
            "SELECT number, tract, producer, acres FROM farms WHERE producer = ? "
            "ORDER BY number, tract",
            (code,),
        )
        return [self._read(row) for row in rows]

    def all(self) -> list[Farm]:
        rows = self.connection.execute(
            "SELECT number, tract, producer, acres FROM farms ORDER BY number, tract"
        )
        return [self._read(row) for row in rows]

    def acres_for(self, code: str) -> Decimal:
        return sum((farm.acres for farm in self.for_producer(code)), start=Decimal("0.00"))

    def _read(self, row: sqlite3.Row) -> Farm:
        return Farm(row["number"], row["tract"], row["producer"], Decimal(row["acres"]))
