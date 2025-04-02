"""The receipt register.

One warehouse, one register. It is the only thing allowed to issue or release
a receipt, because two receipts outstanding on the same bale is the failure
that costs somebody a bale, and it cannot be caught later by reading the file.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.ids import BaleId
from moteroom.core.weight import Weight, total
from moteroom.warehouse.receipt import Receipt


class ReceiptRegister:
    """Every receipt this house has issued, outstanding or not."""

    def __init__(self, warehouse: str) -> None:
        if not warehouse.strip():
            raise ValidationError("warehouse", "is blank")
        self.warehouse = warehouse
        self._receipts: dict[str, Receipt] = {}

    def issue(self, receipt: Receipt) -> None:
        """Take a bale in, refusing a second live receipt on the same bale."""
        if receipt.warehouse != self.warehouse:
            raise ValidationError("warehouse", f"{receipt.number} is for another house")
        if receipt.number in self._receipts:
            raise ConflictError("receipt", receipt.number, "is already issued")
        live = self.for_bale(receipt.bale_id)
        if live is not None:
            raise ConflictError("bale", str(receipt.bale_id), "is already receipted")
        self._receipts[receipt.number] = receipt

    def release(self, number: str, on: date, to: str) -> Receipt:
        """Release a receipt and keep the released copy in its place."""
        held = self.get(number)
        if not held.is_outstanding:
            raise ConflictError("receipt", number, "is already released")
        released = held.release(on, to)
        self._receipts[number] = released
        return released

    def get(self, number: str) -> Receipt:
        try:
            return self._receipts[number]
        except KeyError as exc:
            raise NotFoundError("receipt", number) from exc

    def for_bale(self, bale_id: BaleId) -> Receipt | None:
        """The outstanding receipt on a bale, if there is one."""
        for receipt in self._receipts.values():
            if receipt.bale_id == bale_id and receipt.is_outstanding:
                return receipt
        return None

    def outstanding(self) -> list[Receipt]:
        return [r for r in self.all() if r.is_outstanding]

    def released(self) -> list[Receipt]:
        return [r for r in self.all() if not r.is_outstanding]

    def for_holder(self, holder: str) -> list[Receipt]:
        return [r for r in self.outstanding() if r.holder == holder]

    def holders(self) -> list[str]:
        return sorted({r.holder for r in self.outstanding()})

    def net_outstanding(self) -> Weight:
        return total([r.net for r in self.outstanding()])

    def all(self) -> list[Receipt]:
        return [self._receipts[number] for number in sorted(self._receipts)]

    def __len__(self) -> int:
        return len(self._receipts)

    def __iter__(self) -> Iterator[Receipt]:
        return iter(self.all())
