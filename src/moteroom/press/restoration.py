"""Putting moisture back into the lint before it is baled.

Lint comes off the driers too dry to press well, and moisture is restored at
the press so the bale holds its shape. That is legitimate and it is also how a
gin could add weight it did not grow, so the plant works to a ceiling and
records what it added.

The arithmetic is on dry matter. Lint at 5 percent moisture is 95 percent
fibre, and that fibre weight does not change when water is added, so the
restored weight is the dry weight divided by one minus the new moisture.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.reading import TENTH, checked
from moteroom.core.weight import Weight

MIN_MOISTURE = Decimal("3.0")
MAX_MOISTURE = Decimal("10.0")
CEILING = Decimal("7.5")
HUNDREDTH = Decimal("0.01")


@dataclass(frozen=True)
class Restoration:
    """One press worth of restoration, in and out."""

    dry_weight: Weight
    before: Decimal
    after: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "before", checked(self.before, "before", MIN_MOISTURE, MAX_MOISTURE, TENTH)
        )
        object.__setattr__(
            self, "after", checked(self.after, "after", MIN_MOISTURE, MAX_MOISTURE, TENTH)
        )
        if self.after < self.before:
            raise ValidationError("after", "restoration does not take moisture out")
        if self.dry_weight.is_zero:
            raise ValidationError("dry_weight", "there is nothing to restore")

    @property
    def fibre(self) -> Decimal:
        """The dry fibre in the lint, which does not change."""
        return Decimal(self.dry_weight.pounds) * (Decimal(100) - self.before) / Decimal(100)

    @property
    def restored(self) -> Weight:
        """What the lint weighs once the moisture is back in it."""
        weight = self.fibre * Decimal(100) / (Decimal(100) - self.after)
        return Weight(int(weight.to_integral_value(rounding=ROUND_HALF_UP)))

    @property
    def added(self) -> Weight:
        """The water, which is the part somebody will ask about."""
        return self.restored - self.dry_weight

    @property
    def over_ceiling(self) -> bool:
        """Whether the bale left the press wetter than the plant allows."""
        return self.after > CEILING

    @property
    def gain(self) -> Decimal:
        """The added weight as a percentage of what went in."""
        if self.dry_weight.is_zero:
            return Decimal("0.00")
        return (
            Decimal(self.added.pounds) * Decimal(100) / Decimal(self.dry_weight.pounds)
        ).quantize(HUNDREDTH, rounding=ROUND_HALF_UP)

    def value_of_water(self, rate: CentsPerPound) -> Money:
        """What the added weight would be worth at a lint price."""
        return rate.on(self.added)

    def __str__(self) -> str:
        verdict = " over the ceiling" if self.over_ceiling else ""
        return f"{self.added} restored, {self.gain}%{verdict}"


def to_target(dry_weight: Weight, before: Decimal, target: Decimal = CEILING) -> Restoration:
    """Restore to a target moisture, refusing a target above the ceiling."""
    if target > CEILING:
        raise ValidationError("target", f"the plant works to {CEILING} percent")
    return Restoration(dry_weight, before, target)
