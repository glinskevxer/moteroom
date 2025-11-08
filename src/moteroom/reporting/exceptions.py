"""The one report anybody reads every morning.

Every other report says what happened. This one says what is wrong, and it is
the only place in the package that pulls from every part of the season at once:
modules held too long, bales with no card back, lots where the press and the
sheet disagree, receipts running up storage, contracts that will not fill
before their window shuts.

Each finding carries how bad it is, so the page sorts itself and the first
three lines are the ones worth walking out to the yard about.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from moteroom.classing.record import ClassingRecord
from moteroom.core.ids import BaleId
from moteroom.core.weight import Weight
from moteroom.ginning.reconcile import Reconciliation
from moteroom.receiving.yard import Waiting
from moteroom.reporting.report import Report
from moteroom.settlement.contract import Contract, Fill
from moteroom.warehouse.receipt import Receipt

URGENT = "urgent"
WATCH = "watch"
NOTE = "note"

ORDER = {URGENT: 0, WATCH: 1, NOTE: 2}

UNCLASSED_DAYS = 21
STORAGE_DAYS = 120
WINDOW_DAYS = 14


@dataclass(frozen=True)
class Finding:
    """One thing that needs somebody to do something."""

    level: str
    what: str
    detail: str

    def __post_init__(self) -> None:
        if self.level not in ORDER:
            raise ValueError(f"{self.level!r} is not a level this report has")

    @property
    def rank(self) -> int:
        return ORDER[self.level]

    def __str__(self) -> str:
        return f"{self.level}: {self.what} {self.detail}"


def from_yard(waiting: Sequence[Waiting]) -> list[Finding]:
    """Modules the yard says should have gone through the plant."""
    return [
        Finding(URGENT, str(line.ticket.module), f"{line.reason}, {line.days} days in the yard")
        for line in waiting
        if line.is_urgent
    ]


def from_unclassed(bales: Sequence[tuple[BaleId, int]]) -> list[Finding]:
    """Bales pressed a long time ago with no card back."""
    return [
        Finding(
            WATCH if days < UNCLASSED_DAYS * 2 else URGENT,
            str(bale_id),
            f"pressed {days} days ago and still not classed",
        )
        for bale_id, days in bales
        if days > UNCLASSED_DAYS
    ]


def from_reconciliations(checks: Sequence[Reconciliation]) -> list[Finding]:
    """Lots where the press and the lot sheet do not agree."""
    return [
        Finding(WATCH, f"lot {check.lot}", f"press and sheet differ by {check.drift}%")
        for check in checks
        if not check.agrees
    ]


def from_storage(receipts: Sequence[Receipt], as_of: date) -> list[Finding]:
    """Bales that have been in store long enough to be worth moving."""
    return [
        Finding(
            NOTE,
            receipt.number,
            f"{receipt.days_stored(as_of)} days in store at {receipt.warehouse}",
        )
        for receipt in receipts
        if receipt.is_outstanding and receipt.days_stored(as_of) > STORAGE_DAYS
    ]


def from_contracts(contracts: Sequence[tuple[Contract, Fill]], as_of: date) -> list[Finding]:
    """Contracts that will not fill before the window shuts."""
    found = []
    for contract, fill in contracts:
        if fill.is_complete or as_of > contract.delivery_to:
            continue
        left = (contract.delivery_to - as_of).days
        if left <= WINDOW_DAYS:
            found.append(
                Finding(
                    URGENT,
                    contract.number,
                    f"{fill.remaining} bales short with {left} days left",
                )
            )
    return found


def from_cards(cards: Sequence[ClassingRecord]) -> list[Finding]:
    """Cards the loan will not take, and the ones the plant caused."""
    found = []
    for card in cards:
        if card.is_below_grade:
            found.append(Finding(WATCH, str(card.bale_id), "classed below grade"))
        for finding in card.gin_faults:
            found.append(Finding(NOTE, str(card.bale_id), f"carries {finding}"))
    return found


def from_unsettled(producers: Sequence[str], lint: dict[str, Weight]) -> list[Finding]:
    """Producers with cotton in and no settlement written."""
    return [
        Finding(NOTE, producer, f"not settled, {lint.get(producer, Weight.zero())} of lint")
        for producer in producers
    ]


def build(findings: Sequence[Finding], as_of: date) -> Report:
    """Sort the findings worst first and put them on a page."""
    ordered = sorted(findings, key=lambda one: (one.rank, one.what))
    rows = tuple((one.level, one.what, one.detail) for one in ordered)
    urgent = sum(1 for one in ordered if one.level == URGENT)
    return Report(
        title=f"exceptions as at {as_of.isoformat()}",
        headers=("level", "what", "detail"),
        rows=rows,
        notes=(
            f"{len(ordered)} findings, {urgent} urgent"
            if ordered
            else "nothing needs attention",
        ),
    )


def worst_level(findings: Sequence[Finding]) -> str | None:
    """The worst level anything reached, which is what a status line shows."""
    if not findings:
        return None
    return min(findings, key=lambda one: one.rank).level


def counts(findings: Sequence[Finding]) -> dict[str, int]:
    """How many findings there are at each level."""
    tallied = {level: 0 for level in ORDER}
    for one in findings:
        tallied[one.level] += 1
    return tallied


def urgency(findings: Sequence[Finding]) -> Decimal:
    """The share of findings that are urgent, which trends over a season."""
    if not findings:
        return Decimal("0.00")
    urgent = sum(1 for one in findings if one.level == URGENT)
    return (Decimal(urgent) * Decimal(100) / Decimal(len(findings))).quantize(Decimal("0.01"))
