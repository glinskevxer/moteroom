"""What it costs to run the plant.

A gin buys two things to turn cotton into bales: electricity for the motors
and gas for the driers. They move independently. A wet year burns gas without
touching the power bill, and a plant running badly burns power without ginning
any more cotton, so they are metered and priced apart and only added at the end.

Energy per bale is the number that gets compared against last year, and it is
only meaningful next to the moisture that came in, which is why the reading
carries it.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money, total_money
from moteroom.core.reading import TENTH, checked

CENT = Decimal("0.01")
THOUSANDTH = Decimal("0.001")
MIN_MOISTURE = Decimal("2.0")
MAX_MOISTURE = Decimal("25.0")


@dataclass(frozen=True)
class Reading:
    """One day's meters, against the cotton that went through."""

    day: date
    bales: int
    kilowatt_hours: int
    therms: int
    moisture: Decimal

    def __post_init__(self) -> None:
        for name, value in (
            ("bales", self.bales),
            ("kilowatt_hours", self.kilowatt_hours),
            ("therms", self.therms),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValidationError(name, "must be a whole count")
            if value < 0:
                raise ValidationError(name, "must not be negative")
        object.__setattr__(
            self,
            "moisture",
            checked(self.moisture, "moisture", MIN_MOISTURE, MAX_MOISTURE, TENTH),
        )
        if self.bales == 0 and (self.kilowatt_hours or self.therms):
            raise ValidationError("bales", "the plant burned energy and made nothing")

    def power_per_bale(self) -> Decimal:
        if self.bales == 0:
            return Decimal("0.000")
        return (Decimal(self.kilowatt_hours) / Decimal(self.bales)).quantize(THOUSANDTH)

    def gas_per_bale(self) -> Decimal:
        if self.bales == 0:
            return Decimal("0.000")
        return (Decimal(self.therms) / Decimal(self.bales)).quantize(THOUSANDTH)

    def cost(self, power_rate: Money, gas_rate: Money) -> Money:
        """What the day cost at the rates the plant is on."""
        for name, rate in (("power_rate", power_rate), ("gas_rate", gas_rate)):
            if rate.amount < 0:
                raise ValidationError(name, "must not be negative")
        spent = power_rate.amount * Decimal(self.kilowatt_hours) + gas_rate.amount * Decimal(
            self.therms
        )
        return Money(spent.quantize(CENT, rounding=ROUND_HALF_UP))

    def __str__(self) -> str:
        return f"{self.day.isoformat()} {self.bales} bales, {self.power_per_bale()} kWh a bale"


class EnergyLog:
    """Every day's meters this season."""

    def __init__(self) -> None:
        self._readings: list[Reading] = []

    def add(self, reading: Reading) -> None:
        """Log a day."""
        if any(one.day == reading.day for one in self._readings):
            raise ValidationError("day", f"{reading.day} is already logged")
        self._readings.append(reading)

    def extend(self, readings: Iterable[Reading]) -> None:
        for reading in readings:
            self.add(reading)

    def readings(self) -> list[Reading]:
        return sorted(self._readings, key=lambda one: one.day)

    def bales(self) -> int:
        return sum(one.bales for one in self._readings)

    def kilowatt_hours(self) -> int:
        return sum(one.kilowatt_hours for one in self._readings)

    def therms(self) -> int:
        return sum(one.therms for one in self._readings)

    def power_per_bale(self) -> Decimal:
        """Power across the season, weighted by bales rather than averaged."""
        if self.bales() == 0:
            return Decimal("0.000")
        return (Decimal(self.kilowatt_hours()) / Decimal(self.bales())).quantize(THOUSANDTH)

    def gas_per_bale(self) -> Decimal:
        if self.bales() == 0:
            return Decimal("0.000")
        return (Decimal(self.therms()) / Decimal(self.bales())).quantize(THOUSANDTH)

    def cost(self, power_rate: Money, gas_rate: Money) -> Money:
        return total_money([one.cost(power_rate, gas_rate) for one in self._readings])

    def cost_per_bale(self, power_rate: Money, gas_rate: Money) -> Money:
        if self.bales() == 0:
            return Money.zero()
        return self.cost(power_rate, gas_rate).allocate([1] * self.bales())[0]

    def wettest(self) -> Reading | None:
        """The day the driers worked hardest, which is where the gas went."""
        if not self._readings:
            return None
        return max(self._readings, key=lambda one: (one.moisture, one.day))

    def __len__(self) -> int:
        return len(self._readings)
