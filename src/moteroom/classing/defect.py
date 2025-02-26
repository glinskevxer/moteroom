"""Leaf grade and the extraneous matter codes.

Leaf is a separate grade from colour and it is called by a classer against
physical standards rather than by an instrument. Extraneous matter is not a
grade at all: it is a list of things found in the bale that a mill will
object to, and each one carries a level, so bark shows up as light bark or
heavy bark and never as a number.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Self

from moteroom.core.errors import ValidationError

MIN_LEAF = 1
MAX_LEAF = 7
BELOW_GRADE_LEAF = 8

LEAF_NAMES = {
    1: "leaf 1",
    2: "leaf 2",
    3: "leaf 3",
    4: "leaf 4",
    5: "leaf 5",
    6: "leaf 6",
    7: "leaf 7",
    BELOW_GRADE_LEAF: "below grade",
}


class Matter(Enum):
    """What the classer found that should not be in a bale of cotton."""

    BARK = "bark"
    GRASS = "grass"
    SEED_COAT = "seed coat fragments"
    OIL = "oil"
    PLASTIC = "plastic"
    SPINDLE_TWIST = "spindle twist"

    @property
    def is_gin_fault(self) -> bool:
        """Whether the plant caused it, which decides who wears the discount."""
        return self in {Matter.OIL, Matter.PLASTIC, Matter.SPINDLE_TWIST}


class Level(Enum):
    """How much of it there is, which is all the classer records."""

    LIGHT = 1
    HEAVY = 2


@dataclass(frozen=True, order=True)
class LeafGrade:
    """A leaf grade of one through seven, or eight for below grade."""

    grade: int

    def __post_init__(self) -> None:
        if not isinstance(self.grade, int) or isinstance(self.grade, bool):
            raise ValidationError("leaf", "must be a whole grade")
        if self.grade not in LEAF_NAMES:
            raise ValidationError("leaf", f"{self.grade} is not a leaf grade")

    @classmethod
    def parse(cls, text: str) -> Self:
        cleaned = text.strip()
        if not cleaned.isdigit():
            raise ValidationError("leaf", f"{text!r} is not a leaf grade")
        return cls(int(cleaned))

    @property
    def is_below_grade(self) -> bool:
        return self.grade == BELOW_GRADE_LEAF

    @property
    def name(self) -> str:
        return LEAF_NAMES[self.grade]

    def is_better_than(self, other: LeafGrade) -> bool:
        return self.grade < other.grade

    def __str__(self) -> str:
        return str(self.grade)


@dataclass(frozen=True, order=True)
class Extraneous:
    """One finding: what it was and how much of it."""

    matter: Matter
    level: Level

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read a code such as ``B2`` or ``G1`` off the classing card."""
        cleaned = text.strip().upper()
        if len(cleaned) != 2 or not cleaned[1].isdigit():
            raise ValidationError("extraneous", f"{text!r} is not an extraneous code")
        letters = {
            "B": Matter.BARK,
            "G": Matter.GRASS,
            "S": Matter.SEED_COAT,
            "O": Matter.OIL,
            "P": Matter.PLASTIC,
            "T": Matter.SPINDLE_TWIST,
        }
        if cleaned[0] not in letters:
            raise ValidationError("extraneous", f"{text!r} names nothing the classer calls")
        try:
            level = Level(int(cleaned[1]))
        except ValueError as exc:
            raise ValidationError("extraneous", f"{text!r} carries no level") from exc
        return cls(letters[cleaned[0]], level)

    @property
    def code(self) -> str:
        first = {
            Matter.BARK: "B",
            Matter.GRASS: "G",
            Matter.SEED_COAT: "S",
            Matter.OIL: "O",
            Matter.PLASTIC: "P",
            Matter.SPINDLE_TWIST: "T",
        }[self.matter]
        return f"{first}{self.level.value}"

    @property
    def is_heavy(self) -> bool:
        return self.level is Level.HEAVY

    def __str__(self) -> str:
        weight = "heavy" if self.is_heavy else "light"
        return f"{weight} {self.matter.value}"
