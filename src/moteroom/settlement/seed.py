"""Seed.

Cottonseed is the other half of what a gin makes and in a poor lint year it is
the half that pays. It is sold by the ton, and the gin keeps a share of it
under the ginning agreement, so the producer's seed credit is what is left
after the gin's share and the hauling come off.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.core.weight import Weight

POUNDS_PER_TON = 2_000
CENT = Decimal("0.01")


@dataclass(frozen=True)
class SeedTerms:
    """What the ginning agreement says about the seed."""

    price_per_ton: Money
    gin_shares: int
    producer_shares: int
    hauling_per_ton: Money = Money.zero()

    def __post_init__(self) -> None:
        if self.price_per_ton.amount < 0:
            raise ValidationError("price_per_ton", "must not be negative")
        if self.hauling_per_ton.amount < 0:
            raise ValidationError("hauling_per_ton", "must not be negative")
        if self.gin_shares < 0 or self.producer_shares < 0:
            raise ValidationError("shares", "must not be negative")
        if self.gin_shares + self.producer_shares == 0:
            raise ValidationError("shares", "must not both be zero")


@dataclass(frozen=True)
class SeedCredit:
    """What the seed off one producer's cotton came to."""

    seed: Weight
    gross: Money
    gin_share: Money
    hauling: Money

    @property
    def producer_share(self) -> Money:
        return self.gross - self.gin_share

    @property
    def net(self) -> Money:
        """What actually reaches the settlement, after hauling."""
        return self.producer_share - self.hauling

    def lines(self) -> list[tuple[str, Money]]:
        return [
            ("seed value", self.gross),
            ("gin share", -self.gin_share),
            ("hauling", -self.hauling),
            ("seed credit", self.net),
        ]

    def __str__(self) -> str:
        return f"{self.seed} of seed, credit {self.net}"


def tons(seed: Weight) -> Decimal:
    """Seed weight in tons, to three places, which is how it is invoiced."""
    return (Decimal(seed.pounds) / Decimal(POUNDS_PER_TON)).quantize(Decimal("0.001"))


def _per_ton(rate: Money, seed: Weight) -> Money:
    return Money((rate.amount * tons(seed)).quantize(CENT, rounding=ROUND_HALF_UP))


def credit(seed: Weight, terms: SeedTerms) -> SeedCredit:
    """Work out the seed credit on one producer's seed."""
    gross = _per_ton(terms.price_per_ton, seed)
    shares = [terms.gin_shares, terms.producer_shares]
    gin_share = gross.allocate(shares)[0]
    return SeedCredit(
        seed=seed,
        gross=gross,
        gin_share=gin_share,
        hauling=_per_ton(terms.hauling_per_ton, seed),
    )
