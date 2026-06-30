"""How long the cotton has been sitting.

Storage is the cost that creeps. Nobody notices a bale sitting in a warehouse
because nothing happens to it, and the invoice arrives quarterly with a number
somebody then has to explain.

So the receipts are put in buckets by how long they have been in store, which
is how the trade talks about it, and each bucket carries what it is running up.
The buckets are cumulative in nobody's head, so they are exclusive here: a bale
in the sixty day bucket is not also in the thirty.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from moteroom.core.money import Money, total_money
from moteroom.core.weight import Weight, total
from moteroom.reporting.report import Report
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.storage import Tariff, charge_for

BUCKETS = ((0, 30), (31, 60), (61, 90), (91, 180), (181, 10_000))


def label(low: int, high: int) -> str:
    """What a bucket is called on the page."""
    if high >= 10_000:
        return f"{low} days and over"
    return f"{low} to {high} days"


def bucket_of(days: int) -> tuple[int, int]:
    """Which bucket a number of days falls in."""
    for low, high in BUCKETS:
        if low <= days <= high:
            return (low, high)
    return BUCKETS[-1]


def aging(receipts: Sequence[Receipt], tariff: Tariff, as_of: date) -> Report:
    """Bales in store by how long they have been there."""
    held = [
        receipt
        for receipt in receipts
        if receipt.is_outstanding and receipt.received_on <= as_of
    ]
    rows = []
    for low, high in BUCKETS:
        inside = [one for one in held if bucket_of(one.days_stored(as_of)) == (low, high)]
        charges = [charge_for(one, tariff, as_of) for one in inside]
        rows.append(
            (
                label(low, high),
                str(len(inside)),
                str(total([one.net for one in inside]).pounds),
                str(total_money([one.total for one in charges])),
            )
        )
    return Report(
        title=f"bales in store as at {as_of.isoformat()}",
        headers=("age", "bales", "net", "charges"),
        rows=tuple(rows),
        right=(1, 2, 3),
        notes=_notes(held, tariff, as_of),
    )


def _notes(held: Sequence[Receipt], tariff: Tariff, as_of: date) -> tuple[str, ...]:
    if not held:
        return ("nothing in store",)
    charges = [charge_for(one, tariff, as_of) for one in held]
    oldest = max(one.days_stored(as_of) for one in held)
    return (
        f"{len(held)} bales, {total([one.net for one in held])}, "
        f"{total_money([one.total for one in charges])} run up",
        f"the oldest has been there {oldest} days",
    )


def over(receipts: Sequence[Receipt], days: int, as_of: date) -> list[Receipt]:
    """Receipts older than a number of days, oldest first."""
    held = [
        one
        for one in receipts
        if one.is_outstanding and one.received_on <= as_of and one.days_stored(as_of) > days
    ]
    return sorted(held, key=lambda one: (-one.days_stored(as_of), one.number))


def running_up(receipts: Sequence[Receipt], tariff: Tariff, as_of: date) -> Money:
    """What the bales in store have run up in charges so far."""
    return total_money(
        [
            charge_for(one, tariff, as_of).total
            for one in receipts
            if one.is_outstanding and one.received_on <= as_of
        ]
    )


def net_in_store(receipts: Sequence[Receipt], as_of: date) -> Weight:
    """Lint in store on a day."""
    return total(
        [one.net for one in receipts if one.is_outstanding and one.received_on <= as_of]
    )
