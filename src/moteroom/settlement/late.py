"""A settlement that came out owing.

Most producers are paid. Some are not: a producer who took advances against a
crop that did not come in owes the gin at the end, and that balance sits there
over the winter. It carries interest from a day named in the ginning agreement
rather than from the day the settlement was worked out, because the producer
cannot pay a bill they have not been sent.

Nothing here chases anybody. It says what is owed on a day, which is the number
that goes on the reminder.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money, total_money

DAYS_IN_YEAR = 365
CENT = Decimal("0.01")
GRACE_DAYS = 30
MAX_RATE = Decimal("24.00")


@dataclass(frozen=True)
class Account:
    """One producer who owes the gin at the end of a season."""

    producer: str
    owed: Money
    billed_on: date
    rate: Decimal
    grace_days: int = GRACE_DAYS
    paid_on: date | None = None

    def __post_init__(self) -> None:
        if not self.producer.strip():
            raise ValidationError("producer", "is blank")
        if self.owed.amount <= 0:
            raise ValidationError("owed", "an account only exists if something is owed")
        if self.rate < 0 or self.rate > MAX_RATE:
            raise ValidationError("rate", f"must lie between 0 and {MAX_RATE}")
        if self.grace_days < 0:
            raise ValidationError("grace_days", "must not be negative")
        if self.paid_on is not None and self.paid_on < self.billed_on:
            raise ValidationError("paid_on", "is before the bill went out")

    @property
    def due_on(self) -> date:
        """The day interest starts, which is after the grace period."""
        return self.billed_on + timedelta(days=self.grace_days)

    @property
    def is_paid(self) -> bool:
        return self.paid_on is not None

    def days_late(self, as_of: date) -> int:
        """Days past the grace period, which stops when it is paid."""
        end = self.paid_on if self.paid_on is not None else as_of
        if end <= self.due_on:
            return 0
        return (end - self.due_on).days

    def interest(self, as_of: date) -> Money:
        """Simple interest on what is owed, from the day it fell due."""
        late = self.days_late(as_of)
        if late == 0:
            return Money.zero()
        earned = (
            self.owed.amount * self.rate / Decimal(100) * Decimal(late) / Decimal(DAYS_IN_YEAR)
        )
        return Money(earned.quantize(CENT, rounding=ROUND_HALF_UP))

    def due(self, as_of: date) -> Money:
        """What would clear the account on a day."""
        if self.is_paid:
            return Money.zero()
        return self.owed + self.interest(as_of)

    def is_late(self, as_of: date) -> bool:
        return not self.is_paid and self.days_late(as_of) > 0

    def settle(self, on: date) -> Account:
        """Mark it paid, which makes a new record rather than editing."""
        if self.is_paid:
            raise ValidationError("paid_on", "is already paid")
        return Account(
            producer=self.producer,
            owed=self.owed,
            billed_on=self.billed_on,
            rate=self.rate,
            grace_days=self.grace_days,
            paid_on=on,
        )

    def __str__(self) -> str:
        if self.is_paid:
            return f"{self.producer} paid {self.owed}"
        return f"{self.producer} owes {self.owed} from {self.billed_on.isoformat()}"


def outstanding(accounts: Iterable[Account]) -> list[Account]:
    """Accounts that are still open, oldest bill first."""
    return sorted(
        (one for one in accounts if not one.is_paid),
        key=lambda one: (one.billed_on, one.producer),
    )


def owed_on(accounts: Sequence[Account], as_of: date) -> Money:
    """What the gin is owed on a day, interest and all."""
    return total_money([one.due(as_of) for one in accounts])


def late_on(accounts: Sequence[Account], as_of: date) -> list[Account]:
    """Accounts past their grace period, worst first."""
    return sorted(
        (one for one in accounts if one.is_late(as_of)),
        key=lambda one: (-one.days_late(as_of), one.producer),
    )
