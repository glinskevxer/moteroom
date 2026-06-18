"""What seasons a book holds.

A book carries whatever seasons somebody put in it, and there is no list of
them anywhere: they are implied by the rows. So the list is worked out by
asking every table that carries a season what it has, which also answers the
question behind it, which is how much of each season is in there.
"""

from __future__ import annotations

from dataclasses import dataclass

from moteroom.core.season import Season
from moteroom.storage.repository import Repository

TABLES = (
    "tickets",
    "lots",
    "bales",
    "receipts",
    "statements",
    "contracts",
    "cheques",
    "season_rates",
    "audit",
)


@dataclass(frozen=True)
class Held:
    """One season and how much of it the book carries."""

    season: Season
    tickets: int
    lots: int
    bales: int
    statements: int

    @property
    def is_empty(self) -> bool:
        return not any((self.tickets, self.lots, self.bales, self.statements))

    @property
    def is_settled(self) -> bool:
        return self.statements > 0

    def __str__(self) -> str:
        if self.is_empty:
            return f"{self.season} nothing in it"
        return (
            f"{self.season} {self.tickets} tickets, {self.lots} lots, "
            f"{self.bales} bales, {self.statements} settled"
        )


class SeasonRepository(Repository):
    """The seasons a book holds, worked out from the rows."""

    def years(self) -> list[Season]:
        """Every season anything in the book belongs to, oldest first."""
        found: set[int] = set()
        for table in TABLES:
            column = "season"
            if table == "receipts":
                continue
            for row in self.rows(f"SELECT DISTINCT {column} AS year FROM {table}"):
                found.add(int(row["year"]))
        return [Season(year) for year in sorted(found)]

    def held(self, season: Season) -> Held:
        """How much of one season the book carries."""
        return Held(
            season=season,
            tickets=self.scalar(
                "SELECT count(*) FROM tickets WHERE season = ?", (season.year,)
            ),
            lots=self.scalar("SELECT count(*) FROM lots WHERE season = ?", (season.year,)),
            bales=self.scalar("SELECT count(*) FROM bales WHERE season = ?", (season.year,)),
            statements=self.scalar(
                "SELECT count(*) FROM statements WHERE season = ?", (season.year,)
            ),
        )

    def all(self) -> list[Held]:
        """Every season the book holds, oldest first."""
        return [self.held(season) for season in self.years()]

    def latest(self) -> Season | None:
        """The most recent season in the book, if there is one."""
        years = self.years()
        return years[-1] if years else None
