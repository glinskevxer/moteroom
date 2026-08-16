"""How long the office is taking.

A bale cannot be sold until it is classed, and the gap between the day it was
pressed and the day the card came back is time the cotton sits doing nothing.
The office is not slow every week: it is slow the week everybody in the valley
gins at once, and the only way to see that is to look at the gap week by week
rather than as one average over the season.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ValidationError
from moteroom.press.bale import Bale
from moteroom.reporting.report import Report

HUNDREDTH = Decimal("0.01")
PROMPT_DAYS = 7


def gap(bale: Bale, card: ClassingRecord) -> int:
    """Days from the press to the card, which is what the office is judged on."""
    if card.bale_id != bale.bale_id:
        raise ValidationError("card", "is for another bale")
    if card.classed_on < bale.pressed_on:
        raise ValidationError("card", "is dated before the bale was pressed")
    return (card.classed_on - bale.pressed_on).days


def week_of(day: date) -> date:
    """The Monday of the week a date falls in."""
    return day - timedelta(days=day.weekday())


def average(gaps: Sequence[int]) -> Decimal:
    """The average gap, to a hundredth of a day."""
    if not gaps:
        return Decimal("0.00")
    return (Decimal(sum(gaps)) / Decimal(len(gaps))).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)


def turnaround(pairs: Sequence[tuple[Bale, ClassingRecord]]) -> Report:
    """The gap week by week, by the week the bale was pressed in."""
    weeks: dict[date, list[int]] = {}
    for bale, card in pairs:
        weeks.setdefault(week_of(bale.pressed_on), []).append(gap(bale, card))
    rows = tuple(
        (
            week.isoformat(),
            str(len(gaps)),
            str(average(gaps)),
            str(min(gaps)),
            str(max(gaps)),
            "prompt" if average(gaps) <= PROMPT_DAYS else "slow",
        )
        for week, gaps in sorted(weeks.items())
    )
    everything = [gap(bale, card) for bale, card in pairs]
    return Report(
        title="classing turnaround",
        headers=("week", "bales", "average", "fastest", "slowest", "reading"),
        rows=rows,
        right=(1, 2, 3, 4),
        notes=(
            f"{len(everything)} cards, {average(everything)} days on average"
            if everything
            else "no cards back yet",
        ),
    )


def slowest(
    pairs: Sequence[tuple[Bale, ClassingRecord]], count: int = 5
) -> list[tuple[str, int]]:
    """The bales that waited longest, worst first."""
    if count < 1:
        raise ValidationError("count", "must be at least one")
    measured = [(str(bale.bale_id), gap(bale, card)) for bale, card in pairs]
    return sorted(measured, key=lambda one: (-one[1], one[0]))[:count]


def waiting(bales: Sequence[Bale], classed: set[str], as_of: date) -> list[tuple[str, int]]:
    """Bales pressed and still not classed, longest first."""
    found = [
        (str(one.bale_id), (as_of - one.pressed_on).days)
        for one in bales
        if str(one.bale_id) not in classed and one.pressed_on <= as_of
    ]
    return sorted(found, key=lambda one: (-one[1], one[0]))
