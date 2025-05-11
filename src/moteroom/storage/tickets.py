"""The ticket book on disc.

The ticket table is the one the scale house writes to all day, so the
repository refuses anything the ticket book in memory would refuse rather than
letting a bad row land and be found in March.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.ids import ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.receiving.book import TicketBook
from moteroom.receiving.ticket import ModuleTicket

COLUMNS = "number, season, module, producer, farm, weighed_on, gross, tare, moisture, voids"


class TicketRepository:
    """Scale tickets, one table, keyed by season and number."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def add(self, ticket: ModuleTicket) -> None:
        try:
            self.connection.execute(
                f"INSERT INTO tickets ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ticket.number,
                    ticket.season.year,
                    str(ticket.module),
                    ticket.producer,
                    ticket.farm,
                    ticket.weighed_on.isoformat(),
                    ticket.gross.pounds,
                    ticket.tare.pounds,
                    str(ticket.moisture),
                    ticket.voids,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ConflictError(
                "ticket", str(ticket.number), "will not go in the book"
            ) from exc

    def get(self, season: Season, number: int) -> ModuleTicket:
        row = self.connection.execute(
            f"SELECT {COLUMNS} FROM tickets WHERE season = ? AND number = ?",
            (season.year, number),
        ).fetchone()
        if row is None:
            raise NotFoundError("ticket", str(number))
        return self._read(row)

    def for_season(self, season: Season) -> list[ModuleTicket]:
        rows = self.connection.execute(
            f"SELECT {COLUMNS} FROM tickets WHERE season = ? ORDER BY number", (season.year,)
        )
        return [self._read(row) for row in rows]

    def for_producer(self, season: Season, producer: str) -> list[ModuleTicket]:
        rows = self.connection.execute(
            f"SELECT {COLUMNS} FROM tickets WHERE season = ? AND producer = ? ORDER BY number",
            (season.year, producer),
        )
        return [self._read(row) for row in rows]

    def book(self, season: Season) -> TicketBook:
        """Load a whole season back into a ticket book."""
        loaded = TicketBook(season)
        loaded.extend(self.for_season(season))
        return loaded

    def next_number(self, season: Season) -> int:
        row = self.connection.execute(
            "SELECT max(number) AS top FROM tickets WHERE season = ?", (season.year,)
        ).fetchone()
        return int(row["top"] or 0) + 1

    def count(self, season: Season) -> int:
        row = self.connection.execute(
            "SELECT count(*) AS n FROM tickets WHERE season = ?", (season.year,)
        ).fetchone()
        return int(row["n"])

    def _read(self, row: sqlite3.Row) -> ModuleTicket:
        return ModuleTicket(
            number=int(row["number"]),
            module=ModuleId(row["module"]),
            producer=row["producer"],
            farm=row["farm"],
            weighed_on=date.fromisoformat(row["weighed_on"]),
            gross=Weight(int(row["gross"])),
            tare=Weight(int(row["tare"])),
            moisture=Decimal(row["moisture"]),
            voids=None if row["voids"] is None else int(row["voids"]),
        )
