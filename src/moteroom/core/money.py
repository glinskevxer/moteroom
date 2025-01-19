"""Money, and the cents-per-pound rate lint is priced in.

Two types, because a gin quotes two different things. Settlement lines are
dollars and cents. Loan rates, ginning charges and seed prices are quoted in
cents per pound and carry two decimals of a cent, so 52.34 cents means
52.34 and never 52.3400000001. Both are exact and neither is a float.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Self

from moteroom.core.errors import ValidationError
from moteroom.core.weight import Weight

CENT = Decimal("0.01")
HUNDREDTH_CENT = Decimal("0.01")


def _decimal(text: str, field: str) -> Decimal:
    cleaned = text.strip().replace(",", "").replace("$", "")
    if not cleaned:
        raise ValidationError(field, "is blank")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValidationError(field, f"{text!r} is not a number") from exc


@dataclass(frozen=True, order=True)
class Money:
    """Dollars and cents. May be negative, since deductions are money too."""

    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise ValidationError("amount", "must be a Decimal")
        if self.amount != self.amount.quantize(CENT):
            raise ValidationError("amount", f"{self.amount} is finer than a cent")

    @classmethod
    def zero(cls) -> Self:
        return cls(Decimal("0.00"))

    @classmethod
    def dollars(cls, value: int | str) -> Self:
        return cls(Decimal(value).quantize(CENT))

    @classmethod
    def parse(cls, text: str) -> Self:
        value = _decimal(text, "amount")
        if value != value.quantize(CENT):
            raise ValidationError("amount", f"{text!r} is finer than a cent")
        return cls(value.quantize(CENT))

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        return Money(self.amount - other.amount)

    def __neg__(self) -> Money:
        return Money(-self.amount)

    def __str__(self) -> str:
        sign = "-" if self.amount < 0 else ""
        return f"{sign}${abs(self.amount):,.2f}"

    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    def times(self, count: int) -> Money:
        return Money(self.amount * count)

    def allocate(self, shares: list[int]) -> list[Money]:
        """Split by whole shares, giving the remainder cents out in order.

        A settlement that splits three ways must still add back to what it
        started as, so the pennies go somewhere rather than being rounded away.
        """
        if not shares:
            raise ValidationError("shares", "is empty")
        if any(s < 0 for s in shares):
            raise ValidationError("shares", "must not be negative")
        denominator = sum(shares)
        if denominator == 0:
            raise ValidationError("shares", "must not all be zero")
        cents = int((self.amount / CENT).to_integral_value(rounding=ROUND_HALF_UP))
        out = [cents * s // denominator for s in shares]
        remainder = cents - sum(out)
        step = 1 if remainder >= 0 else -1
        index = 0
        while remainder != 0:
            if shares[index % len(shares)] > 0:
                out[index % len(shares)] += step
                remainder -= step
            index += 1
        return [Money(Decimal(c) * CENT) for c in out]


def total_money(amounts: list[Money]) -> Money:
    """Add a column of money, which is what every statement footer does."""
    return Money(sum((m.amount for m in amounts), Decimal("0.00")))


@dataclass(frozen=True, order=True)
class CentsPerPound:
    """A price in cents per pound, carried to a hundredth of a cent."""

    cents: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.cents, Decimal):
            raise ValidationError("cents", "must be a Decimal")
        if self.cents != self.cents.quantize(HUNDREDTH_CENT):
            raise ValidationError("cents", f"{self.cents} is finer than a hundredth")

    @classmethod
    def of(cls, value: int | str) -> Self:
        return cls(Decimal(value).quantize(HUNDREDTH_CENT))

    @classmethod
    def parse(cls, text: str) -> Self:
        value = _decimal(text.removesuffix("c"), "cents")
        if value != value.quantize(HUNDREDTH_CENT):
            raise ValidationError("cents", f"{text!r} is finer than a hundredth")
        return cls(value.quantize(HUNDREDTH_CENT))

    def __add__(self, other: CentsPerPound) -> CentsPerPound:
        return CentsPerPound(self.cents + other.cents)

    def __sub__(self, other: CentsPerPound) -> CentsPerPound:
        return CentsPerPound(self.cents - other.cents)

    def __str__(self) -> str:
        return f"{self.cents:.2f}c"

    def on(self, weight: Weight) -> Money:
        """What this rate is worth on a weight, rounded to the cent."""
        dollars = self.cents * Decimal(weight.pounds) / Decimal(100)
        return Money(dollars.quantize(CENT, rounding=ROUND_HALF_UP))
