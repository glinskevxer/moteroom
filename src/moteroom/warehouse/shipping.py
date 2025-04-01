"""Shipping orders.

A buyer calls for bales by receipt, not by bale, and the warehouse loads them
onto trucks. The order is the authority to move them and it is written against
receipts that are still outstanding, so an order naming a released receipt is
refused when it is written rather than when the truck is at the dock.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from moteroom.core.errors import ConflictError, ValidationError
from moteroom.core.ids import BaleId
from moteroom.core.weight import Weight, total
from moteroom.warehouse.receipt import Receipt

_ORDER = re.compile(r"^SO\d{6}$")
TRUCKLOAD = 44


@dataclass(frozen=True)
class ShippingOrder:
    """One order to move a set of bales out of a warehouse."""

    number: str
    warehouse: str
    ordered_on: date
    buyer: str
    receipts: tuple[str, ...]
    ship_by: date | None = None

    def __post_init__(self) -> None:
        if not _ORDER.match(self.number):
            raise ValidationError("order", f"{self.number!r} is not an order number")
        if not self.buyer.strip():
            raise ValidationError("buyer", "is blank")
        if not self.receipts:
            raise ValidationError("receipts", "an order has to name a bale")
        if len(set(self.receipts)) != len(self.receipts):
            raise ValidationError("receipts", "names the same receipt twice")
        if self.ship_by is not None and self.ship_by < self.ordered_on:
            raise ValidationError("ship_by", "is before the order was written")

    @property
    def count(self) -> int:
        return len(self.receipts)

    @property
    def loads(self) -> int:
        """Trucks needed, which is what the yard wants to know."""
        return -(-self.count // TRUCKLOAD)

    def covers(self, number: str) -> bool:
        return number in self.receipts

    def __str__(self) -> str:
        return f"order {self.number} {self.count} bales for {self.buyer}"


def check_against(order: ShippingOrder, held: Iterable[Receipt]) -> list[Receipt]:
    """Line an order up against the receipt file, refusing what cannot ship."""
    by_number = {receipt.number: receipt for receipt in held}
    picked: list[Receipt] = []
    for number in order.receipts:
        receipt = by_number.get(number)
        if receipt is None:
            raise ConflictError("order", order.number, f"names no receipt {number}")
        if receipt.warehouse != order.warehouse:
            raise ConflictError("order", order.number, f"receipt {number} is at another house")
        if not receipt.is_outstanding:
            raise ConflictError("order", order.number, f"receipt {number} is already released")
        picked.append(receipt)
    return picked


def plan_loads(receipts: Sequence[Receipt], per_truck: int = TRUCKLOAD) -> list[list[BaleId]]:
    """Split the bales into truckloads in receipt order."""
    if per_truck < 1:
        raise ValidationError("per_truck", "must carry at least one bale")
    return [
        [receipt.bale_id for receipt in receipts[start : start + per_truck]]
        for start in range(0, len(receipts), per_truck)
    ]


def load_weight(receipts: Iterable[Receipt]) -> Weight:
    return total([receipt.net for receipt in receipts])
