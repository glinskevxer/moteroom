"""Colour grade, which is two digits and neither of them is a number.

A colour grade reads as a two digit code. The second digit is the colour
class, running white, light spotted, spotted, tinged, yellow stained. The
first digit is the grade inside that class, running good middling down to good
ordinary. So 41 is strict low middling white and 31 is middling white, and 41
is worth less than 31 even though it is the larger number.

The instrument reports reflectance as Rd and yellowness as plus b, and the
classing office reads a code off a chart. The chart here is stated as bands
rather than drawn, because the gin only ever needs the code back.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from moteroom.core.errors import ValidationError
from moteroom.core.reading import TENTH, checked

MIN_RD = Decimal("40.0")
MAX_RD = Decimal("85.0")
MIN_PLUS_B = Decimal("4.0")
MAX_PLUS_B = Decimal("18.0")

CLASS_NAMES = {
    1: "white",
    2: "light spotted",
    3: "spotted",
    4: "tinged",
    5: "yellow stained",
}

GRADE_NAMES = {
    1: "good middling",
    2: "strict middling",
    3: "middling",
    4: "strict low middling",
    5: "low middling",
    6: "strict good ordinary",
    7: "good ordinary",
}

# A class is the first one whose yellowness ceiling and reflectance floor the
# bale sits inside. Anything below all of them is yellow stained.
CLASS_LIMITS: tuple[tuple[int, Decimal, Decimal], ...] = (
    (1, Decimal("9.0"), Decimal("68.0")),
    (2, Decimal("10.5"), Decimal("64.0")),
    (3, Decimal("12.5"), Decimal("58.0")),
    (4, Decimal("14.5"), Decimal("52.0")),
)

# Inside a class the grade is a reflectance band, read from the top down.
GRADE_BANDS: dict[int, tuple[tuple[int, Decimal], ...]] = {
    1: (
        (1, Decimal("79.0")),
        (2, Decimal("76.0")),
        (3, Decimal("73.0")),
        (4, Decimal("70.0")),
        (5, Decimal("68.0")),
        (6, Decimal("64.0")),
        (7, Decimal("0.0")),
    ),
    2: ((2, Decimal("74.0")), (3, Decimal("70.0")), (4, Decimal("66.0")), (5, Decimal("0.0"))),
    3: ((3, Decimal("68.0")), (4, Decimal("63.0")), (5, Decimal("58.0")), (6, Decimal("0.0"))),
    4: ((4, Decimal("62.0")), (5, Decimal("56.0")), (6, Decimal("0.0"))),
    5: ((5, Decimal("58.0")), (6, Decimal("0.0"))),
}


def clean_reading(value: Decimal, field: str, low: Decimal, high: Decimal) -> Decimal:
    """One instrument reading, checked against the range it can report."""
    return checked(value, field, low, high, TENTH)


@dataclass(frozen=True, order=True)
class ColorGrade:
    """A two digit colour code, held as the digits rather than as a number."""

    code: int

    def __post_init__(self) -> None:
        if not isinstance(self.code, int) or isinstance(self.code, bool):
            raise ValidationError("color", "must be a two digit code")
        if not 11 <= self.code <= 99:
            raise ValidationError("color", f"{self.code} is not a colour code")
        if self.color_class not in CLASS_NAMES:
            raise ValidationError("color", f"{self.code} names no colour class")
        if self.grade not in GRADE_NAMES:
            raise ValidationError("color", f"{self.code} names no grade")
        if self.grade not in {digit for digit, _ in GRADE_BANDS[self.color_class]}:
            raise ValidationError("color", f"{self.code} is not a grade that exists")

    @classmethod
    def parse(cls, text: str) -> Self:
        cleaned = text.strip()
        if not cleaned.isdigit():
            raise ValidationError("color", f"{text!r} is not a colour code")
        return cls(int(cleaned))

    @classmethod
    def from_reading(cls, rd: Decimal, plus_b: Decimal) -> Self:
        """Read the code the classing office would write off the chart."""
        reflectance = clean_reading(rd, "rd", MIN_RD, MAX_RD)
        yellowness = clean_reading(plus_b, "plus_b", MIN_PLUS_B, MAX_PLUS_B)
        color_class = 5
        for digit, max_yellow, min_rd in CLASS_LIMITS:
            if yellowness <= max_yellow and reflectance >= min_rd:
                color_class = digit
                break
        for grade, floor in GRADE_BANDS[color_class]:
            if reflectance >= floor:
                return cls(grade * 10 + color_class)
        raise ValidationError("color", "the chart has no band for this reading")

    @property
    def grade(self) -> int:
        return self.code // 10

    @property
    def color_class(self) -> int:
        return self.code % 10

    @property
    def is_white(self) -> bool:
        return self.color_class == 1

    @property
    def name(self) -> str:
        return f"{GRADE_NAMES[self.grade]} {CLASS_NAMES[self.color_class]}"

    def is_better_than(self, other: ColorGrade) -> bool:
        """Lower digits are better, and the class outranks the grade."""
        return (self.color_class, self.grade) < (other.color_class, other.grade)

    def __str__(self) -> str:
        return str(self.code)
