"""Classing cards on disc.

A card is written against a bale that is already in the book. The office
sometimes sends a corrected card weeks later, so replacing one has to take the
findings with it rather than leaving the old bark code behind attached to
nothing.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from moteroom.classing.book import ClassingBook
from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.ids import BaleId
from moteroom.core.season import Season

COLUMNS = (
    "bale_id, classed_on, office, micronaire, staple, strength, uniformity, color, leaf, trash"
)


class CardRepository:
    """Classing cards, one per bale, with their findings alongside."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def add(self, card: ClassingRecord) -> None:
        try:
            self._write(card)
        except sqlite3.IntegrityError as exc:
            raise ConflictError("card", str(card.bale_id), "will not go in the book") from exc

    def replace(self, card: ClassingRecord) -> None:
        """Take a corrected card, findings and all."""
        key = str(card.bale_id)
        if not self.has(card.bale_id):
            raise NotFoundError("card", key)
        self.connection.execute("DELETE FROM card_extraneous WHERE bale_id = ?", (key,))
        self.connection.execute("DELETE FROM cards WHERE bale_id = ?", (key,))
        self._write(card)

    def get(self, bale_id: BaleId) -> ClassingRecord:
        row = self.connection.execute(
            f"SELECT {COLUMNS} FROM cards WHERE bale_id = ?", (str(bale_id),)
        ).fetchone()
        if row is None:
            raise NotFoundError("card", str(bale_id))
        return self._read(row)

    def has(self, bale_id: BaleId) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM cards WHERE bale_id = ?", (str(bale_id),)
        ).fetchone()
        return row is not None

    def for_season(self, season: Season) -> list[ClassingRecord]:
        rows = self.connection.execute(
            f"SELECT {COLUMNS} FROM cards WHERE bale_id IN "
            "(SELECT bale_id FROM bales WHERE season = ?) ORDER BY bale_id",
            (season.year,),
        )
        return [self._read(row) for row in rows.fetchall()]

    def book(self, season: Season) -> ClassingBook:
        loaded = ClassingBook(season)
        loaded.extend(self.for_season(season))
        return loaded

    def unclassed(self, season: Season) -> list[BaleId]:
        """Bales in the book with no card back yet."""
        rows = self.connection.execute(
            "SELECT bale_id FROM bales WHERE season = ? "
            "AND bale_id NOT IN (SELECT bale_id FROM cards) ORDER BY number",
            (season.year,),
        )
        return [BaleId(row["bale_id"]) for row in rows]

    def _write(self, card: ClassingRecord) -> None:
        self.connection.execute(
            f"INSERT INTO cards ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(card.bale_id),
                card.classed_on.isoformat(),
                card.office,
                str(card.micronaire.reading),
                card.staple.thirty_seconds,
                str(card.strength.grams_per_tex),
                str(card.uniformity.percent),
                card.color.code,
                card.leaf.grade,
                str(card.trash.percent),
            ),
        )
        self.connection.executemany(
            "INSERT INTO card_extraneous (bale_id, code) VALUES (?, ?)",
            [(str(card.bale_id), code) for code in card.codes],
        )

    def _findings(self, bale_id: str) -> tuple[Extraneous, ...]:
        rows = self.connection.execute(
            "SELECT code FROM card_extraneous WHERE bale_id = ? ORDER BY code", (bale_id,)
        )
        return tuple(Extraneous.parse(row["code"]) for row in rows)

    def _read(self, row: sqlite3.Row) -> ClassingRecord:
        return ClassingRecord(
            bale_id=BaleId(row["bale_id"]),
            classed_on=date.fromisoformat(row["classed_on"]),
            office=row["office"],
            micronaire=Micronaire(Decimal(row["micronaire"])),
            staple=Staple(int(row["staple"])),
            strength=Strength(Decimal(row["strength"])),
            uniformity=Uniformity(Decimal(row["uniformity"])),
            color=ColorGrade(int(row["color"])),
            leaf=LeafGrade(int(row["leaf"])),
            trash=Trash(Decimal(row["trash"])),
            extraneous=self._findings(row["bale_id"]),
        )
