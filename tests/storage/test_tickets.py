from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.ids import ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.storage.book import Book
from moteroom.storage.producers import ProducerRepository
from moteroom.storage.tickets import TicketRepository

SEASON = Season(2025)


def ticket(number: int, **overrides: Any) -> ModuleTicket:
    fields: dict[str, Any] = {
        "number": number,
        "module": ModuleId(f"HW-{number:06d}"),
        "producer": "BLYTHE",
        "farm": "3312",
        "weighed_on": date(2025, 10, 14),
        "gross": Weight(38_400),
        "tare": Weight(17_200),
        "moisture": Decimal("9.4"),
    }
    fields.update(overrides)
    return ModuleTicket(**fields)


@pytest.fixture()
def tickets():
    with Book.open() as book:
        people = ProducerRepository(book.connection)
        people.add(Producer("BLYTHE", "Blythe Farms"))
        people.add(Producer("MERRITT", "Merritt"))
        yield TicketRepository(book.connection)


def test_a_ticket_saves_and_reads_back_whole(tickets):
    tickets.add(ticket(1))
    read = tickets.get(SEASON, 1)
    assert read == ticket(1)
    assert read.net == Weight(21_200)
    assert read.moisture == Decimal("9.4")


def test_a_ticket_nobody_wrote(tickets):
    with pytest.raises(NotFoundError):
        tickets.get(SEASON, 9)


def test_the_same_number_twice_in_a_season_is_refused(tickets):
    tickets.add(ticket(1))
    with pytest.raises(ConflictError):
        tickets.add(ticket(1, module=ModuleId("HW-999999")))


def test_a_ticket_for_a_producer_nobody_added_is_refused(tickets):
    with pytest.raises(ConflictError):
        tickets.add(ticket(1, producer="GHOST"))


def test_tickets_come_back_in_number_order(tickets):
    tickets.add(ticket(2))
    tickets.add(ticket(1))
    assert [t.number for t in tickets.for_season(SEASON)] == [1, 2]
    assert tickets.count(SEASON) == 2


def test_tickets_can_be_pulled_per_producer(tickets):
    tickets.add(ticket(1))
    tickets.add(ticket(2, producer="MERRITT"))
    assert [t.number for t in tickets.for_producer(SEASON, "MERRITT")] == [2]
    assert tickets.for_producer(SEASON, "NOBODY") == []


def test_the_next_number_follows_the_last_one(tickets):
    assert tickets.next_number(SEASON) == 1
    tickets.add(ticket(7))
    assert tickets.next_number(SEASON) == 8


def test_a_season_loads_back_into_a_ticket_book(tickets):
    tickets.add(ticket(1))
    tickets.add(ticket(2))
    tickets.add(ticket(3, voids=2, module=ModuleId("HW-000002")))
    loaded = tickets.book(SEASON)
    assert [t.number for t in loaded.live()] == [1, 3]
    assert loaded.net() == Weight(21_200 * 2)


def test_another_season_is_kept_apart(tickets):
    tickets.add(ticket(1))
    tickets.add(ticket(1, weighed_on=date(2026, 10, 14), module=ModuleId("HW-100001")))
    assert tickets.count(SEASON) == 1
    assert tickets.count(Season(2026)) == 1
