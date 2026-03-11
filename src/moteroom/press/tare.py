"""Bagging and ties.

Every bale leaves the press wrapped, and the wrap is bought in by the pallet
before the season starts. Running out at two in the morning stops the plant, so
the store is counted against what is still to gin rather than against what is
on the floor.

Bagging and ties are counted separately because they are bought separately and
run out at different rates: a bale takes one bag and eight ties, and a short
delivery of one does not tell you anything about the other.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money

BAGS = "bags"
TIES = "ties"
KINDS = (BAGS, TIES)
PER_BALE = {BAGS: 1, TIES: 8}
CENT = Decimal("0.01")


@dataclass(frozen=True)
class Delivery:
    """One lot of wrap arriving at the plant."""

    kind: str
    arrived_on: date
    count: int
    cost_each: Money
    supplier: str

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValidationError("kind", f"{self.kind!r} is not wrap this plant buys")
        if not self.supplier.strip():
            raise ValidationError("supplier", "is blank")
        if not isinstance(self.count, int) or isinstance(self.count, bool):
            raise ValidationError("count", "must be a whole count")
        if self.count <= 0:
            raise ValidationError("count", "a delivery has to bring something")
        if self.cost_each.amount < 0:
            raise ValidationError("cost_each", "must not be negative")

    @property
    def value(self) -> Money:
        return self.cost_each.times(self.count)

    def __str__(self) -> str:
        return f"{self.count} {self.kind} from {self.supplier} at {self.cost_each}"


class TareStore:
    """What wrap is on hand, and whether it will see the season out."""

    def __init__(self) -> None:
        self._deliveries: list[Delivery] = []
        self._used: dict[str, int] = {kind: 0 for kind in KINDS}

    def receive(self, delivery: Delivery) -> None:
        """Take a delivery in."""
        self._deliveries.append(delivery)

    def extend(self, deliveries: Iterable[Delivery]) -> None:
        for delivery in deliveries:
            self.receive(delivery)

    def press(self, bales: int) -> None:
        """Use the wrap a run of bales takes."""
        if bales < 0:
            raise ValidationError("bales", "must not be negative")
        for kind in KINDS:
            wanted = bales * PER_BALE[kind]
            if wanted > self.on_hand(kind):
                raise ValidationError(
                    kind, f"only {self.on_hand(kind)} left and {wanted} wanted"
                )
        for kind in KINDS:
            self._used[kind] += bales * PER_BALE[kind]

    def delivered(self, kind: str) -> int:
        self._known(kind)
        return sum(one.count for one in self._deliveries if one.kind == kind)

    def used(self, kind: str) -> int:
        self._known(kind)
        return self._used[kind]

    def on_hand(self, kind: str) -> int:
        return self.delivered(kind) - self.used(kind)

    def bales_left(self) -> int:
        """How many more bales the store will wrap before something runs out."""
        return min(self.on_hand(kind) // PER_BALE[kind] for kind in KINDS)

    def short_for(self, bales: int) -> dict[str, int]:
        """What would have to be bought to wrap a number of bales."""
        if bales < 0:
            raise ValidationError("bales", "must not be negative")
        short = {}
        for kind in KINDS:
            wanted = bales * PER_BALE[kind] - self.on_hand(kind)
            if wanted > 0:
                short[kind] = wanted
        return short

    def value(self) -> Money:
        """What the wrap on hand cost, at the average paid for it."""
        held = Money.zero()
        for kind in KINDS:
            delivered = self.delivered(kind)
            if delivered == 0:
                continue
            spent = sum(
                (one.value.amount for one in self._deliveries if one.kind == kind),
                Decimal("0.00"),
            )
            average = spent / Decimal(delivered)
            held += Money(
                (average * Decimal(self.on_hand(kind))).quantize(CENT, rounding=ROUND_HALF_UP)
            )
        return held

    def cost_per_bale(self) -> Money:
        """What wrapping one bale costs at the average paid."""
        held = Money.zero()
        for kind in KINDS:
            delivered = self.delivered(kind)
            if delivered == 0:
                continue
            spent = sum(
                (one.value.amount for one in self._deliveries if one.kind == kind),
                Decimal("0.00"),
            )
            average = spent / Decimal(delivered)
            held += Money(
                (average * Decimal(PER_BALE[kind])).quantize(CENT, rounding=ROUND_HALF_UP)
            )
        return held

    def deliveries(self, kind: str | None = None) -> list[Delivery]:
        rows = [one for one in self._deliveries if kind is None or one.kind == kind]
        return sorted(rows, key=lambda one: (one.arrived_on, one.kind))

    def _known(self, kind: str) -> None:
        if kind not in KINDS:
            raise ValidationError("kind", f"{kind!r} is not wrap this plant buys")
