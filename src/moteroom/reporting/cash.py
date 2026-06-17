"""What the gin owes and what it is owed.

Four different obligations, all of them real money, and none of them on the
same page anywhere else. Cheques written and not cleared. Money held back under
a deferral. Equity standing in members' names. And on the other side, producers
who owe the gin.

They net against each other only on paper. A cheque that has not cleared is
still going to clear, so it is not cover for a producer's overdue account, and
the page says both numbers rather than the difference alone.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from moteroom.core.money import Money, total_money
from moteroom.reporting.report import Report
from moteroom.settlement.cheque import Cheque
from moteroom.settlement.deferred import Deferral
from moteroom.settlement.late import Account


def position(
    cheques: Sequence[Cheque],
    deferrals: Sequence[Deferral],
    accounts: Sequence[Account],
    equity: Money,
    as_of: date,
) -> Report:
    """Everything the gin owes and is owed, on one page."""
    outstanding = total_money([one.amount for one in cheques if one.is_outstanding])
    held = total_money([one.due(as_of) for one in deferrals])
    owed = total_money([one.due(as_of) for one in accounts if not one.is_paid])
    rows = (
        ("cheques outstanding", str(outstanding)),
        ("deferrals held", str(held)),
        ("equity standing", str(equity)),
        ("owed to the gin", str(owed)),
        ("net obligation", str(outstanding + held + equity - owed)),
    )
    return Report(
        title=f"cash position as at {as_of.isoformat()}",
        headers=("what", "amount"),
        rows=rows,
        right=(1,),
        notes=_notes(cheques, deferrals, accounts, as_of),
    )


def _notes(
    cheques: Sequence[Cheque],
    deferrals: Sequence[Deferral],
    accounts: Sequence[Account],
    as_of: date,
) -> tuple[str, ...]:
    stale = [one for one in cheques if one.is_stale(as_of)]
    matured = [one for one in deferrals if one.is_matured(as_of)]
    late = [one for one in accounts if one.is_late(as_of)]
    found = []
    if stale:
        found.append(f"{len(stale)} cheques have gone stale")
    if matured:
        found.append(f"{len(matured)} deferrals have come due")
    if late:
        found.append(f"{len(late)} accounts are past their grace period")
    return tuple(found) if found else ("nothing needs chasing",)


def stale_cheques(cheques: Sequence[Cheque], as_of: date) -> Report:
    """Cheques the bank will not take any more."""
    rows = tuple(
        (one.number, one.payee, str(one.amount), one.issued_on.isoformat())
        for one in sorted(cheques, key=lambda one: one.issued_on)
        if one.is_stale(as_of)
    )
    return Report(
        title="stale cheques",
        headers=("cheque", "payee", "amount", "written"),
        rows=rows,
        right=(2,),
        notes=(f"{len(rows)} to rewrite",),
    )


def coming_due(deferrals: Sequence[Deferral], as_of: date, within: int = 30) -> Report:
    """Deferrals that fall due soon, so the money is there when they do."""
    rows = tuple(
        (one.producer, str(one.amount), one.pay_on.isoformat(), str((one.pay_on - as_of).days))
        for one in sorted(deferrals, key=lambda one: one.pay_on)
        if 0 <= (one.pay_on - as_of).days <= within
    )
    return Report(
        title=f"deferrals due inside {within} days",
        headers=("producer", "held", "pays", "days"),
        rows=rows,
        right=(1, 3),
        notes=(f"{len(rows)} to pay",),
    )
