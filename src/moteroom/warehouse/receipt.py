"""Warehouse receipts.

A receipt is issued when the warehouse takes a bale in and it is the document
of title, so the bale cannot be shipped without it and it cannot be issued
twice. Most receipts are electronic now, but a paper receipt still turns up
and the two are not interchangeable: a paper receipt has to be surrendered
physically before the bale moves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId
from moteroom.core.weight import Weight

_RECEIPT = re.compile(r"^[A-Z]{2}\d{8}$")
_WAREHOUSE = re.compile(r"^[A-Z0-9]{4,8}$")
MIN_NET_POUNDS = 300
MAX_NET_POUNDS = 700


@dataclass(frozen=True)
class Receipt:
    """One bale in store, and who holds the paper on it."""

    number: str
    warehouse: str
    bale_id: BaleId
    received_on: date
    net: Weight
    holder: str
    electronic: bool = True
    released_on: date | None = None

    def __post_init__(self) -> None:
        if not _RECEIPT.match(self.number):
            raise ValidationError("receipt", f"{self.number!r} is not a receipt number")
        if not _WAREHOUSE.match(self.warehouse):
            raise ValidationError("warehouse", f"{self.warehouse!r} is not a warehouse code")
        if not self.holder.strip():
            raise ValidationError("holder", "is blank")
        if not MIN_NET_POUNDS <= self.net.pounds <= MAX_NET_POUNDS:
            raise ValidationError("net", f"{self.net} is not a bale weight")
        if self.released_on is not None and self.released_on < self.received_on:
            raise ValidationError("released_on", "is before the bale arrived")

    @property
    def is_outstanding(self) -> bool:
        """A receipt still in force, which is what the loan is secured on."""
        return self.released_on is None

    @property
    def needs_surrender(self) -> bool:
        """Paper has to come back before the bale moves. Electronic does not."""
        return not self.electronic and self.is_outstanding

    def days_stored(self, as_of: date) -> int:
        """Days in store as at a date, counting the day it arrived."""
        if as_of < self.received_on:
            raise ValidationError("as_of", "is before the bale arrived")
        end = self.released_on if self.released_on and self.released_on < as_of else as_of
        return (end - self.received_on).days + 1

    def release(self, on: date, to: str) -> Receipt:
        """Take the receipt out of store, which makes a new one rather than editing."""
        if not self.is_outstanding:
            raise ValidationError("released_on", "is already released")
        if not to.strip():
            raise ValidationError("holder", "is blank")
        return Receipt(
            number=self.number,
            warehouse=self.warehouse,
            bale_id=self.bale_id,
            received_on=self.received_on,
            net=self.net,
            holder=to,
            electronic=self.electronic,
            released_on=on,
        )

    def __str__(self) -> str:
        state = "outstanding" if self.is_outstanding else "released"
        return f"receipt {self.number} {self.bale_id} {state}"
