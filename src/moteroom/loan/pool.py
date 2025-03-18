"""Pooling the season's bales at loan value.

One bale at a time is how the schedule works. What the office actually asks
for is the whole set: how many bales are eligible, what they loan for
together, and what the average rate came out at once the good bales and the
bad ones are put in the same pile.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from moteroom.classing.record import ClassingRecord
from moteroom.core.money import CentsPerPound, Money, total_money
from moteroom.core.weight import Weight, total
from moteroom.loan.value import IneligibleError, rate_for
from moteroom.press.bale import Bale


@dataclass(frozen=True)
class PoolLine:
    """One bale in the pool, priced."""

    bale_id: str
    net: Weight
    rate: CentsPerPound
    value: Money
    color_class: int
    staple: int


@dataclass(frozen=True)
class Pool:
    """Every bale that could be priced, and the ones that could not."""

    lines: tuple[PoolLine, ...]
    ineligible: tuple[tuple[str, str], ...]

    @property
    def bales(self) -> int:
        return len(self.lines)

    @property
    def lint(self) -> Weight:
        return total([line.net for line in self.lines])

    @property
    def value(self) -> Money:
        return total_money([line.value for line in self.lines])

    @property
    def average_rate(self) -> CentsPerPound:
        """Value over weight, which is not the average of the rates."""
        if self.lint.is_zero:
            return CentsPerPound.of(0)
        cents = self.value.amount * Decimal(100) / Decimal(self.lint.pounds)
        return CentsPerPound(cents.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @property
    def average_bale(self) -> Weight:
        if not self.lines:
            return Weight.zero()
        return Weight(self.lint.pounds // self.bales)

    def by_color_class(self) -> dict[int, int]:
        counted: dict[int, int] = {}
        for line in self.lines:
            counted[line.color_class] = counted.get(line.color_class, 0) + 1
        return dict(sorted(counted.items()))

    def by_staple(self) -> dict[int, int]:
        counted: dict[int, int] = {}
        for line in self.lines:
            counted[line.staple] = counted.get(line.staple, 0) + 1
        return dict(sorted(counted.items()))

    def __str__(self) -> str:
        return f"{self.bales} bales, {self.lint}, {self.value} at {self.average_rate}"


def build(pairs: Iterable[tuple[Bale, ClassingRecord]], base: CentsPerPound) -> Pool:
    """Price every bale that has a card, keeping the refusals with a reason."""
    lines: list[PoolLine] = []
    refused: list[tuple[str, str]] = []
    for bale, card in pairs:
        if bale.bale_id != card.bale_id:
            refused.append((str(bale.bale_id), "card is for another bale"))
            continue
        try:
            breakdown = rate_for(card, base)
        except IneligibleError as exc:
            refused.append((str(bale.bale_id), exc.reason))
            continue
        lines.append(
            PoolLine(
                bale_id=str(bale.bale_id),
                net=bale.net,
                rate=breakdown.rate,
                value=breakdown.rate.on(bale.net),
                color_class=card.color.color_class,
                staple=card.staple.thirty_seconds,
            )
        )
    return Pool(tuple(lines), tuple(refused))
