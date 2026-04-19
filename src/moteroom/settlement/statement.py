"""The producer statement.

One page per producer per season. Lint proceeds at the top, everything the gin
is owed underneath, the seed and byproduct credits, the freight on their
modules, then whatever was advanced during the season, and a net at the bottom
that is either a cheque or a bill. The lines
are kept in the order they print because a statement that adds up but reads in
a different order every time is a statement nobody trusts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money, total_money
from moteroom.core.season import Season
from moteroom.core.weight import Weight


@dataclass(frozen=True)
class Advance:
    """Money paid out before the settlement, which comes back off it."""

    reference: str
    amount: Money

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise ValidationError("reference", "is blank")
        if self.amount.amount <= 0:
            raise ValidationError("amount", "an advance has to be money")


@dataclass(frozen=True)
class Statement:
    """What one producer is owed, or owes."""

    producer: str
    season: Season
    bales: int
    lint: Weight
    lint_proceeds: Money
    gin_charges: Money
    seed_credit: Money
    freight: Money = field(default_factory=Money.zero)
    byproduct_credit: Money = field(default_factory=Money.zero)
    advances: tuple[Advance, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.producer.strip():
            raise ValidationError("producer", "is blank")
        if self.bales < 0:
            raise ValidationError("bales", "must not be negative")
        if self.gin_charges.amount < 0:
            raise ValidationError("gin_charges", "is stated as a positive charge")
        if self.freight.amount < 0:
            raise ValidationError("freight", "is stated as a positive charge")
        references = [advance.reference for advance in self.advances]
        if len(set(references)) != len(references):
            raise ValidationError("advances", "names the same advance twice")

    @property
    def advanced(self) -> Money:
        return total_money([advance.amount for advance in self.advances])

    @property
    def net(self) -> Money:
        """Positive is a cheque to the producer, negative is an invoice."""
        credits = self.lint_proceeds + self.seed_credit + self.byproduct_credit
        return credits - self.gin_charges - self.freight - self.advanced

    @property
    def is_payable(self) -> bool:
        return self.net.amount > 0

    def lines(self) -> list[tuple[str, Money]]:
        rows = [
            ("lint proceeds", self.lint_proceeds),
            ("gin charges", -self.gin_charges),
            ("seed credit", self.seed_credit),
            ("byproducts", self.byproduct_credit),
            ("freight", -self.freight),
        ]
        rows.extend(
            (f"advance {advance.reference}", -advance.amount) for advance in self.advances
        )
        rows.append(("net", self.net))
        return rows

    def __str__(self) -> str:
        verdict = "due" if self.is_payable else "owing"
        return (
            f"{self.producer} {self.season} {self.bales} bales {abs(self.net.amount)} {verdict}"
        )
