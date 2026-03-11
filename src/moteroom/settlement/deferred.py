"""Deferred payment.

A producer who has had a good year asks the gin to hold their settlement until
January so it falls in the next tax year. The gin agrees in writing before the
cotton is ginned, holds the money, and pays it on the day named. It is a real
liability sitting on the gin's books all winter, so it carries interest and it
is tracked separately from anything unpaid by accident.

The one rule that makes it a deferral rather than a late payment: the day named
has to fall in a later calendar year than the day it was agreed. An agreement
to pay in six weeks is not a deferral, it is just slow.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ConflictError, ValidationError
from moteroom.core.money import Money, total_money

DAYS_IN_YEAR = 365
CENT = Decimal("0.01")
MAX_RATE = Decimal("15.00")


@dataclass(frozen=True)
class Deferral:
    """One agreement to hold a producer's money until a named day."""

    producer: str
    amount: Money
    agreed_on: date
    pay_on: date
    rate: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        if not self.producer.strip():
            raise ValidationError("producer", "is blank")
        if self.amount.amount <= 0:
            raise ValidationError("amount", "a deferral has to hold money")
        if self.pay_on <= self.agreed_on:
            raise ValidationError("pay_on", "is not after the agreement")
        if self.pay_on.year <= self.agreed_on.year:
            raise ValidationError("pay_on", "falls in the same year, so it defers nothing")
        if self.rate < 0 or self.rate > MAX_RATE:
            raise ValidationError("rate", f"must lie between 0 and {MAX_RATE}")

    @property
    def days(self) -> int:
        return (self.pay_on - self.agreed_on).days

    def held_days(self, as_of: date) -> int:
        """How long the gin has had the money, which stops on the pay day."""
        if as_of < self.agreed_on:
            return 0
        end = min(as_of, self.pay_on)
        return (end - self.agreed_on).days

    def interest(self, as_of: date) -> Money:
        """Simple interest to a date, which stops accruing when it is paid."""
        earned = (
            self.amount.amount
            * self.rate
            / Decimal(100)
            * Decimal(self.held_days(as_of))
            / Decimal(DAYS_IN_YEAR)
        )
        return Money(earned.quantize(CENT, rounding=ROUND_HALF_UP))

    def due(self, as_of: date) -> Money:
        return self.amount + self.interest(as_of)

    def is_matured(self, as_of: date) -> bool:
        return as_of >= self.pay_on

    def __str__(self) -> str:
        return f"{self.producer} {self.amount} held to {self.pay_on.isoformat()}"


class DeferralBook:
    """Every deferral the gin has agreed to."""

    def __init__(self) -> None:
        self._deferrals: list[Deferral] = []

    def agree(self, deferral: Deferral) -> None:
        """Take on a deferral, refusing a second one for the same day."""
        for held in self._deferrals:
            if held.producer == deferral.producer and held.pay_on == deferral.pay_on:
                raise ConflictError(
                    "deferral", deferral.producer, f"already defers to {deferral.pay_on}"
                )
        self._deferrals.append(deferral)

    def extend(self, deferrals: Iterable[Deferral]) -> None:
        for deferral in deferrals:
            self.agree(deferral)

    def deferrals(self, producer: str | None = None) -> list[Deferral]:
        """Every deferral, soonest to pay first."""
        rows = [one for one in self._deferrals if producer is None or one.producer == producer]
        return sorted(rows, key=lambda one: (one.pay_on, one.producer))

    def held(self) -> Money:
        """What the gin is holding, before any interest."""
        return total_money([one.amount for one in self._deferrals])

    def owed(self, as_of: date) -> Money:
        """What it would cost to pay every deferral out today."""
        return total_money([one.due(as_of) for one in self._deferrals])

    def maturing(self, as_of: date) -> list[Deferral]:
        """Deferrals that have come due and are not paid."""
        return [one for one in self.deferrals() if one.is_matured(as_of)]

    def producers(self) -> list[str]:
        return sorted({one.producer for one in self._deferrals})

    def __len__(self) -> int:
        return len(self._deferrals)
