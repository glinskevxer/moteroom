"""Every producer at a glance.

The season page says how the plant did. This says how each grower did, one
line each, sorted by what they brought in. It is the page the manager takes to
the annual meeting, so the columns are the ones growers argue about: what they
put in, what they got out, and how their turnout sat against everybody else's.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

from moteroom.core.money import Money, total_money
from moteroom.core.weight import Weight, total
from moteroom.reporting.report import Report


class Standing(Protocol):
    """What this page needs to know about a producer.

    It is a shape rather than an import. The thing that gathers a producer's
    season sits above reporting and reads the book, and a report that imported
    it could not be used without one.
    """

    @property
    def producer(self) -> str: ...

    @property
    def modules(self) -> int: ...

    @property
    def seed_cotton(self) -> Weight: ...

    @property
    def bales(self) -> int: ...

    @property
    def lint(self) -> Weight: ...

    @property
    def turnout(self) -> Decimal: ...

    @property
    def against_the_plant(self) -> Decimal: ...

    @property
    def settled(self) -> bool: ...

    @property
    def net(self) -> Money: ...


def summary(standings: Sequence[Standing]) -> Report:
    """One line per producer, most cotton first."""
    ordered = sorted(standings, key=lambda one: (-one.seed_cotton.pounds, one.producer))
    rows = tuple(
        (
            one.producer,
            str(one.modules),
            str(one.seed_cotton.pounds),
            str(one.bales),
            str(one.lint.pounds),
            f"{one.turnout}",
            f"{one.against_the_plant:+}",
            "yes" if one.settled else "no",
        )
        for one in ordered
    )
    return Report(
        title="producers",
        headers=(
            "producer",
            "modules",
            "seed cotton",
            "bales",
            "lint",
            "turnout",
            "against",
            "settled",
        ),
        rows=rows,
        right=(1, 2, 3, 4, 5, 6),
        notes=_notes(ordered),
    )


def _notes(standings: Sequence[Standing]) -> tuple[str, ...]:
    if not standings:
        return ("nobody has ginned yet",)
    settled = sum(1 for one in standings if one.settled)
    return (
        f"{len(standings)} producers, "
        f"{sum(one.modules for one in standings)} modules, "
        f"{total([one.lint for one in standings])} of lint",
        f"{settled} settled, {len(standings) - settled} to go",
        f"turnout runs {spread(standings)}",
    )


def spread(standings: Sequence[Standing]) -> str:
    """The gap between the best and worst turnout, which is the argument."""
    if not standings:
        return "nowhere"
    turnouts = [one.turnout for one in standings]
    return f"{min(turnouts)}% to {max(turnouts)}%"


def owed(standings: Sequence[Standing]) -> Money:
    """What is still to be paid across the producers settled so far."""
    return total_money([one.net for one in standings if one.settled])


def best_turnout(standings: Sequence[Standing]) -> Decimal:
    """The best turnout anybody managed, which somebody always asks."""
    if not standings:
        return Decimal("0.00")
    return max(one.turnout for one in standings)


def total_seed_cotton(standings: Sequence[Standing]) -> Weight:
    """Seed cotton across every producer, which is what came through the gate."""
    return total([one.seed_cotton for one in standings])
