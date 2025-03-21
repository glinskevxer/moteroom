"""Storage and handling charges.

The warehouse bills three separate things and they behave differently. The
receiving charge is once per bale and never prorated. Storage is by the day
after a free period, with a floor on the number of days that can be billed at
all, so a bale pulled out a week after the free period still pays the floor.
Compression is optional and only charged when the bale is actually pressed to
a shipping density.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.warehouse.receipt import Receipt


@dataclass(frozen=True)
class Tariff:
    """The warehouse's published rates for a season."""

    handling: Money
    daily: Money
    free_days: int = 0
    minimum_days: int = 0
    compression: Money = Money.zero()

    def __post_init__(self) -> None:
        for name, amount in (
            ("handling", self.handling),
            ("daily", self.daily),
            ("compression", self.compression),
        ):
            if amount.amount < 0:
                raise ValidationError(name, "must not be negative")
        if self.free_days < 0:
            raise ValidationError("free_days", "must not be negative")
        if self.minimum_days < 0:
            raise ValidationError("minimum_days", "must not be negative")


@dataclass(frozen=True)
class Charge:
    """What one bale owes the warehouse, split the way the invoice prints."""

    bale_id: str
    days_stored: int
    days_billed: int
    handling: Money
    storage: Money
    compression: Money

    @property
    def total(self) -> Money:
        return self.handling + self.storage + self.compression

    @property
    def is_free_period(self) -> bool:
        return self.days_billed == 0

    def __str__(self) -> str:
        return f"bale {self.bale_id} {self.days_billed} days {self.total}"


def days_billed(days_stored: int, tariff: Tariff) -> int:
    """Chargeable days: nothing inside the free period, a floor after it."""
    if days_stored < 0:
        raise ValidationError("days_stored", "must not be negative")
    beyond = days_stored - tariff.free_days
    if beyond <= 0:
        return 0
    return max(beyond, tariff.minimum_days)


def charge_for(
    receipt: Receipt,
    tariff: Tariff,
    as_of: date,
    compressed: bool = False,
) -> Charge:
    """Bill one receipt as at a date."""
    stored = receipt.days_stored(as_of)
    billed = days_billed(stored, tariff)
    return Charge(
        bale_id=str(receipt.bale_id),
        days_stored=stored,
        days_billed=billed,
        handling=tariff.handling,
        storage=tariff.daily.times(billed),
        compression=tariff.compression if compressed else Money.zero(),
    )
