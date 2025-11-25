"""Closing a season.

A season is not closed because the last bale went out. It is closed when
nothing is left hanging: every ticket ginned, every bale classed and placed,
every producer settled, and the press agreeing with the lot sheets. Each of
those is a check that either passes or names what is outstanding, and the
season closes only when all of them pass.

Nothing here writes. Closing is a statement about the book, so it is worked out
fresh every time it is asked for rather than being a flag somebody set once.
"""

from __future__ import annotations

from dataclasses import dataclass

from moteroom.core.season import Season
from moteroom.core.weight import total
from moteroom.ginning.reconcile import reconcile
from moteroom.service import inventory
from moteroom.storage.book import Book
from moteroom.storage.registry import Repositories


@dataclass(frozen=True)
class Check:
    """One thing that has to be true before a season closes."""

    name: str
    passed: bool
    detail: str

    def __str__(self) -> str:
        return f"{'ok  ' if self.passed else 'open'} {self.name}: {self.detail}"


@dataclass(frozen=True)
class Closing:
    """Every check, and whether the season can close."""

    season: Season
    checks: tuple[Check, ...]

    @property
    def can_close(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def outstanding(self) -> tuple[Check, ...]:
        return tuple(check for check in self.checks if not check.passed)

    def named(self, name: str) -> Check:
        for check in self.checks:
            if check.name == name:
                return check
        raise KeyError(name)

    def __str__(self) -> str:
        if self.can_close:
            return f"{self.season} can close"
        return f"{self.season} has {len(self.outstanding)} things outstanding"


def check(book: Book, season: Season) -> Closing:
    """Work out whether a season is finished with."""
    repos = Repositories(book.connection)
    tickets = repos.tickets.book(season)
    ginned = repos.lots.assigned_tickets(season)
    waiting = [one.number for one in tickets.live() if one.number not in ginned]
    unclassed = repos.cards.unclassed(season)
    bales = repos.bales.for_season(season)

    drifting = []
    for run in repos.lots.for_season(season):
        pressed = repos.bales.for_lot(run.lot)
        if (
            pressed
            and not reconcile(run, total([one.net for one in pressed]), len(pressed)).agrees
        ):
            drifting.append(str(run.lot))

    settled = {one.producer for one in repos.statements.for_season(season)}
    unsettled = [code for code in tickets.producers() if code not in settled]
    placed = inventory.take(book, season)
    at_gin = placed.counts()[inventory.AT_THE_GIN]

    return Closing(
        season,
        (
            Check(
                "modules ginned",
                not waiting,
                "all ginned" if not waiting else f"{len(waiting)} still in the yard",
            ),
            Check(
                "bales classed",
                not unclassed,
                f"{len(bales)} classed" if not unclassed else f"{len(unclassed)} with no card",
            ),
            Check(
                "lots reconcile",
                not drifting,
                "press agrees" if not drifting else f"{', '.join(drifting)} do not agree",
            ),
            Check(
                "bales placed",
                at_gin == 0 and placed.balances,
                "all placed"
                if at_gin == 0 and placed.balances
                else f"{at_gin} still at the gin",
            ),
            Check(
                "producers settled",
                not unsettled,
                "all settled" if not unsettled else f"{', '.join(unsettled)} not settled",
            ),
        ),
    )
