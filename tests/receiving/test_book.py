from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.ids import ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.receiving.book import TicketBook
from moteroom.receiving.ticket import ModuleTicket

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


def book(*tickets: ModuleTicket) -> TicketBook:
    made = TicketBook(SEASON)
    made.extend(tickets)
    return made


def test_a_book_holds_tickets_in_order():
    held = book(ticket(2), ticket(1))
    assert [t.number for t in held.live()] == [1, 2]
    assert len(held) == 2


def test_a_ticket_can_be_looked_up():
    held = book(ticket(1))
    assert held.get(1).number == 1
    assert 1 in held


def test_a_missing_ticket_says_so():
    with pytest.raises(NotFoundError):
        book().get(9)


def test_a_ticket_number_is_used_once():
    held = book(ticket(1))
    with pytest.raises(ConflictError):
        held.add(ticket(1, module=ModuleId("HW-999999")))


def test_a_module_is_weighed_in_once():
    held = book(ticket(1))
    with pytest.raises(ConflictError) as caught:
        held.add(ticket(2, module=ModuleId("HW-000001")))
    assert caught.value.kind == "module"


def test_a_ticket_from_another_season_is_refused():
    with pytest.raises(ValidationError):
        book().add(ticket(1, weighed_on=date(2024, 10, 14)))


def test_a_correction_takes_the_first_ticket_out():
    held = book(ticket(1), ticket(2, voids=1, module=ModuleId("HW-000001")))
    assert [t.number for t in held.live()] == [2]
    assert held.is_voided(1)
    assert 1 not in held
    assert [t.number for t in held.voided()] == [1]


def test_a_correction_has_to_name_a_ticket_that_exists():
    with pytest.raises(NotFoundError):
        book().add(ticket(2, voids=1))


def test_a_ticket_is_only_voided_once():
    held = book(ticket(1), ticket(2, voids=1, module=ModuleId("HW-000001")))
    with pytest.raises(ConflictError):
        held.add(ticket(3, voids=1))


def test_lookup_by_module_skips_the_voided_one():
    held = book(ticket(1), ticket(2, voids=1, module=ModuleId("HW-000001")))
    assert held.for_module(ModuleId("HW-000001")).number == 2


def test_lookup_by_a_module_nobody_weighed():
    with pytest.raises(NotFoundError):
        book(ticket(1)).for_module(ModuleId("HW-777777"))


def test_totals_come_off_the_live_tickets():
    held = book(ticket(1), ticket(2), ticket(3, voids=2, module=ModuleId("HW-000002")))
    assert held.net() == Weight(21_200 * 2)
    assert held.net_for_producer("BLYTHE") == Weight(21_200 * 2)
    assert held.net_for_producer("MERRITT").is_zero


def test_producers_and_farms_are_listed_from_the_live_tickets():
    held = book(ticket(1), ticket(2, producer="MERRITT", farm="4410"))
    assert held.producers() == ["BLYTHE", "MERRITT"]
    assert [t.number for t in held.for_farm("MERRITT", "4410")] == [2]
    assert held.for_farm("BLYTHE", "4410") == []


def test_dry_net_is_lighter_when_the_yard_is_wet():
    held = book(ticket(1, moisture=Decimal("13.0")))
    assert held.dry_net() < held.net()


def test_iterating_a_book_walks_the_live_tickets():
    held = book(ticket(1), ticket(2))
    assert [t.number for t in held] == [1, 2]
