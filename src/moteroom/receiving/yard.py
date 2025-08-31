"""The module yard.

Modules sit in the yard between the scale and the feeder, and the order they
are ginned in is not the order they arrived. Wet cotton heats. A module that
came in over the wet line has a few days before it starts to go off, and one
that has been sitting past that is the next thing through the plant whatever
else is in front of it.

So the yard hands back a running order rather than a list, and it says why
each module is where it is.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.ids import ModuleId
from moteroom.core.weight import Weight, total
from moteroom.receiving.ticket import ModuleTicket

WET_MOISTURE = Decimal("11.0")
WET_HOLD_DAYS = 7
STALE_DAYS = 45

URGENT = 0
WET = 1
STALE = 2
ORDINARY = 3

REASONS = {
    URGENT: "wet and held too long",
    WET: "wet",
    STALE: "sat too long",
    ORDINARY: "in turn",
}


@dataclass(frozen=True)
class Waiting:
    """One module in the yard, with why it sits where it does."""

    ticket: ModuleTicket
    priority: int
    days: int

    @property
    def reason(self) -> str:
        return REASONS[self.priority]

    @property
    def is_urgent(self) -> bool:
        return self.priority == URGENT

    def __str__(self) -> str:
        return f"module {self.ticket.module} {self.days} days, {self.reason}"


def is_wet(ticket: ModuleTicket) -> bool:
    """Whether a module came in over the line the plant calls wet."""
    return ticket.moisture > WET_MOISTURE


def days_waiting(ticket: ModuleTicket, as_of: date) -> int:
    """Days in the yard, counting the day it was weighed in."""
    if as_of < ticket.weighed_on:
        raise ValidationError("as_of", "is before the module was weighed in")
    return (as_of - ticket.weighed_on).days + 1


def priority_of(ticket: ModuleTicket, as_of: date) -> int:
    """Where a module sits in the running order."""
    days = days_waiting(ticket, as_of)
    if is_wet(ticket):
        return URGENT if days > WET_HOLD_DAYS else WET
    return STALE if days > STALE_DAYS else ORDINARY


class ModuleYard:
    """What is in the yard and what order it should go through the plant."""

    def __init__(self) -> None:
        self._waiting: dict[int, ModuleTicket] = {}
        self._ginned: set[int] = set()

    def receive(self, ticket: ModuleTicket) -> None:
        """Put a weighed module in the yard."""
        if ticket.number in self._waiting or ticket.number in self._ginned:
            raise ConflictError("ticket", str(ticket.number), "is already in the yard")
        if ticket.is_correction:
            raise ValidationError("ticket", "a correction does not put a module in the yard")
        self._waiting[ticket.number] = ticket

    def extend(self, tickets: Iterable[ModuleTicket]) -> None:
        for ticket in tickets:
            self.receive(ticket)

    def gin(self, number: int) -> ModuleTicket:
        """Take a module out of the yard because it went through the plant."""
        if number not in self._waiting:
            raise NotFoundError("module", str(number))
        ticket = self._waiting.pop(number)
        self._ginned.add(number)
        return ticket

    def holds(self, number: int) -> bool:
        return number in self._waiting

    def running_order(self, as_of: date) -> list[Waiting]:
        """Everything in the yard, worst first and oldest first inside that."""
        lines = [
            Waiting(ticket, priority_of(ticket, as_of), days_waiting(ticket, as_of))
            for ticket in self._waiting.values()
        ]
        return sorted(lines, key=lambda line: (line.priority, -line.days, line.ticket.number))

    def urgent(self, as_of: date) -> list[Waiting]:
        """Modules that should have gone through the plant already."""
        return [line for line in self.running_order(as_of) if line.is_urgent]

    def next_module(self, as_of: date) -> Waiting | None:
        order = self.running_order(as_of)
        return order[0] if order else None

    def net_waiting(self) -> Weight:
        return total([ticket.net for ticket in self._waiting.values()])

    def producers(self) -> list[str]:
        return sorted({ticket.producer for ticket in self._waiting.values()})

    def modules(self) -> list[ModuleId]:
        return sorted(ticket.module for ticket in self._waiting.values())

    def __len__(self) -> int:
        return len(self._waiting)

    def __iter__(self) -> Iterator[ModuleTicket]:
        return iter(self._waiting.values())
