"""The ticket book.

Tickets arrive in whatever order the scale house wrote them and a correction
turns up days later. The book is the only thing that knows which tickets are
still live, so every total in the package is taken from here rather than from
a list of tickets somebody filtered themselves.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.ids import ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight, total
from moteroom.receiving.ticket import ModuleTicket


class TicketBook:
    """Every ticket written this season, and which of them still count."""

    def __init__(self, season: Season) -> None:
        self.season = season
        self._tickets: dict[int, ModuleTicket] = {}
        self._voided: set[int] = set()

    def add(self, ticket: ModuleTicket) -> None:
        """File a ticket, refusing anything that contradicts the book."""
        if ticket.season != self.season:
            raise ValidationError("ticket", f"{ticket.number} is not in {self.season}")
        if ticket.number in self._tickets:
            raise ConflictError("ticket", str(ticket.number), "is already in the book")
        if ticket.voids is not None:
            if ticket.voids not in self._tickets:
                raise NotFoundError("ticket", str(ticket.voids))
            if ticket.voids in self._voided:
                raise ConflictError("ticket", str(ticket.voids), "is already voided")
            self._voided.add(ticket.voids)
        elif any(live.module == ticket.module for live in self.live()):
            raise ConflictError("module", str(ticket.module), "was already weighed in")
        self._tickets[ticket.number] = ticket

    def extend(self, tickets: Iterable[ModuleTicket]) -> None:
        for ticket in tickets:
            self.add(ticket)

    def get(self, number: int) -> ModuleTicket:
        try:
            return self._tickets[number]
        except KeyError as exc:
            raise NotFoundError("ticket", str(number)) from exc

    def is_voided(self, number: int) -> bool:
        return number in self._voided

    def live(self) -> list[ModuleTicket]:
        """Tickets that still count, in the order they were written."""
        return [
            ticket
            for number, ticket in sorted(self._tickets.items())
            if number not in self._voided
        ]

    def voided(self) -> list[ModuleTicket]:
        return [self._tickets[number] for number in sorted(self._voided)]

    def for_module(self, module: ModuleId) -> ModuleTicket:
        for ticket in self.live():
            if ticket.module == module:
                return ticket
        raise NotFoundError("module", str(module))

    def for_producer(self, producer: str) -> list[ModuleTicket]:
        return [ticket for ticket in self.live() if ticket.producer == producer]

    def for_farm(self, producer: str, farm: str) -> list[ModuleTicket]:
        return [ticket for ticket in self.for_producer(producer) if ticket.farm == farm]

    def producers(self) -> list[str]:
        return sorted({ticket.producer for ticket in self.live()})

    def net(self) -> Weight:
        return total([ticket.net for ticket in self.live()])

    def net_for_producer(self, producer: str) -> Weight:
        return total([ticket.net for ticket in self.for_producer(producer)])

    def dry_net(self) -> Weight:
        return total([ticket.dry_weight() for ticket in self.live()])

    def __len__(self) -> int:
        return len(self.live())

    def __iter__(self) -> Iterator[ModuleTicket]:
        return iter(self.live())

    def __contains__(self, number: object) -> bool:
        return number in self._tickets and number not in self._voided
