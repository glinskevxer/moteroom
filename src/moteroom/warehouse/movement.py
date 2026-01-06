"""Moving a bale from one warehouse to another.

A bale does not carry its receipt with it. The house it leaves cancels the
receipt it issued and the house it arrives at issues its own, so a movement is
two receipts and a gap in between where the bale is on a truck and nobody holds
a receipt on it at all.

That gap is the whole reason this is not a field update. A movement that is
recorded as one receipt changing its warehouse loses the fact that the first
house stopped being liable for the bale on the day it left.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from moteroom.core.errors import ConflictError, ValidationError
from moteroom.core.ids import BaleId
from moteroom.core.weight import Weight
from moteroom.warehouse.receipt import Receipt

IN_TRANSIT = "in transit"


@dataclass(frozen=True)
class Movement:
    """One bale leaving one house for another."""

    bale_id: BaleId
    net: Weight
    left: str
    arrived: str
    left_on: date
    arrived_on: date | None
    old_receipt: str
    new_receipt: str | None

    def __post_init__(self) -> None:
        if self.left == self.arrived:
            raise ValidationError("arrived", "a bale does not move to the house it is in")
        if self.arrived_on is not None and self.arrived_on < self.left_on:
            raise ValidationError("arrived_on", "is before the bale left")
        if (self.arrived_on is None) != (self.new_receipt is None):
            raise ValidationError("new_receipt", "arrives with the bale or not at all")

    @property
    def in_transit(self) -> bool:
        """Whether the bale is still on the truck as far as the book knows."""
        return self.arrived_on is None

    def days_in_transit(self, as_of: date) -> int:
        """How long the bale has been between houses."""
        if as_of < self.left_on:
            raise ValidationError("as_of", "is before the bale left")
        end = self.arrived_on if self.arrived_on is not None else as_of
        return (end - self.left_on).days

    def __str__(self) -> str:
        if self.in_transit:
            return f"{self.bale_id} left {self.left} for {self.arrived}, {IN_TRANSIT}"
        return f"{self.bale_id} moved {self.left} to {self.arrived}"


def send(receipt: Receipt, to: str, on: date) -> Movement:
    """Cancel the receipt at the house the bale is leaving."""
    if not receipt.is_outstanding:
        raise ConflictError("receipt", receipt.number, "is already released")
    if not to.strip():
        raise ValidationError("to", "a movement has to name a house")
    if on < receipt.received_on:
        raise ValidationError("on", "is before the bale arrived at the first house")
    return Movement(
        bale_id=receipt.bale_id,
        net=receipt.net,
        left=receipt.warehouse,
        arrived=to.strip().upper(),
        left_on=on,
        arrived_on=None,
        old_receipt=receipt.number,
        new_receipt=None,
    )


def arrive(movement: Movement, number: str, on: date, holder: str) -> tuple[Movement, Receipt]:
    """Issue the receiving house's own receipt and close the movement."""
    if not movement.in_transit:
        raise ConflictError("movement", str(movement.bale_id), "has already arrived")
    if on < movement.left_on:
        raise ValidationError("on", "is before the bale left")
    receipt = Receipt(
        number=number.strip().upper(),
        warehouse=movement.arrived,
        bale_id=movement.bale_id,
        received_on=on,
        net=movement.net,
        holder=holder.strip().upper(),
    )
    closed = Movement(
        bale_id=movement.bale_id,
        net=movement.net,
        left=movement.left,
        arrived=movement.arrived,
        left_on=movement.left_on,
        arrived_on=on,
        old_receipt=movement.old_receipt,
        new_receipt=receipt.number,
    )
    return closed, receipt
