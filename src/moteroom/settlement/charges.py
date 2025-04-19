"""What the gin charges to gin.

Ginning is quoted per hundredweight of seed cotton, not per bale, because that
is what the plant is actually handling. Bagging and ties are per bale because
that is what they wrap. Drying is only charged on the cotton that had to be
dried. A per bale minimum sits under the whole thing so a producer who brings
in three light modules still covers the cost of running them.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.core.weight import Weight

CENT = Decimal("0.01")


@dataclass(frozen=True)
class ChargeSchedule:
    """The plant's posted charges for a season."""

    ginning_per_cwt: Money
    bagging_and_ties: Money
    module_handling: Money
    drying_per_cwt: Money = Money.zero()
    minimum_per_bale: Money = Money.zero()

    def __post_init__(self) -> None:
        for name, amount in (
            ("ginning_per_cwt", self.ginning_per_cwt),
            ("bagging_and_ties", self.bagging_and_ties),
            ("module_handling", self.module_handling),
            ("drying_per_cwt", self.drying_per_cwt),
            ("minimum_per_bale", self.minimum_per_bale),
        ):
            if amount.amount < 0:
                raise ValidationError(name, "must not be negative")


@dataclass(frozen=True)
class GinBill:
    """The charges on one producer's cotton, kept as the lines that print."""

    ginning: Money
    bagging_and_ties: Money
    module_handling: Money
    drying: Money
    minimum_uplift: Money

    @property
    def total(self) -> Money:
        return (
            self.ginning
            + self.bagging_and_ties
            + self.module_handling
            + self.drying
            + self.minimum_uplift
        )

    def lines(self) -> list[tuple[str, Money]]:
        return [
            ("ginning", self.ginning),
            ("bagging and ties", self.bagging_and_ties),
            ("module handling", self.module_handling),
            ("drying", self.drying),
            ("minimum", self.minimum_uplift),
            ("total", self.total),
        ]

    def __str__(self) -> str:
        return f"gin charges {self.total}"


def _on_cwt(rate: Money, weight: Weight) -> Money:
    """A rate per hundredweight applied to a weight, to the cent."""
    amount = rate.amount * weight.hundredweight()
    return Money(amount.quantize(CENT, rounding=ROUND_HALF_UP))


def bill(
    schedule: ChargeSchedule,
    seed_cotton: Weight,
    bales: int,
    modules: int,
    dried: Weight | None = None,
) -> GinBill:
    """Charge one producer's cotton against the posted schedule."""
    if bales < 0 or modules < 0:
        raise ValidationError("count", "must not be negative")
    if bales == 0 and not seed_cotton.is_zero:
        raise ValidationError("bales", "seed cotton that made no bales is not billable")
    dried_weight = dried or Weight.zero()
    if dried_weight.pounds > seed_cotton.pounds:
        raise ValidationError("dried", "more was dried than came in")
    ginning = _on_cwt(schedule.ginning_per_cwt, seed_cotton)
    bagging = schedule.bagging_and_ties.times(bales)
    handling = schedule.module_handling.times(modules)
    drying = _on_cwt(schedule.drying_per_cwt, dried_weight)
    before_minimum = ginning + bagging + handling + drying
    floor = schedule.minimum_per_bale.times(bales)
    uplift = floor - before_minimum if floor > before_minimum else Money.zero()
    return GinBill(ginning, bagging, handling, drying, uplift)
