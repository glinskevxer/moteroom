"""Sampling a bale for classing.

Two samples are cut from every bale, one from each side, and both go to the
office. They are cut from the same bale so they should read the same, and the
gap between them is the check on the sampling rather than on the cotton: a bale
whose two sides disagree was sampled badly, or it is not uniform, and either
way the card off it is worth less than it looks.

The office classes one sample and holds the other. If a producer asks for a
re-class the held sample is what gets read, which is why it is tracked.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId

SIDE_A = "a"
SIDE_B = "b"
SIDES = (SIDE_A, SIDE_B)

MIN_GRAMS = 60
MAX_GRAMS = 200
UNIFORM_MIKE = Decimal("0.3")
UNIFORM_STAPLE = 1


@dataclass(frozen=True)
class Sample:
    """One cut off one side of a bale."""

    bale_id: BaleId
    side: str
    cut_on: date
    grams: int
    cut_by: str

    def __post_init__(self) -> None:
        if self.side not in SIDES:
            raise ValidationError("side", f"{self.side!r} is not a side of a bale")
        if not self.cut_by.strip():
            raise ValidationError("cut_by", "is blank")
        if not isinstance(self.grams, int) or isinstance(self.grams, bool):
            raise ValidationError("grams", "must be whole grams")
        if not MIN_GRAMS <= self.grams <= MAX_GRAMS:
            raise ValidationError("grams", f"must lie between {MIN_GRAMS} and {MAX_GRAMS}")

    def __str__(self) -> str:
        return f"{self.bale_id} side {self.side} {self.grams}g"


@dataclass(frozen=True)
class Pair:
    """Both cuts off one bale, and what they say about each other."""

    first: Sample
    second: Sample

    def __post_init__(self) -> None:
        if self.first.bale_id != self.second.bale_id:
            raise ValidationError("second", "is a sample off another bale")
        if self.first.side == self.second.side:
            raise ValidationError("second", "is off the same side as the first")
        if self.first.cut_on != self.second.cut_on:
            raise ValidationError("second", "was cut on a different day")

    @property
    def bale_id(self) -> BaleId:
        return self.first.bale_id

    @property
    def grams(self) -> int:
        return self.first.grams + self.second.grams

    @property
    def is_enough(self) -> bool:
        """Whether there is enough cotton for the office to class and hold."""
        return self.first.grams >= MIN_GRAMS and self.second.grams >= MIN_GRAMS

    def uniform(self, mike_gap: Decimal, staple_gap: int) -> bool:
        """Whether the two sides read close enough to trust the card."""
        if mike_gap < 0 or staple_gap < 0:
            raise ValidationError("gap", "is measured as a distance, not a direction")
        return mike_gap <= UNIFORM_MIKE and staple_gap <= UNIFORM_STAPLE

    def __str__(self) -> str:
        return f"{self.bale_id} sampled both sides, {self.grams}g"


def cut(bale_id: BaleId, on: date, by: str, grams: int = 100) -> Pair:
    """Cut both samples off a bale at once, which is how it is actually done."""
    return Pair(
        Sample(bale_id, SIDE_A, on, grams, by),
        Sample(bale_id, SIDE_B, on, grams, by),
    )
