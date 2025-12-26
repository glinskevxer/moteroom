"""Motes, gin trash and what they are worth.

The mote room pulls short fibre out of the lint and it is baled and sold, at a
fraction of what lint makes but for real money. Gin trash is the rest: burrs,
sticks and dirt. Sometimes a feedlot pays for it and sometimes the plant pays
to have it hauled away, so the price on a load of trash can be negative and
nothing here assumes otherwise.

Whatever it makes is allocated back to the producers on ginned volume, because
the trash came off their cotton.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money, total_money
from moteroom.core.weight import Weight, total

POUNDS_PER_TON = 2_000
CENT = Decimal("0.01")

MOTES = "motes"
TRASH = "trash"
HULLS = "hulls"
KINDS = (MOTES, TRASH, HULLS)


@dataclass(frozen=True)
class Sale:
    """One load of something that is not lint or seed."""

    kind: str
    sold_on: date
    weight: Weight
    price_per_ton: Money
    buyer: str

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValidationError("kind", f"{self.kind!r} is not something this plant sells")
        if not self.buyer.strip():
            raise ValidationError("buyer", "is blank")
        if self.weight.is_zero:
            raise ValidationError("weight", "a load has to weigh something")

    @property
    def tons(self) -> Decimal:
        return (Decimal(self.weight.pounds) / Decimal(POUNDS_PER_TON)).quantize(
            Decimal("0.001")
        )

    @property
    def proceeds(self) -> Money:
        """What the load made, which is negative when it cost to shift it."""
        amount = self.price_per_ton.amount * self.tons
        return Money(amount.quantize(CENT, rounding=ROUND_HALF_UP))

    @property
    def is_disposal(self) -> bool:
        return self.price_per_ton.amount < 0

    def __str__(self) -> str:
        verb = "cost" if self.is_disposal else "made"
        return f"{self.tons} tons of {self.kind} {verb} {abs(self.proceeds.amount)}"


class ByproductLedger:
    """Every load sold this season."""

    def __init__(self) -> None:
        self._sales: list[Sale] = []

    def sell(self, sale: Sale) -> None:
        """Record a load leaving the plant."""
        self._sales.append(sale)

    def extend(self, sales: Iterable[Sale]) -> None:
        for sale in sales:
            self.sell(sale)

    def sales(self, kind: str | None = None) -> list[Sale]:
        """Every load, oldest first, or only one kind of them."""
        rows = [one for one in self._sales if kind is None or one.kind == kind]
        return sorted(rows, key=lambda one: (one.sold_on, one.kind, one.buyer))

    def weight(self, kind: str | None = None) -> Weight:
        return total([one.weight for one in self.sales(kind)])

    def proceeds(self, kind: str | None = None) -> Money:
        return total_money([one.proceeds for one in self.sales(kind)])

    def by_kind(self) -> dict[str, Money]:
        """What each kind came to, in the order the plant lists them."""
        return {kind: self.proceeds(kind) for kind in KINDS if self.sales(kind)}

    def disposals(self) -> list[Sale]:
        """Loads that cost money rather than making it."""
        return [one for one in self.sales() if one.is_disposal]

    def allocate(self, volume: dict[str, Weight]) -> dict[str, Money]:
        """Share what the byproducts came to across the producers who grew it."""
        if not volume:
            raise ValidationError("volume", "nobody ginned anything")
        ginned = total(list(volume.values()))
        if ginned.is_zero:
            raise ValidationError("volume", "nobody ginned anything")
        names = sorted(volume)
        parts = self.proceeds().allocate([volume[name].pounds for name in names])
        return dict(zip(names, parts, strict=True))

    def __len__(self) -> int:
        return len(self._sales)
