"""Insuring the cotton in store.

A warehouse insures what it holds, and the gin insures its own bales until the
receipt is issued. Both work the same way: a declared value per bale up to a
limit, so the interesting number is not the premium but the gap between what
the cotton is worth today and what the policy would actually pay.

Cotton is worth more in February than it was in October, so the gap opens by
itself without anybody doing anything. That is the whole reason to compute it
rather than to file the policy and forget it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from moteroom.core.errors import ValidationError
from moteroom.core.money import CentsPerPound, Money, total_money
from moteroom.core.weight import Weight, total
from moteroom.warehouse.receipt import Receipt


@dataclass(frozen=True)
class Policy:
    """One policy over bales in store."""

    insurer: str
    number: str
    per_bale: Money
    limit: Money
    starts_on: date
    ends_on: date
    deductible: Money = Money.zero()

    def __post_init__(self) -> None:
        if not self.insurer.strip():
            raise ValidationError("insurer", "is blank")
        if not self.number.strip():
            raise ValidationError("policy", "is blank")
        if self.per_bale.amount <= 0:
            raise ValidationError("per_bale", "must be money")
        if self.limit.amount <= 0:
            raise ValidationError("limit", "must be money")
        if self.deductible.amount < 0:
            raise ValidationError("deductible", "must not be negative")
        if self.ends_on <= self.starts_on:
            raise ValidationError("ends_on", "is not after the policy starts")

    def covers(self, day: date) -> bool:
        return self.starts_on <= day <= self.ends_on

    def bales_covered(self) -> int:
        """How many bales the limit reaches at the declared value."""
        return int(self.limit.amount // self.per_bale.amount)

    def __str__(self) -> str:
        return f"{self.insurer} {self.number} at {self.per_bale} a bale to {self.limit}"


@dataclass(frozen=True)
class Exposure:
    """What is in store, what it is worth, and what the policy would pay."""

    policy: Policy
    as_of: date
    bales: int
    lint: Weight
    market_value: Money

    @property
    def in_force(self) -> bool:
        return self.policy.covers(self.as_of)

    @property
    def declared(self) -> Money:
        """What the policy says the bales are worth."""
        return self.policy.per_bale.times(self.bales)

    @property
    def payable(self) -> Money:
        """What it would actually pay, which is the lower of the two."""
        if not self.in_force:
            return Money.zero()
        capped = min(self.declared, self.policy.limit)
        after = capped - self.policy.deductible
        return after if after.amount > 0 else Money.zero()

    @property
    def shortfall(self) -> Money:
        """The gap between what the cotton is worth and what would be paid."""
        gap = self.market_value - self.payable
        return gap if gap.amount > 0 else Money.zero()

    @property
    def is_covered(self) -> bool:
        return self.shortfall.is_zero

    @property
    def over_limit(self) -> bool:
        return self.declared > self.policy.limit

    def lines(self) -> list[tuple[str, str]]:
        return [
            ("policy", str(self.policy)),
            ("in force", "yes" if self.in_force else "no"),
            ("bales", str(self.bales)),
            ("lint", str(self.lint)),
            ("market value", str(self.market_value)),
            ("declared", str(self.declared)),
            ("would pay", str(self.payable)),
            ("shortfall", str(self.shortfall)),
        ]

    def __str__(self) -> str:
        if not self.in_force:
            return f"{self.bales} bales with no cover on {self.as_of.isoformat()}"
        if self.is_covered:
            return f"{self.bales} bales covered"
        return f"{self.bales} bales short by {self.shortfall}"


def exposure(
    receipts: Sequence[Receipt],
    policy: Policy,
    price: CentsPerPound,
    as_of: date,
) -> Exposure:
    """Work out the gap on the bales still in store."""
    held = [receipt for receipt in receipts if receipt.is_outstanding]
    lint = total([receipt.net for receipt in held])
    return Exposure(
        policy=policy,
        as_of=as_of,
        bales=len(held),
        lint=lint,
        market_value=price.on(lint),
    )


def premium(policy: Policy, rate_per_hundred: Money, bales: int) -> Money:
    """What the cover costs, quoted per hundred dollars of declared value."""
    if bales < 0:
        raise ValidationError("bales", "must not be negative")
    if rate_per_hundred.amount < 0:
        raise ValidationError("rate", "must not be negative")
    declared = policy.per_bale.times(bales)
    hundreds = declared.amount / 100
    return total_money([Money(round(rate_per_hundred.amount * hundreds, 2))])
