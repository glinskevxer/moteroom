"""The one page the season gets remembered by.

Everything else is a working report. This is the page that goes on the wall in
the office and gets compared against last year, so it carries the handful of
numbers a gin is actually judged on and it states each of them the same way
every year: how much came in, how much lint went out, what it turned out at,
and what it was worth.

It takes numbers rather than a book. Two seasons are compared by building this
twice, and a report that reached into storage could not do that.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from moteroom.core.money import Money
from moteroom.core.reading import ratio, share
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.reporting.report import Report


@dataclass(frozen=True)
class Facts:
    """What a season came to, before anybody formats it."""

    season: Season
    producers: int
    modules: int
    seed_cotton: Weight
    lint: Weight
    seed: Weight
    motes: Weight
    bales: int
    classed: int
    white: int
    loan_value: Money
    settled: int

    @property
    def turnout(self) -> Decimal:
        return share(self.lint.pounds, self.seed_cotton.pounds)

    @property
    def average_bale(self) -> Weight:
        if self.bales == 0:
            return Weight.zero()
        return Weight(self.lint.pounds // self.bales)

    @property
    def bales_per_module(self) -> Decimal:
        if self.modules == 0:
            return Decimal("0.00")
        return (Decimal(self.bales) / Decimal(self.modules)).quantize(Decimal("0.01"))

    @property
    def white_share(self) -> Decimal:
        return share(self.white, self.classed)

    @property
    def classed_share(self) -> Decimal:
        return share(self.classed, self.bales)

    @property
    def value_per_bale(self) -> Money:
        if self.bales == 0:
            return Money.zero()
        return self.loan_value.allocate([1] * self.bales)[0]


def summary(facts: Facts) -> Report:
    """The season on one page."""
    rows = (
        ("producers", str(facts.producers)),
        ("modules", str(facts.modules)),
        ("seed cotton", str(facts.seed_cotton)),
        ("lint", str(facts.lint)),
        ("seed", str(facts.seed)),
        ("motes", str(facts.motes)),
        ("turnout", f"{facts.turnout}%"),
        ("bales", str(facts.bales)),
        ("average bale", str(facts.average_bale)),
        ("bales a module", str(facts.bales_per_module)),
        ("classed", f"{facts.classed} ({facts.classed_share}%)"),
        ("white", f"{facts.white} ({facts.white_share}%)"),
        ("loan value", str(facts.loan_value)),
        ("value a bale", str(facts.value_per_bale)),
        ("settled", str(facts.settled)),
    )
    return Report(
        title=f"season {facts.season}",
        headers=("measure", "value"),
        rows=rows,
        right=(1,),
        notes=(f"{facts.bales} bales off {facts.modules} modules",),
    )


def against(this: Facts, last: Facts) -> Report:
    """This season beside the last one, with the move between them."""
    if this.season == last.season:
        raise ValueError("a season does not compare against itself")
    rows = (
        ("modules", str(last.modules), str(this.modules), _move(this.modules, last.modules)),
        (
            "seed cotton",
            str(last.seed_cotton.pounds),
            str(this.seed_cotton.pounds),
            _move(this.seed_cotton.pounds, last.seed_cotton.pounds),
        ),
        (
            "lint",
            str(last.lint.pounds),
            str(this.lint.pounds),
            _move(this.lint.pounds, last.lint.pounds),
        ),
        ("bales", str(last.bales), str(this.bales), _move(this.bales, last.bales)),
        ("turnout", f"{last.turnout}", f"{this.turnout}", ""),
    )
    return Report(
        title=f"{this.season} against {last.season}",
        headers=("measure", str(last.season), str(this.season), "move"),
        rows=rows,
        right=(1, 2, 3),
    )


def _move(now: int, before: int) -> str:
    if before == 0:
        return "-"
    moved = ratio(now - before, before)
    return f"+{moved}%" if moved > 0 else f"{moved}%"
