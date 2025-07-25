"""What the season classed like.

The office manager wants three things off the cards: where the bales landed on
the colour chart, how the staple ran, and whether the plant is putting bark in
the bales. All three are counts over the same set of cards, so they are built
the same way and only the key changes.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import ROUND_HALF_UP, Decimal

from moteroom.classing.color import CLASS_NAMES
from moteroom.classing.record import ClassingRecord
from moteroom.reporting.report import Report

HUNDREDTH = Decimal("0.01")


def share(count: int, whole: int) -> Decimal:
    """A count as a percentage of a whole, which is nothing when there is none."""
    if whole <= 0:
        return Decimal("0.00")
    return (Decimal(count) * Decimal(100) / Decimal(whole)).quantize(
        HUNDREDTH, rounding=ROUND_HALF_UP
    )


def _counted(
    cards: Sequence[ClassingRecord],
    key: Callable[[ClassingRecord], str],
) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for card in cards:
        name = key(card)
        counts[name] = counts.get(name, 0) + 1
    return sorted(counts.items())


def _distribution(
    title: str,
    label: str,
    cards: Sequence[ClassingRecord],
    key: Callable[[ClassingRecord], str],
    right: tuple[int, ...] = (1, 2),
) -> Report:
    counts = _counted(cards, key)
    rows = tuple((name, str(count), str(share(count, len(cards)))) for name, count in counts)
    return Report(
        title=title,
        headers=(label, "bales", "percent"),
        rows=rows,
        right=right,
        notes=(f"{len(cards)} cards",),
    )


def colour_distribution(cards: Sequence[ClassingRecord]) -> Report:
    """Bales by colour code, which is the one the buyer asks about."""
    return _distribution("colour", "code", cards, lambda card: str(card.color))


def class_distribution(cards: Sequence[ClassingRecord]) -> Report:
    """Bales by colour class rather than by code."""
    return _distribution(
        "colour class", "class", cards, lambda card: CLASS_NAMES[card.color.color_class]
    )


def leaf_distribution(cards: Sequence[ClassingRecord]) -> Report:
    return _distribution("leaf", "grade", cards, lambda card: str(card.leaf))


def staple_distribution(cards: Sequence[ClassingRecord]) -> Report:
    return _distribution("staple", "staple", cards, lambda card: str(card.staple))


def findings_report(cards: Sequence[ClassingRecord]) -> Report:
    """Extraneous matter by code, and who caused it."""
    counts: dict[str, int] = {}
    for card in cards:
        for finding in card.extraneous:
            counts[finding.code] = counts.get(finding.code, 0) + 1
    rows = tuple(
        (code, str(count), str(share(count, len(cards))))
        for code, count in sorted(counts.items())
    )
    gin_faults = sum(1 for card in cards if card.gin_faults)
    return Report(
        title="extraneous matter",
        headers=("code", "bales", "percent"),
        rows=rows,
        right=(1, 2),
        notes=(
            f"{len(cards)} cards",
            f"{gin_faults} carry something the plant caused",
        ),
    )


def averages(cards: Sequence[ClassingRecord]) -> Report:
    """The season's averages, which is what goes on the wall."""
    if not cards:
        return Report(
            title="averages",
            headers=("measure", "value"),
            rows=(),
            notes=("no cards back yet",),
        )
    count = len(cards)
    mike = sum((card.micronaire.reading for card in cards), Decimal(0)) / count
    staple = sum((Decimal(card.staple.thirty_seconds) for card in cards), Decimal(0)) / count
    strength = sum((card.strength.grams_per_tex for card in cards), Decimal(0)) / count
    uniformity = sum((card.uniformity.percent for card in cards), Decimal(0)) / count
    white = sum(1 for card in cards if card.color.is_white)
    barky = sum(1 for card in cards if card.has_bark)
    rows = (
        ("micronaire", str(mike.quantize(HUNDREDTH, rounding=ROUND_HALF_UP))),
        ("staple", str(staple.quantize(HUNDREDTH, rounding=ROUND_HALF_UP))),
        ("strength", str(strength.quantize(HUNDREDTH, rounding=ROUND_HALF_UP))),
        ("uniformity", str(uniformity.quantize(HUNDREDTH, rounding=ROUND_HALF_UP))),
        ("white", f"{share(white, count)}%"),
        ("bark", f"{share(barky, count)}%"),
    )
    return Report(
        title="averages",
        headers=("measure", "value"),
        rows=rows,
        right=(1,),
        notes=(f"{count} cards",),
    )
