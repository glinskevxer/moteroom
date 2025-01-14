"""Weights.

Every weight a gin writes down is a whole number of pounds. Scale tickets,
bale tags and warehouse receipts all round to the pound before anybody signs
them, so pounds are the only unit stored and fractions are refused rather than
silently truncated.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from moteroom.core.errors import ValidationError

MAX_POUNDS = 10_000_000


@dataclass(frozen=True, order=True)
class Weight:
    """A whole number of pounds, never negative."""

    pounds: int

    def __post_init__(self) -> None:
        if not isinstance(self.pounds, int) or isinstance(self.pounds, bool):
            raise ValidationError("pounds", "must be a whole number of pounds")
        if self.pounds < 0:
            raise ValidationError("pounds", "must not be negative")
        if self.pounds > MAX_POUNDS:
            raise ValidationError("pounds", f"must not exceed {MAX_POUNDS}")

    @classmethod
    def zero(cls) -> Self:
        return cls(0)

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read a weight off a ticket, which may carry commas and a unit."""
        cleaned = text.strip().lower().removesuffix("lb").removesuffix("lbs").strip()
        cleaned = cleaned.replace(",", "")
        if not cleaned:
            raise ValidationError("pounds", "is blank")
        try:
            value = Decimal(cleaned)
        except ArithmeticError as exc:
            raise ValidationError("pounds", f"{text!r} is not a weight") from exc
        if value != value.to_integral_value():
            raise ValidationError("pounds", f"{text!r} is not a whole pound")
        return cls(int(value))

    def __add__(self, other: Weight) -> Weight:
        return Weight(self.pounds + other.pounds)

    def __sub__(self, other: Weight) -> Weight:
        if other.pounds > self.pounds:
            raise ValidationError("pounds", "a weight cannot go below zero")
        return Weight(self.pounds - other.pounds)

    def __str__(self) -> str:
        return f"{self.pounds:,} lb"

    @property
    def is_zero(self) -> bool:
        return self.pounds == 0

    def hundredweight(self) -> Decimal:
        """Pounds expressed in cwt, the unit ginning is charged in."""
        return (Decimal(self.pounds) / Decimal(100)).quantize(Decimal("0.01"))

    def share(self, numerator: int, denominator: int) -> Weight:
        """Split a weight on a lease share, rounding to the nearest pound."""
        if denominator <= 0:
            raise ValidationError("denominator", "must be positive")
        if not 0 <= numerator <= denominator:
            raise ValidationError("numerator", "must lie inside the share")
        scaled = Decimal(self.pounds * numerator) / Decimal(denominator)
        return Weight(int(scaled.to_integral_value(rounding="ROUND_HALF_UP")))


def total(weights: list[Weight]) -> Weight:
    """Add a run of weights, which is the one thing every report does."""
    return Weight(sum(w.pounds for w in weights))
