"""Receipts and shipping orders on disc.

A release is an update rather than an insert, which is the one place in this
book where a row changes after it is written. It has to be, because the receipt
number is what the buyer and the lender both hold, and issuing a second number
for the same bale is exactly what the register exists to stop.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.ids import BaleId
from moteroom.storage import rows as read
from moteroom.storage.repository import Repository
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.register import ReceiptRegister
from moteroom.warehouse.shipping import ShippingOrder

RECEIPT_COLUMNS = (
    "number, warehouse, bale_id, received_on, net, holder, electronic, released_on"
)
ORDER_COLUMNS = "number, warehouse, ordered_on, buyer, ship_by"


class ReceiptRepository(Repository):
    """Warehouse receipts across every house the gin ships to."""

    def issue(self, receipt: Receipt) -> None:
        if self.for_bale(receipt.bale_id) is not None:
            raise ConflictError("bale", str(receipt.bale_id), "is already receipted")
        self.write(
            f"INSERT INTO receipts ({RECEIPT_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                receipt.number,
                receipt.warehouse,
                str(receipt.bale_id),
                receipt.received_on.isoformat(),
                receipt.net.pounds,
                receipt.holder,
                int(receipt.electronic),
                receipt.released_on.isoformat() if receipt.released_on else None,
            ),
            lambda: ConflictError("receipt", receipt.number, "will not go in the book"),
        )

    def release(self, number: str, on: date, to: str) -> Receipt:
        held = self.get(number)
        if not held.is_outstanding:
            raise ConflictError("receipt", number, "is already released")
        released = held.release(on, to)
        self.connection.execute(
            "UPDATE receipts SET holder = ?, released_on = ? WHERE number = ?",
            (released.holder, on.isoformat(), number),
        )
        return released

    def get(self, number: str) -> Receipt:
        row = self.connection.execute(
            f"SELECT {RECEIPT_COLUMNS} FROM receipts WHERE number = ?", (number,)
        ).fetchone()
        if row is None:
            raise NotFoundError("receipt", number)
        return self._read(row)

    def for_bale(self, bale_id: BaleId) -> Receipt | None:
        row = self.connection.execute(
            f"SELECT {RECEIPT_COLUMNS} FROM receipts WHERE bale_id = ? AND released_on IS NULL",
            (str(bale_id),),
        ).fetchone()
        return None if row is None else self._read(row)

    def last_released(self, bale_id: BaleId) -> Receipt | None:
        """The most recent released receipt on a bale, if there is one.

        A bale that has left store has no live receipt, and the question of
        where it went is answered by the receipt that was released rather than
        by its absence.
        """
        row = self.one(
            f"SELECT {RECEIPT_COLUMNS} FROM receipts "
            "WHERE bale_id = ? AND released_on IS NOT NULL "
            "ORDER BY released_on DESC, number DESC",
            (str(bale_id),),
        )
        return None if row is None else self._read(row)

    def outstanding(self, warehouse: str | None = None) -> list[Receipt]:
        if warehouse is None:
            rows = self.connection.execute(
                f"SELECT {RECEIPT_COLUMNS} FROM receipts "
                "WHERE released_on IS NULL ORDER BY number"
            )
        else:
            rows = self.connection.execute(
                f"SELECT {RECEIPT_COLUMNS} FROM receipts "
                "WHERE released_on IS NULL AND warehouse = ? ORDER BY number",
                (warehouse,),
            )
        return [self._read(row) for row in rows.fetchall()]

    def register(self, warehouse: str) -> ReceiptRegister:
        """Rebuild one house's register out of the book."""
        made = ReceiptRegister(warehouse)
        rows = self.connection.execute(
            f"SELECT {RECEIPT_COLUMNS} FROM receipts WHERE warehouse = ? ORDER BY number",
            (warehouse,),
        )
        for row in rows.fetchall():
            receipt = self._read(row)
            if receipt.is_outstanding:
                made.issue(receipt)
        return made

    def _read(self, row: sqlite3.Row) -> Receipt:
        return Receipt(
            number=row["number"],
            warehouse=row["warehouse"],
            bale_id=BaleId(row["bale_id"]),
            received_on=read.day(row, "received_on"),
            net=read.weight(row, "net"),
            holder=row["holder"],
            electronic=read.flag(row, "electronic"),
            released_on=read.maybe_day(row, "released_on"),
        )


class OrderRepository(Repository):
    """Shipping orders and the receipts they call for."""

    def add(self, order: ShippingOrder) -> None:
        refuse = _named(lambda: ConflictError("order", order.number, "will not go in the book"))
        with self.atomic():
            self.write(
                f"INSERT INTO orders ({ORDER_COLUMNS}) VALUES (?, ?, ?, ?, ?)",
                (
                    order.number,
                    order.warehouse,
                    order.ordered_on.isoformat(),
                    order.buyer,
                    order.ship_by.isoformat() if order.ship_by else None,
                ),
                refuse,
            )
            self.write_many(
                "INSERT INTO order_receipts (order_number, receipt, position) VALUES (?, ?, ?)",
                [
                    (order.number, receipt, position)
                    for position, receipt in enumerate(order.receipts)
                ],
                refuse,
            )

    def get(self, number: str) -> ShippingOrder:
        row = self.connection.execute(
            f"SELECT {ORDER_COLUMNS} FROM orders WHERE number = ?", (number,)
        ).fetchone()
        if row is None:
            raise NotFoundError("order", number)
        rows = self.connection.execute(
            "SELECT receipt FROM order_receipts WHERE order_number = ? ORDER BY position",
            (number,),
        )
        ship_by = row["ship_by"]
        return ShippingOrder(
            number=row["number"],
            warehouse=row["warehouse"],
            ordered_on=read.day(row, "ordered_on"),
            buyer=row["buyer"],
            receipts=tuple(r["receipt"] for r in rows),
            ship_by=None if ship_by is None else date.fromisoformat(ship_by),
        )

    def open_orders(self) -> list[ShippingOrder]:
        rows = self.connection.execute("SELECT number FROM orders ORDER BY number")
        return [self.get(row["number"]) for row in rows.fetchall()]


def _named(refusal: Callable[[], Exception]) -> Callable[[], Exception]:
    """Keep one refusal for a pair of writes that stand or fall together."""
    return refusal
