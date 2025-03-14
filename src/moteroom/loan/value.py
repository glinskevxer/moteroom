"""What a classed bale loans for.

The rate is the base rate for the season plus every adjustment the schedule
makes for the card, and the value is that rate on the bale's net weight. The
breakdown is kept rather than just the answer, because a producer who is
unhappy about a number wants to see which line took it off.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import MoteroomError
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.weight import Weight
from moteroom.loan import schedule
from moteroom.press.bale import Bale

ZERO = Decimal("0.00")


class IneligibleError(MoteroomError):
    """A bale the loan will not take at any rate."""

    def __init__(self, bale_id: str, reason: str) -> None:
        super().__init__(f"bale {bale_id}: {reason}")
        self.bale_id = bale_id
        self.reason = reason


@dataclass(frozen=True)
class RateBreakdown:
    """Every line that moved the rate, in the order the office reads them."""

    bale_id: str
    base: CentsPerPound
    color: Decimal
    leaf: Decimal
    staple: Decimal
    micronaire: Decimal
    strength: Decimal
    uniformity: Decimal
    extraneous: Decimal

    @property
    def adjustments(self) -> Decimal:
        return (
            self.color
            + self.leaf
            + self.staple
            + self.micronaire
            + self.strength
            + self.uniformity
            + self.extraneous
        )

    @property
    def rate(self) -> CentsPerPound:
        """The rate the bale loans at, which never goes below nothing."""
        moved = self.base.cents + self.adjustments
        return CentsPerPound(max(moved, ZERO))

    @property
    def is_floored(self) -> bool:
        """Whether the discounts ran past the base rate and were cut off."""
        return self.base.cents + self.adjustments < ZERO

    def lines(self) -> list[tuple[str, Decimal]]:
        """The breakdown as it prints, base first and total last."""
        return [
            ("base", self.base.cents),
            ("color", self.color),
            ("leaf", self.leaf),
            ("staple", self.staple),
            ("micronaire", self.micronaire),
            ("strength", self.strength),
            ("uniformity", self.uniformity),
            ("extraneous", self.extraneous),
            ("rate", self.rate.cents),
        ]

    def __str__(self) -> str:
        return f"bale {self.bale_id} loans at {self.rate}"


def rate_for(card: ClassingRecord, base: CentsPerPound) -> RateBreakdown:
    """Price one card against the schedule."""
    if card.is_below_grade:
        raise IneligibleError(str(card.bale_id), "is below grade")
    extraneous = sum((schedule.extraneous_points(code) for code in card.codes), start=ZERO)
    return RateBreakdown(
        bale_id=str(card.bale_id),
        base=base,
        color=schedule.color_points(card.color.code),
        leaf=schedule.leaf_points(card.leaf.grade),
        staple=schedule.STAPLE.lookup(Decimal(card.staple.thirty_seconds)),
        micronaire=schedule.MICRONAIRE.lookup(card.micronaire.reading),
        strength=schedule.STRENGTH.lookup(card.strength.grams_per_tex),
        uniformity=schedule.UNIFORMITY.lookup(card.uniformity.percent),
        extraneous=extraneous,
    )


def value_for(bale: Bale, card: ClassingRecord, base: CentsPerPound) -> Money:
    """What the bale is worth at loan, on its own net weight."""
    if bale.bale_id != card.bale_id:
        raise IneligibleError(str(bale.bale_id), "was priced against another bale's card")
    return rate_for(card, base).rate.on(bale.net)


def value_on(weight: Weight, card: ClassingRecord, base: CentsPerPound) -> Money:
    """The same rate applied to a weight, for a share rather than a bale."""
    return rate_for(card, base).rate.on(weight)
