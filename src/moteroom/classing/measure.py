"""The instrument readings on a classing card.

Every one of these comes off a high volume instrument line at a classing
office, and every one has a range the instrument can report and a step it
reports in. A reading outside the range is a keying error rather than an
unusual bale, so it is refused here and never stored.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Self

from moteroom.core.errors import ValidationError
from moteroom.core.reading import HUNDREDTH, TENTH, checked

MIN_MIKE = Decimal("2.0")
MAX_MIKE = Decimal("6.9")
PREMIUM_MIKE_LOW = Decimal("3.7")
PREMIUM_MIKE_HIGH = Decimal("4.2")

MIN_STAPLE = 24
MAX_STAPLE = 45
THIRTY_SECONDS = Decimal(32)

MIN_STRENGTH = Decimal("15.0")
MAX_STRENGTH = Decimal("40.0")

MIN_UNIFORMITY = Decimal("70.0")
MAX_UNIFORMITY = Decimal("90.0")

MIN_TRASH = Decimal("0.00")
MAX_TRASH = Decimal("9.99")


@dataclass(frozen=True, order=True)
class Micronaire:
    """Fineness and maturity together, which is what mike actually measures."""

    reading: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "reading", checked(self.reading, "mike", MIN_MIKE, MAX_MIKE, TENTH)
        )

    @classmethod
    def parse(cls, text: str) -> Self:
        return cls(Decimal(text.strip()))

    @property
    def is_premium(self) -> bool:
        """The base range, where mike neither adds nor takes anything off."""
        return PREMIUM_MIKE_LOW <= self.reading <= PREMIUM_MIKE_HIGH

    @property
    def is_low(self) -> bool:
        return self.reading < PREMIUM_MIKE_LOW

    def __str__(self) -> str:
        return f"{self.reading:.1f}"


@dataclass(frozen=True, order=True)
class Staple:
    """Fibre length in thirty seconds of an inch, the way it is traded."""

    thirty_seconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.thirty_seconds, int) or isinstance(self.thirty_seconds, bool):
            raise ValidationError("staple", "must be a whole thirty second")
        if not MIN_STAPLE <= self.thirty_seconds <= MAX_STAPLE:
            raise ValidationError("staple", f"{self.thirty_seconds} is off the staple chart")

    @classmethod
    def from_inches(cls, inches: Decimal) -> Self:
        """Convert an instrument length in inches to the traded staple."""
        if inches != inches.quantize(HUNDREDTH):
            raise ValidationError("length", f"{inches} is finer than a hundredth")
        stapled = (inches * THIRTY_SECONDS).to_integral_value(rounding=ROUND_HALF_UP)
        return cls(int(stapled))

    @property
    def inches(self) -> Decimal:
        exact = Decimal(self.thirty_seconds) / THIRTY_SECONDS
        return exact.quantize(HUNDREDTH, rounding=ROUND_HALF_UP)

    def __str__(self) -> str:
        return str(self.thirty_seconds)


@dataclass(frozen=True, order=True)
class Strength:
    """Grams per tex, which is what breaks in the spinning mill."""

    grams_per_tex: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "grams_per_tex",
            checked(self.grams_per_tex, "strength", MIN_STRENGTH, MAX_STRENGTH, TENTH),
        )

    def __str__(self) -> str:
        return f"{self.grams_per_tex:.1f}"


@dataclass(frozen=True, order=True)
class Uniformity:
    """Length uniformity as a percentage of the mean length."""

    percent: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "percent",
            checked(self.percent, "uniformity", MIN_UNIFORMITY, MAX_UNIFORMITY, TENTH),
        )

    def __str__(self) -> str:
        return f"{self.percent:.1f}"


@dataclass(frozen=True, order=True)
class Trash:
    """Surface trash by area, which the instrument reports as a percentage."""

    percent: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "percent", checked(self.percent, "trash", MIN_TRASH, MAX_TRASH, HUNDREDTH)
        )

    def __str__(self) -> str:
        return f"{self.percent:.2f}"
