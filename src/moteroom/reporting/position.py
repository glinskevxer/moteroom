"""Where the cotton is and what it is costing.

Position is asked two ways. The lender asks by holder, because that is what
the loan is secured on. The plant asks by house, because that is where the
storage bill comes from. Both are the same receipts counted on a different
key, and both are taken as at a date rather than as at now.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date

from moteroom.core.money import Money, total_money
from moteroom.core.weight import Weight, total
from moteroom.reporting.report import Report
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.storage import Tariff, charge_for


def _grouped(
    receipts: Sequence[Receipt],
    key: Callable[[Receipt], str],
    as_of: date,
    label: str,
    title: str,
) -> Report:
    live = [receipt for receipt in receipts if receipt.is_outstanding]
    groups: dict[str, list[Receipt]] = {}
    for receipt in live:
        groups.setdefault(key(receipt), []).append(receipt)
    rows = []
    for name in sorted(groups):
        held = groups[name]
        oldest = min(receipt.received_on for receipt in held)
        days = sum(receipt.days_stored(as_of) for receipt in held) // len(held)
        rows.append(
            (
                name,
                str(len(held)),
                str(total([receipt.net for receipt in held]).pounds),
                oldest.isoformat(),
                str(days),
            )
        )
    return Report(
        title=f"{title} as at {as_of.isoformat()}",
        headers=(label, "bales", "net", "oldest", "average days"),
        rows=tuple(rows),
        right=(1, 2, 4),
        notes=(
            f"{len(live)} outstanding, {total([receipt.net for receipt in live])}",
            f"{len(receipts) - len(live)} released",
        ),
    )


def by_house(receipts: Sequence[Receipt], as_of: date) -> Report:
    """Position by warehouse, which is who bills the storage."""
    return _grouped(receipts, lambda receipt: receipt.warehouse, as_of, "house", "position")


def by_holder(receipts: Sequence[Receipt], as_of: date) -> Report:
    """Position by holder, which is what the lender asks for."""
    return _grouped(receipts, lambda receipt: receipt.holder, as_of, "holder", "holdings")


def storage_owed(receipts: Sequence[Receipt], tariff: Tariff, as_of: date) -> Report:
    """What the warehouse will bill, receipt by receipt."""
    charges = [
        (receipt, charge_for(receipt, tariff, as_of))
        for receipt in receipts
        if receipt.received_on <= as_of
    ]
    rows = tuple(
        (
            receipt.number,
            str(receipt.bale_id),
            str(charge.days_stored),
            str(charge.days_billed),
            str(charge.storage),
            str(charge.total),
        )
        for receipt, charge in charges
    )
    owed = total_money([charge.total for _, charge in charges])
    free = sum(1 for _, charge in charges if charge.is_free_period)
    return Report(
        title=f"storage owed as at {as_of.isoformat()}",
        headers=("receipt", "bale", "days", "billed", "storage", "total"),
        rows=rows,
        right=(2, 3, 4, 5),
        notes=(
            f"{len(charges)} receipts, {owed} owed",
            f"{free} still inside the free period",
        ),
    )


def paper_outstanding(receipts: Sequence[Receipt]) -> list[Receipt]:
    """Paper receipts still in force, which have to be surrendered by hand."""
    return [receipt for receipt in receipts if receipt.needs_surrender]


def oldest_bale(receipts: Sequence[Receipt]) -> Receipt | None:
    """The bale that has been in store longest, if there is one."""
    live = [receipt for receipt in receipts if receipt.is_outstanding]
    if not live:
        return None
    return min(live, key=lambda receipt: (receipt.received_on, receipt.number))


def net_in_store(receipts: Sequence[Receipt]) -> Weight:
    """Lint still in store, which is what the position adds to."""
    return total([receipt.net for receipt in receipts if receipt.is_outstanding])


def money_in_store(receipts: Sequence[Receipt], tariff: Tariff, as_of: date) -> Money:
    """What the bales still in store have run up in charges."""
    return total_money(
        [
            charge_for(receipt, tariff, as_of).total
            for receipt in receipts
            if receipt.is_outstanding and receipt.received_on <= as_of
        ]
    )
