"""Plant time.

A gin is judged on bales an hour, and bales an hour is meaningless without the
downtime underneath it. Two plants that both made four hundred bales in a
twelve hour shift are not the same plant if one of them was choked for three
hours of it.

Shifts run past midnight, so a shift carries the date it started and the
finish time is read as the next day when it is earlier than the start.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError

MINUTES_IN_DAY = 24 * 60
HUNDREDTH = Decimal("0.01")

REASONS = ("choke", "moisture", "maintenance", "power", "trucks", "other")


@dataclass(frozen=True)
class Stoppage:
    """One thing that stopped the plant, and for how long."""

    reason: str
    minutes: int

    def __post_init__(self) -> None:
        if self.reason not in REASONS:
            raise ValidationError(
                "reason", f"{self.reason!r} is not a stoppage this plant logs"
            )
        if not isinstance(self.minutes, int) or isinstance(self.minutes, bool):
            raise ValidationError("minutes", "must be whole minutes")
        if self.minutes <= 0:
            raise ValidationError("minutes", "a stoppage has to last")

    def __str__(self) -> str:
        return f"{self.reason} {self.minutes} min"


@dataclass(frozen=True)
class Shift:
    """One run of the plant, with what stopped it."""

    started_on: date
    started: time
    finished: time
    bales: int
    stoppages: tuple[Stoppage, ...] = field(default=())

    def __post_init__(self) -> None:
        if not isinstance(self.bales, int) or isinstance(self.bales, bool):
            raise ValidationError("bales", "must be a whole count")
        if self.bales < 0:
            raise ValidationError("bales", "must not be negative")
        if self.started == self.finished:
            raise ValidationError("finished", "a shift has to last")
        if self.stopped > self.elapsed:
            raise ValidationError("stoppages", "the plant stopped longer than it ran")

    @property
    def elapsed(self) -> int:
        """Minutes from start to finish, reading a wrap as the next day."""
        start = self.started.hour * 60 + self.started.minute
        end = self.finished.hour * 60 + self.finished.minute
        return end - start if end > start else end - start + MINUTES_IN_DAY

    @property
    def stopped(self) -> int:
        return sum(stoppage.minutes for stoppage in self.stoppages)

    @property
    def running(self) -> int:
        return self.elapsed - self.stopped

    @property
    def availability(self) -> Decimal:
        """Running time as a percentage of the shift."""
        return (Decimal(self.running) * Decimal(100) / Decimal(self.elapsed)).quantize(
            HUNDREDTH, rounding=ROUND_HALF_UP
        )

    @property
    def bales_per_hour(self) -> Decimal:
        """Bales an hour on running time, which is the honest number."""
        if self.running <= 0:
            return Decimal("0.00")
        rate = Decimal(self.bales) * Decimal(60) / Decimal(self.running)
        return rate.quantize(HUNDREDTH, rounding=ROUND_HALF_UP)

    @property
    def bales_per_shift_hour(self) -> Decimal:
        """Bales an hour on elapsed time, which is what the owner asks about."""
        rate = Decimal(self.bales) * Decimal(60) / Decimal(self.elapsed)
        return rate.quantize(HUNDREDTH, rounding=ROUND_HALF_UP)

    def worst_stoppage(self) -> Stoppage | None:
        if not self.stoppages:
            return None
        return max(self.stoppages, key=lambda one: (one.minutes, one.reason))

    def __str__(self) -> str:
        return (
            f"{self.started_on.isoformat()} {self.bales} bales at {self.bales_per_hour} an hour"
        )


class ShiftLog:
    """Every shift run this season."""

    def __init__(self) -> None:
        self._shifts: list[Shift] = []

    def add(self, shift: Shift) -> None:
        """Log a shift."""
        self._shifts.append(shift)

    def extend(self, shifts: Iterable[Shift]) -> None:
        for shift in shifts:
            self.add(shift)

    def shifts(self) -> list[Shift]:
        """Every shift, oldest first."""
        return sorted(self._shifts, key=lambda shift: (shift.started_on, shift.started))

    def bales(self) -> int:
        """Bales made across every shift."""
        return sum(shift.bales for shift in self._shifts)

    def running(self) -> int:
        """Minutes the plant was actually turning."""
        return sum(shift.running for shift in self._shifts)

    def elapsed(self) -> int:
        """Minutes the plant was manned."""
        return sum(shift.elapsed for shift in self._shifts)

    def availability(self) -> Decimal:
        """Running time over manned time across the season."""
        if not self._shifts:
            return Decimal("0.00")
        return (Decimal(self.running()) * Decimal(100) / Decimal(self.elapsed())).quantize(
            HUNDREDTH, rounding=ROUND_HALF_UP
        )

    def rate(self) -> Decimal:
        """Bales an hour across the season, weighted by time rather than averaged."""
        if self.running() <= 0:
            return Decimal("0.00")
        return (Decimal(self.bales()) * Decimal(60) / Decimal(self.running())).quantize(
            HUNDREDTH, rounding=ROUND_HALF_UP
        )

    def by_reason(self) -> dict[str, int]:
        """Minutes lost per reason, worst first."""
        counted: dict[str, int] = {}
        for shift in self._shifts:
            for stoppage in shift.stoppages:
                counted[stoppage.reason] = counted.get(stoppage.reason, 0) + stoppage.minutes
        return dict(sorted(counted.items(), key=lambda pair: (-pair[1], pair[0])))

    def worst_reason(self) -> str | None:
        """What cost the plant the most time this season."""
        reasons = self.by_reason()
        return next(iter(reasons), None)

    def for_day(self, day: date) -> Sequence[Shift]:
        return [shift for shift in self._shifts if shift.started_on == day]

    def __len__(self) -> int:
        return len(self._shifts)
