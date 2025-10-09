"""Forward contracts.

A contract is a promise to deliver a number of bales inside a window at a
price agreed before the cotton was picked. Two kinds. A flat price contract
names the price outright. A basis contract names only the difference from the
futures price, so it has no price at all until a futures number is put against
it, and asking one for its price without that is a mistake rather than a
default.

Contracts are written against a base grade. Bales that class better or worse
than the base are paid the contract price moved by the same premium and
discount ladder the loan uses, so a producer cannot deliver their worst bales
against a contract and keep the rest.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ValidationError
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.weight import Weight
from moteroom.loan import schedule

_NUMBER = re.compile(r"^C\d{6}$")
MAX_BALES = 50_000


@dataclass(frozen=True)
class Contract:
    """One promise to deliver bales inside a window."""

    number: str
    buyer: str
    signed_on: date
    bales: int
    delivery_from: date
    delivery_to: date
    price: CentsPerPound | None = None
    basis: CentsPerPound | None = None

    def __post_init__(self) -> None:
        if not _NUMBER.match(self.number):
            raise ValidationError("contract", f"{self.number!r} is not a contract number")
        if not self.buyer.strip():
            raise ValidationError("buyer", "is blank")
        if not isinstance(self.bales, int) or isinstance(self.bales, bool):
            raise ValidationError("bales", "must be a whole count")
        if not 1 <= self.bales <= MAX_BALES:
            raise ValidationError("bales", f"must lie between 1 and {MAX_BALES}")
        if self.delivery_to < self.delivery_from:
            raise ValidationError("delivery_to", "is before the window opens")
        if self.delivery_from < self.signed_on:
            raise ValidationError("delivery_from", "opens before the contract was signed")
        if (self.price is None) == (self.basis is None):
            raise ValidationError("price", "a contract is priced flat or on basis, not both")

    @property
    def is_basis(self) -> bool:
        """Whether the price still needs a futures number put against it."""
        return self.basis is not None

    @property
    def window_days(self) -> int:
        return (self.delivery_to - self.delivery_from).days + 1

    def covers(self, day: date) -> bool:
        return self.delivery_from <= day <= self.delivery_to

    def price_against(self, futures: CentsPerPound | None = None) -> CentsPerPound:
        """The price this contract works out at."""
        if self.price is not None:
            return self.price
        if futures is None:
            raise ValidationError("futures", "a basis contract needs a futures price")
        assert self.basis is not None
        return futures + self.basis

    def value(self, weight: Weight, futures: CentsPerPound | None = None) -> Money:
        """What a weight is worth at the contract price."""
        return self.price_against(futures).on(weight)

    def __str__(self) -> str:
        kind = f"basis {self.basis}" if self.is_basis else f"flat {self.price}"
        return f"contract {self.number} {self.bales} bales for {self.buyer} at {kind}"


def grade_adjustment(card: ClassingRecord) -> Decimal:
    """How far a card sits from the base grade, in cents per pound."""
    return (
        schedule.color_points(card.color.code)
        + schedule.leaf_points(card.leaf.grade)
        + schedule.STAPLE.lookup(Decimal(card.staple.thirty_seconds))
        + schedule.MICRONAIRE.lookup(card.micronaire.reading)
        + sum((schedule.extraneous_points(code) for code in card.codes), start=Decimal("0.00"))
    )


def delivered_price(
    contract: Contract,
    card: ClassingRecord,
    futures: CentsPerPound | None = None,
) -> CentsPerPound:
    """What one classed bale is paid against a contract."""
    moved = contract.price_against(futures).cents + grade_adjustment(card)
    return CentsPerPound(max(moved, Decimal("0.00")))


@dataclass(frozen=True)
class Fill:
    """How much of a contract has been delivered."""

    contract: str
    contracted: int
    delivered: int

    @property
    def remaining(self) -> int:
        return max(self.contracted - self.delivered, 0)

    @property
    def over(self) -> int:
        """Bales delivered past what was promised."""
        return max(self.delivered - self.contracted, 0)

    @property
    def is_complete(self) -> bool:
        return self.delivered >= self.contracted

    def __str__(self) -> str:
        if self.over:
            return f"contract {self.contract} filled with {self.over} over"
        if self.is_complete:
            return f"contract {self.contract} filled"
        return f"contract {self.contract} short {self.remaining}"


def fill_of(contract: Contract, deliveries: Sequence[int]) -> Fill:
    """Total the deliveries against what was promised."""
    if any(count < 0 for count in deliveries):
        raise ValidationError("deliveries", "must not be negative")
    return Fill(contract.number, contract.bales, sum(deliveries))
