"""Asking the office to look at a bale again.

A producer who does not believe a card can ask for the bale to be re-classed.
The office takes a fresh sample and sends a new card, which may be better,
worse or the same, and the gin has no say in which. What the gin does is keep
the request, because a re-class costs a fee and somebody has to be told whether
it was worth it.

A request is answered once. The answer is the new card, and comparing it
against the old one is the whole point, so both are kept side by side rather
than the new one overwriting the old.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId
from moteroom.core.money import CentsPerPound

BETTER = "better"
WORSE = "worse"
SAME = "same"
MAX_REASON = 120


@dataclass(frozen=True)
class Request:
    """One bale sent back to the office."""

    bale_id: BaleId
    asked_on: date
    reason: str
    asked_by: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValidationError("reason", "a re-class has to say why")
        if len(self.reason) > MAX_REASON:
            raise ValidationError("reason", f"is longer than {MAX_REASON} characters")
        if not self.asked_by.strip():
            raise ValidationError("asked_by", "is blank")

    def line(self) -> str:
        """The line the office's request file takes."""
        return (
            f"{self.bale_id}{self.asked_on.strftime('%Y%m%d')}{self.asked_by:<10}{self.reason}"
        )

    def __str__(self) -> str:
        return f"{self.bale_id} back to the office: {self.reason}"


@dataclass(frozen=True)
class Answer:
    """The old card and the new one, and which way it went."""

    request: Request
    before: ClassingRecord
    after: ClassingRecord

    def __post_init__(self) -> None:
        if self.before.bale_id != self.request.bale_id:
            raise ValidationError("before", "is a card for another bale")
        if self.after.bale_id != self.request.bale_id:
            raise ValidationError("after", "is a card for another bale")
        if self.after.classed_on < self.before.classed_on:
            raise ValidationError("after", "was classed before the card it replaces")

    def moved(self, rate_before: CentsPerPound, rate_after: CentsPerPound) -> str:
        """Which way the re-class went, priced rather than guessed."""
        if rate_after > rate_before:
            return BETTER
        if rate_after < rate_before:
            return WORSE
        return SAME

    @property
    def colour_changed(self) -> bool:
        return self.before.color != self.after.color

    @property
    def leaf_changed(self) -> bool:
        return self.before.leaf != self.after.leaf

    @property
    def changed(self) -> bool:
        """Whether the office said anything different at all."""
        return self.before.card() != self.after.card()

    def __str__(self) -> str:
        if not self.changed:
            return f"{self.request.bale_id} came back the same"
        return f"{self.request.bale_id} came back as {self.after.color}-{self.after.leaf}"


def render_requests(requests: Sequence[Request], office: str, on: date) -> str:
    """Write the file the classing office takes."""
    if not requests:
        raise ValidationError("requests", "a file has to ask about something")
    seen = {str(one.bale_id) for one in requests}
    if len(seen) != len(requests):
        raise ValidationError("requests", "asks about the same bale twice")
    head = f"RCLHDR{office.strip().upper():<8}{on.strftime('%Y%m%d')}{len(requests):06d}"
    return "\n".join([head, *(one.line() for one in requests), f"RCLTRL{len(requests):06d}"])
