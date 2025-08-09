"""The premium and discount schedule.

The schedule prices quality against a base grade. Every table here is read the
same way: find the band the reading falls in and take the adjustment in cents
per pound, positive for a premium and negative for a discount. Add them all to
the base rate and that is what the bale loans for.

Colour and leaf are stored as a base per colour code plus a ladder on leaf,
rather than as a two hundred cell grid, because that is how the office reads it
out loud and it is far easier to check.

The numbers are this gin's own schedule for the season and they are expected to
be replaced each year. What must not change is that they are exact decimals and
that every band is closed at both ends.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from moteroom.core.errors import ValidationError

BASE_COLOR = 41
BASE_LEAF = 3
BASE_STAPLE = 36


@dataclass(frozen=True)
class Band:
    """One row of a table: a closed range and what it does to the rate."""

    low: Decimal
    high: Decimal
    points: Decimal

    def __post_init__(self) -> None:
        if self.low > self.high:
            raise ValidationError("band", f"{self.low} to {self.high} runs backwards")
        if self.points != self.points.quantize(Decimal("0.01")):
            raise ValidationError("band", "is finer than a hundredth of a cent")

    def holds(self, value: Decimal) -> bool:
        return self.low <= value <= self.high


class BandTable:
    """A column of the schedule, checked for gaps when it is built."""

    def __init__(self, name: str, rows: list[tuple[str, str, str]]) -> None:
        if not rows:
            raise ValidationError("table", f"{name} has no bands")
        bands = [
            Band(Decimal(low), Decimal(high), Decimal(points)) for low, high, points in rows
        ]
        for earlier, later in zip(bands, bands[1:], strict=False):
            if later.low <= earlier.high:
                raise ValidationError("table", f"{name} overlaps at {later.low}")
        self.name = name
        self.bands = tuple(bands)

    @property
    def low(self) -> Decimal:
        return self.bands[0].low

    @property
    def high(self) -> Decimal:
        return self.bands[-1].high

    def covers(self, value: Decimal) -> bool:
        return any(band.holds(value) for band in self.bands)

    def lookup(self, value: Decimal) -> Decimal:
        """The adjustment for a reading, refusing one the table does not cover."""
        for band in self.bands:
            if band.holds(value):
                return band.points
        raise ValidationError(self.name, f"{value} falls in no band")

    def __len__(self) -> int:
        return len(self.bands)


MICRONAIRE = BandTable(
    "micronaire",
    [
        ("2.0", "2.6", "-5.00"),
        ("2.7", "2.9", "-3.65"),
        ("3.0", "3.2", "-2.00"),
        ("3.3", "3.4", "-1.20"),
        ("3.5", "3.6", "-0.35"),
        ("3.7", "4.2", "0.00"),
        ("4.3", "4.9", "-0.15"),
        ("5.0", "5.2", "-0.85"),
        ("5.3", "6.9", "-1.60"),
    ],
)

STAPLE = BandTable(
    "staple",
    [
        ("24", "31", "-7.50"),
        ("32", "33", "-3.30"),
        ("34", "34", "-1.10"),
        ("35", "35", "-0.40"),
        ("36", "36", "0.00"),
        ("37", "37", "0.55"),
        ("38", "38", "1.05"),
        ("39", "40", "1.45"),
        ("41", "45", "1.70"),
    ],
)

STRENGTH = BandTable(
    "strength",
    [
        ("15.0", "21.9", "-1.15"),
        ("22.0", "23.9", "-0.60"),
        ("24.0", "25.9", "-0.25"),
        ("26.0", "28.9", "0.00"),
        ("29.0", "30.9", "0.35"),
        ("31.0", "40.0", "0.60"),
    ],
)

UNIFORMITY = BandTable(
    "uniformity",
    [
        ("70.0", "77.9", "-0.85"),
        ("78.0", "79.9", "-0.35"),
        ("80.0", "82.9", "0.00"),
        ("83.0", "84.9", "0.30"),
        ("85.0", "90.0", "0.45"),
    ],
)

# Colour base by code, against strict low middling white as the base grade.
COLOR_POINTS: dict[int, Decimal] = {
    11: Decimal("1.75"),
    21: Decimal("1.30"),
    31: Decimal("0.60"),
    41: Decimal("0.00"),
    51: Decimal("-1.85"),
    61: Decimal("-3.55"),
    71: Decimal("-5.20"),
    22: Decimal("0.10"),
    32: Decimal("-0.35"),
    42: Decimal("-1.15"),
    52: Decimal("-2.95"),
    33: Decimal("-1.60"),
    43: Decimal("-2.70"),
    53: Decimal("-4.15"),
    63: Decimal("-5.90"),
    44: Decimal("-4.35"),
    54: Decimal("-6.05"),
    64: Decimal("-7.80"),
    55: Decimal("-7.40"),
    65: Decimal("-9.10"),
}

# The leaf ladder, against leaf 3 as the base.
LEAF_POINTS: dict[int, Decimal] = {
    1: Decimal("0.35"),
    2: Decimal("0.20"),
    3: Decimal("0.00"),
    4: Decimal("-0.55"),
    5: Decimal("-1.40"),
    6: Decimal("-2.65"),
    7: Decimal("-4.10"),
}

# What the mill takes off for extraneous matter, by code.
EXTRANEOUS_POINTS: dict[str, Decimal] = {
    "B1": Decimal("-0.75"),
    "B2": Decimal("-2.25"),
    "G1": Decimal("-0.60"),
    "G2": Decimal("-1.80"),
    "S1": Decimal("-0.40"),
    "S2": Decimal("-1.20"),
    "O1": Decimal("-1.00"),
    "O2": Decimal("-3.00"),
    "P1": Decimal("-1.50"),
    "P2": Decimal("-4.50"),
    "T1": Decimal("-0.90"),
    "T2": Decimal("-2.70"),
}


def color_points(code: int) -> Decimal:
    """The colour adjustment for a code the schedule prices."""
    try:
        return COLOR_POINTS[code]
    except KeyError as exc:
        raise ValidationError("color", f"{code} is not priced in this schedule") from exc


def leaf_points(grade: int) -> Decimal:
    """The leaf adjustment, which does not price below grade at all."""
    try:
        return LEAF_POINTS[grade]
    except KeyError as exc:
        raise ValidationError("leaf", f"{grade} is not priced in this schedule") from exc


def extraneous_points(code: str) -> Decimal:
    """What the schedule takes off for one extraneous finding."""
    try:
        return EXTRANEOUS_POINTS[code]
    except KeyError as exc:
        raise ValidationError("extraneous", f"{code} is not priced in this schedule") from exc
