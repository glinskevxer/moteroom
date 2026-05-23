"""What the hauling came to.

Two pages the office wants in December. What each haulier is owed, because
they invoice and somebody has to check it, and what the freight came to against
each producer, because that is what appears on their statement and they will
ask.

Both come off the same loads. The haulier page adds by who drove and the
producer page adds by whose modules were on the truck, and the two totals are
the same number arrived at from opposite ends, which is worth printing.
"""

from __future__ import annotations

from collections.abc import Sequence

from moteroom.core.money import Money, total_money
from moteroom.receiving.freight import FreightLedger
from moteroom.receiving.ticket import ModuleTicket
from moteroom.reporting.report import Report


def by_hauler(ledger: FreightLedger) -> Report:
    """What each haulier is owed, most first."""
    rows = []
    for hauler in ledger.haulers():
        loads = ledger.hauls(hauler)
        if not loads:
            continue
        rows.append(
            (
                hauler,
                str(len(loads)),
                str(sum(one.modules for one in loads)),
                str(sum(one.miles for one in loads)),
                str(ledger.owed(hauler)),
            )
        )
    rows.sort(key=lambda row: (-len(row[4]), row[0]))
    return Report(
        title="freight by haulier",
        headers=("haulier", "loads", "modules", "miles", "owed"),
        rows=tuple(rows),
        right=(1, 2, 3, 4),
        notes=(
            f"{len(ledger)} loads, {ledger.owed()} owed"
            if len(ledger)
            else "nothing hauled yet",
        ),
    )


def by_producer(ledger: FreightLedger, tickets: Sequence[ModuleTicket]) -> Report:
    """What the freight came to against each producer's modules."""
    charged = ledger.per_ticket()
    owned: dict[str, list[int]] = {}
    for ticket in tickets:
        owned.setdefault(ticket.producer, []).append(ticket.number)
    rows = []
    for producer in sorted(owned):
        numbers = owned[producer]
        amount = ledger.for_tickets(numbers)
        hauled = sum(1 for number in numbers if number in charged)
        rows.append((producer, str(len(numbers)), str(hauled), str(amount)))
    return Report(
        title="freight by producer",
        headers=("producer", "modules", "hauled", "freight"),
        rows=tuple(rows),
        right=(1, 2, 3),
        notes=(
            f"{total_money([ledger.for_tickets(one) for one in owned.values()])} charged on",
        ),
    )


def unhauled(ledger: FreightLedger, tickets: Sequence[ModuleTicket]) -> list[ModuleTicket]:
    """Modules with no load against them, which the producer brought in themselves."""
    charged = ledger.per_ticket()
    return [ticket for ticket in tickets if ticket.number not in charged]


def owed_to(ledger: FreightLedger, hauler: str) -> Money:
    """What one haulier is owed, which is what their invoice should say."""
    return ledger.owed(hauler)
