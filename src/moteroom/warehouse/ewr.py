"""The electronic warehouse receipt transfer.

Receipts move between holders through a provider rather than by handing paper
over, and the provider takes a fixed width file. The gin sends what it wants
transferred and gets an acknowledgement back saying which ones landed, so the
two files are read together: anything the acknowledgement does not mention did
not transfer, whatever the gin thinks it sent.

    columns  field
    1-10     receipt number
    11-18    warehouse
    19-30    bale id
    31-40    holder it goes to
    41-45    net pounds
    46-53    received date, YYYYMMDD
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from moteroom.core.errors import MoteroomError, ValidationError
from moteroom.core.weight import Weight, total
from moteroom.warehouse.receipt import Receipt

LINE_WIDTH = 53
HEADER = "EWRHDR"
TRAILER = "EWRTRL"
ACCEPTED = "A"
REJECTED = "R"


@dataclass(frozen=True)
class Acknowledgement:
    """What the provider said about a transfer."""

    provider: str
    answered_on: date
    accepted: tuple[str, ...]
    rejected: tuple[tuple[str, str], ...]

    @property
    def is_clean(self) -> bool:
        return not self.rejected

    def took(self, number: str) -> bool:
        return number in self.accepted

    def missing(self, sent: Sequence[str]) -> tuple[str, ...]:
        """Receipts sent that the answer says nothing about at all."""
        answered = set(self.accepted) | {number for number, _ in self.rejected}
        return tuple(number for number in sent if number not in answered)

    def __str__(self) -> str:
        return f"{len(self.accepted)} accepted, {len(self.rejected)} rejected"


def render_transfer(receipts: Sequence[Receipt], provider: str, on: date, to: str) -> str:
    """Write the file the provider takes."""
    if not receipts:
        raise ValidationError("receipts", "a transfer has to move something")
    if not provider.strip() or len(provider.strip()) > 6:
        raise ValidationError("provider", f"{provider!r} is not a provider code")
    if not to.strip():
        raise ValidationError("to", "a transfer has to name who it goes to")
    for receipt in receipts:
        if not receipt.is_outstanding:
            raise ValidationError("receipts", f"{receipt.number} is already released")
        if receipt.needs_surrender:
            raise ValidationError("receipts", f"{receipt.number} is paper and cannot transfer")
    lines = [f"{HEADER}{provider.strip().upper():<6}{on.strftime('%Y%m%d')}{len(receipts):06d}"]
    lines.extend(
        f"{receipt.number:<10}"
        f"{receipt.warehouse:<8}"
        f"{receipt.bale_id}"
        f"{to.strip().upper():<10}"
        f"{receipt.net.pounds:05d}"
        f"{receipt.received_on.strftime('%Y%m%d')}"
        for receipt in receipts
    )
    lines.append(f"{TRAILER}{len(receipts):06d}")
    return "\n".join(lines)


def transfer_weight(receipts: Sequence[Receipt]) -> Weight:
    """What a transfer moves, which the provider bills on."""
    return total([receipt.net for receipt in receipts])


def parse_acknowledgement(text: str) -> Acknowledgement:
    """Read the answer that comes back."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith(HEADER):
        raise MoteroomError("the acknowledgement has no header")
    provider = lines[0][6:12].strip()
    try:
        answered_on = datetime.strptime(lines[0][12:20], "%Y%m%d").date()
        declared = int(lines[0][20:26])
    except ValueError as exc:
        raise MoteroomError("the acknowledgement header will not read") from exc
    if not lines[-1].startswith(TRAILER):
        raise MoteroomError("the acknowledgement has no trailer")

    accepted: list[str] = []
    rejected: list[tuple[str, str]] = []
    for line in lines[1:-1]:
        number = line[:10].strip()
        state = line[10:11]
        reason = line[11:].strip()
        if not number:
            raise MoteroomError("the acknowledgement names a receipt with no number")
        if state == ACCEPTED:
            accepted.append(number)
        elif state == REJECTED:
            rejected.append((number, reason or "no reason given"))
        else:
            raise MoteroomError(f"{state!r} is not an answer this provider gives")
    if len(accepted) + len(rejected) != declared:
        raise MoteroomError("the acknowledgement holds a different count than it claims")
    return Acknowledgement(provider, answered_on, tuple(accepted), tuple(rejected))
