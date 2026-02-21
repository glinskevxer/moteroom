"""Keeping the instrument honest.

A classing line is checked against standard cotton before it classes anything,
and the standards have assigned values that everybody in the trade works to. A
reading outside tolerance means the line is out and every card it produced
since the last good check is suspect.

Drift is the other half. A line that is inside tolerance every day but has
crept the same direction for a week is going out, and the point of keeping the
checks is to see that before it does.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.reading import TENTH, checked

MEASURES = ("micronaire", "strength", "uniformity", "length")

TOLERANCES: dict[str, Decimal] = {
    "micronaire": Decimal("0.1"),
    "strength": Decimal("0.6"),
    "uniformity": Decimal("0.8"),
    "length": Decimal("0.2"),
}

RANGES: dict[str, tuple[Decimal, Decimal]] = {
    "micronaire": (Decimal("2.0"), Decimal("6.9")),
    "strength": (Decimal("15.0"), Decimal("40.0")),
    "uniformity": (Decimal("70.0"), Decimal("90.0")),
    "length": (Decimal("0.7"), Decimal("1.5")),
}

DRIFT_RUN = 4


@dataclass(frozen=True)
class Standard:
    """One box of standard cotton and the values assigned to it."""

    name: str
    values: dict[str, Decimal]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("standard", "is blank")
        missing = [measure for measure in MEASURES if measure not in self.values]
        if missing:
            raise ValidationError("values", f"has no {', '.join(missing)}")
        for measure, value in self.values.items():
            if measure not in MEASURES:
                raise ValidationError("values", f"{measure} is not a measure this checks")
            low, high = RANGES[measure]
            checked(value, measure, low, high, TENTH)

    def __str__(self) -> str:
        return f"standard {self.name}"


@dataclass(frozen=True)
class Check:
    """One run of the standard through the line."""

    standard: Standard
    checked_on: date
    readings: dict[str, Decimal]
    operator: str

    def __post_init__(self) -> None:
        if not self.operator.strip():
            raise ValidationError("operator", "is blank")
        missing = [measure for measure in MEASURES if measure not in self.readings]
        if missing:
            raise ValidationError("readings", f"has no {', '.join(missing)}")
        for measure, value in self.readings.items():
            if measure not in MEASURES:
                raise ValidationError("readings", f"{measure} is not a measure this checks")
            low, high = RANGES[measure]
            checked(value, measure, low, high, TENTH)

    def deviation(self, measure: str) -> Decimal:
        """How far the line read from the assigned value, signed."""
        if measure not in MEASURES:
            raise ValidationError("measure", f"{measure} is not a measure this checks")
        return self.readings[measure] - self.standard.values[measure]

    def within(self, measure: str) -> bool:
        return abs(self.deviation(measure)) <= TOLERANCES[measure]

    @property
    def failures(self) -> tuple[str, ...]:
        """Which measures were outside tolerance, if any."""
        return tuple(measure for measure in MEASURES if not self.within(measure))

    @property
    def passed(self) -> bool:
        return not self.failures

    def __str__(self) -> str:
        if self.passed:
            return f"{self.checked_on.isoformat()} {self.standard.name} passed"
        out = ", ".join(self.failures)
        return f"{self.checked_on.isoformat()} {self.standard.name} out on {out}"


class CalibrationLog:
    """Every check run on the line."""

    def __init__(self) -> None:
        self._checks: list[Check] = []

    def add(self, check: Check) -> None:
        """Log a check."""
        self._checks.append(check)

    def extend(self, checks: Iterable[Check]) -> None:
        for check in checks:
            self.add(check)

    def checks(self) -> list[Check]:
        """Every check, oldest first."""
        return sorted(self._checks, key=lambda one: (one.checked_on, one.standard.name))

    def latest(self) -> Check | None:
        held = self.checks()
        return held[-1] if held else None

    def failures(self) -> list[Check]:
        return [one for one in self.checks() if not one.passed]

    def last_good(self) -> Check | None:
        """The most recent check that passed, which is where the cards are safe to."""
        for one in reversed(self.checks()):
            if one.passed:
                return one
        return None

    def suspect_since(self) -> date | None:
        """The date after which every card is suspect, if the line is out."""
        held = self.checks()
        if not held or held[-1].passed:
            return None
        good = self.last_good()
        return good.checked_on if good else held[0].checked_on

    def drifting(self, measure: str) -> bool:
        """Whether a measure has moved the same way for a run of checks."""
        if measure not in MEASURES:
            raise ValidationError("measure", f"{measure} is not a measure this checks")
        held = self.checks()
        if len(held) < DRIFT_RUN:
            return False
        recent = [one.deviation(measure) for one in held[-DRIFT_RUN:]]
        if any(value == 0 for value in recent):
            return False
        return all(value > 0 for value in recent) or all(value < 0 for value in recent)

    def drift(self, measure: str) -> Decimal:
        """How far a measure has moved across the run, which says how fast."""
        held = self.checks()
        if len(held) < 2:
            return Decimal("0.0")
        return held[-1].deviation(measure) - held[0].deviation(measure)

    def __len__(self) -> int:
        return len(self._checks)
