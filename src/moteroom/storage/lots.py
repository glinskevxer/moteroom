"""Gin lots and their bales on disc.

A lot and the tickets it ginned are written together or not at all, because a
lot whose tickets are missing is worse than no lot: it looks complete and
reports a turnout off nothing.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.ids import BaleId, GinCode, LotId
from moteroom.core.season import Season
from moteroom.core.weight import Weight, total
from moteroom.ginning.run import GinRun
from moteroom.press.bale import Bale
from moteroom.press.run import BalePress
from moteroom.storage.repository import Repository

LOT_COLUMNS = "season, number, ginned_on, seed_cotton, lint, seed, motes, closed"
BALE_COLUMNS = "bale_id, season, lot, number, pressed_on, gross, tare, moisture"


class LotRepository(Repository):
    """Lots, with the tickets each one ginned."""

    def add(self, run: GinRun) -> None:
        refuse = _named(lambda: ConflictError("lot", str(run.lot), "will not go in the book"))
        with self.atomic():
            self.write(
                f"INSERT INTO lots ({LOT_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    run.lot.season.year,
                    run.lot.number,
                    run.ginned_on.isoformat(),
                    run.seed_cotton.pounds,
                    run.lint.pounds,
                    run.seed.pounds,
                    run.motes.pounds,
                ),
                refuse,
            )
            self.write_many(
                "INSERT INTO lot_tickets (season, lot, ticket) VALUES (?, ?, ?)",
                [(run.lot.season.year, run.lot.number, ticket) for ticket in run.tickets],
                refuse,
            )

    def get(self, lot: LotId) -> GinRun:
        row = self.connection.execute(
            f"SELECT {LOT_COLUMNS} FROM lots WHERE season = ? AND number = ?",
            (lot.season.year, lot.number),
        ).fetchone()
        if row is None:
            raise NotFoundError("lot", str(lot))
        return self._read(row)

    def close(self, lot: LotId) -> None:
        updated = self.connection.execute(
            "UPDATE lots SET closed = 1 WHERE season = ? AND number = ?",
            (lot.season.year, lot.number),
        )
        if updated.rowcount == 0:
            raise NotFoundError("lot", str(lot))

    def is_closed(self, lot: LotId) -> bool:
        row = self.connection.execute(
            "SELECT closed FROM lots WHERE season = ? AND number = ?",
            (lot.season.year, lot.number),
        ).fetchone()
        if row is None:
            raise NotFoundError("lot", str(lot))
        return bool(row["closed"])

    def for_season(self, season: Season) -> list[GinRun]:
        rows = self.connection.execute(
            f"SELECT {LOT_COLUMNS} FROM lots WHERE season = ? ORDER BY number", (season.year,)
        )
        return [self._read(row) for row in rows.fetchall()]

    def next_number(self, season: Season) -> int:
        row = self.connection.execute(
            "SELECT max(number) AS top FROM lots WHERE season = ?", (season.year,)
        ).fetchone()
        return int(row["top"] or 0) + 1

    def assigned_tickets(self, season: Season) -> set[int]:
        """Every ticket already ginned into a lot this season."""
        rows = self.connection.execute(
            "SELECT ticket FROM lot_tickets WHERE season = ?", (season.year,)
        )
        return {int(row["ticket"]) for row in rows}

    def lot_for_ticket(self, season: Season, ticket: int) -> LotId | None:
        row = self.connection.execute(
            "SELECT lot FROM lot_tickets WHERE season = ? AND ticket = ?",
            (season.year, ticket),
        ).fetchone()
        return None if row is None else LotId(season, int(row["lot"]))

    def _tickets(self, season: int, number: int) -> tuple[int, ...]:
        rows = self.connection.execute(
            "SELECT ticket FROM lot_tickets WHERE season = ? AND lot = ? ORDER BY ticket",
            (season, number),
        )
        return tuple(int(row["ticket"]) for row in rows)

    def _read(self, row: sqlite3.Row) -> GinRun:
        return GinRun(
            lot=LotId(Season(int(row["season"])), int(row["number"])),
            ginned_on=date.fromisoformat(row["ginned_on"]),
            tickets=self._tickets(int(row["season"]), int(row["number"])),
            seed_cotton=Weight(int(row["seed_cotton"])),
            lint=Weight(int(row["lint"])),
            seed=Weight(int(row["seed"])),
            motes=Weight(int(row["motes"])),
        )


class BaleRepository(Repository):
    """Bales, keyed by the tag the press printed."""

    def add(self, bale: Bale) -> None:
        self.write(
            f"INSERT INTO bales ({BALE_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(bale.bale_id),
                bale.lot.season.year,
                bale.lot.number,
                bale.number,
                bale.pressed_on.isoformat(),
                bale.gross.pounds,
                bale.tare.pounds,
                str(bale.moisture),
            ),
            lambda: ConflictError("bale", str(bale.bale_id), "will not go in the book"),
        )

    def get(self, bale_id: BaleId) -> Bale:
        row = self.connection.execute(
            f"SELECT {BALE_COLUMNS} FROM bales WHERE bale_id = ?", (str(bale_id),)
        ).fetchone()
        if row is None:
            raise NotFoundError("bale", str(bale_id))
        return self._read(row)

    def for_lot(self, lot: LotId) -> list[Bale]:
        rows = self.connection.execute(
            f"SELECT {BALE_COLUMNS} FROM bales WHERE season = ? AND lot = ? ORDER BY number",
            (lot.season.year, lot.number),
        )
        return [self._read(row) for row in rows]

    def for_season(self, season: Season) -> list[Bale]:
        rows = self.connection.execute(
            f"SELECT {BALE_COLUMNS} FROM bales WHERE season = ? ORDER BY number", (season.year,)
        )
        return [self._read(row) for row in rows]

    def lint(self, season: Season) -> Weight:
        return total([bale.net for bale in self.for_season(season)])

    def press(self, season: Season, gin: GinCode) -> BalePress:
        """Rebuild the press counter from what is already in the book."""
        made = BalePress(season, gin)
        made.restore(self.for_season(season))
        return made

    def _read(self, row: sqlite3.Row) -> Bale:
        return Bale(
            bale_id=BaleId(row["bale_id"]),
            lot=LotId(Season(int(row["season"])), int(row["lot"])),
            pressed_on=date.fromisoformat(row["pressed_on"]),
            gross=Weight(int(row["gross"])),
            tare=Weight(int(row["tare"])),
            moisture=Decimal(row["moisture"]),
        )


def _named(refusal: Callable[[], Exception]) -> Callable[[], Exception]:
    """Keep one refusal for a pair of writes that stand or fall together."""
    return refusal
