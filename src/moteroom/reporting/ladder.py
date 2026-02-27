"""The schedule as a ladder, with the season's bales on it.

The premium and discount schedule is a set of tables and nobody reads tables.
What people want to see is where their cotton landed: how many bales sat in the
band that pays nothing, how many fell two rungs down, and what those rungs cost
across the whole season.

So each table is printed as a ladder with the count against every rung and the
money that rung moved. A rung with no bales on it still prints, because the
gap is the point.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import Decimal

from moteroom.classing.record import ClassingRecord
from moteroom.core.money import Money
from moteroom.core.reading import share
from moteroom.core.weight import Weight
from moteroom.loan.schedule import (
    COLOR_POINTS,
    LEAF_POINTS,
    MICRONAIRE,
    STAPLE,
    STRENGTH,
    UNIFORMITY,
    BandTable,
)
from moteroom.reporting.report import Report

TABLES: dict[str, BandTable] = {
    "micronaire": MICRONAIRE,
    "staple": STAPLE,
    "strength": STRENGTH,
    "uniformity": UNIFORMITY,
}

READINGS: dict[str, Callable[[ClassingRecord], Decimal]] = {
    "micronaire": lambda card: card.micronaire.reading,
    "staple": lambda card: Decimal(card.staple.thirty_seconds),
    "strength": lambda card: card.strength.grams_per_tex,
    "uniformity": lambda card: card.uniformity.percent,
}


def money_moved(points: Decimal, lint: Weight) -> Money:
    """What a rung was worth across the lint that sat on it."""
    cents = points * Decimal(lint.pounds) / Decimal(100)
    return Money(cents.quantize(Decimal("0.01")))


def band_ladder(measure: str, cards: Sequence[ClassingRecord], net: Weight) -> Report:
    """One table, rung by rung, with the season's bales counted onto it."""
    if measure not in TABLES:
        raise KeyError(measure)
    table = TABLES[measure]
    reading = READINGS[measure]
    per_bale = Weight(net.pounds // len(cards)) if cards else Weight.zero()
    rows = []
    for band in table.bands:
        on_it = [card for card in cards if band.low <= reading(card) <= band.high]
        lint = Weight(per_bale.pounds * len(on_it))
        rows.append(
            (
                f"{band.low} to {band.high}",
                f"{band.points:+}",
                str(len(on_it)),
                str(share(len(on_it), len(cards))),
                str(money_moved(band.points, lint)),
            )
        )
    return Report(
        title=f"{measure} ladder",
        headers=("band", "cents", "bales", "percent", "moved"),
        rows=tuple(rows),
        right=(1, 2, 3, 4),
        notes=(f"{len(cards)} cards, {net} of lint",),
    )


def grade_ladder(cards: Sequence[ClassingRecord], net: Weight) -> Report:
    """Colour and leaf together, which is how a grade is quoted."""
    per_bale = Weight(net.pounds // len(cards)) if cards else Weight.zero()
    counted: dict[int, int] = {}
    for card in cards:
        counted[card.color.code] = counted.get(card.color.code, 0) + 1
    rows = []
    for code in sorted(COLOR_POINTS, key=lambda one: (-COLOR_POINTS[one], one)):
        bales = counted.get(code, 0)
        lint = Weight(per_bale.pounds * bales)
        rows.append(
            (
                str(code),
                f"{COLOR_POINTS[code]:+}",
                str(bales),
                str(share(bales, len(cards))),
                str(money_moved(COLOR_POINTS[code], lint)),
            )
        )
    return Report(
        title="colour ladder",
        headers=("code", "cents", "bales", "percent", "moved"),
        rows=tuple(rows),
        right=(1, 2, 3, 4),
        notes=(f"{len(cards)} cards, {len(counted)} of {len(COLOR_POINTS)} codes used",),
    )


def leaf_ladder(cards: Sequence[ClassingRecord], net: Weight) -> Report:
    """The leaf ladder, which only ever falls."""
    per_bale = Weight(net.pounds // len(cards)) if cards else Weight.zero()
    counted: dict[int, int] = {}
    for card in cards:
        counted[card.leaf.grade] = counted.get(card.leaf.grade, 0) + 1
    rows = tuple(
        (
            str(grade),
            f"{LEAF_POINTS[grade]:+}",
            str(counted.get(grade, 0)),
            str(share(counted.get(grade, 0), len(cards))),
            str(
                money_moved(LEAF_POINTS[grade], Weight(per_bale.pounds * counted.get(grade, 0)))
            ),
        )
        for grade in sorted(LEAF_POINTS)
    )
    return Report(
        title="leaf ladder",
        headers=("grade", "cents", "bales", "percent", "moved"),
        rows=rows,
        right=(1, 2, 3, 4),
        notes=(f"{len(cards)} cards",),
    )
