from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.ids import ModuleId
from moteroom.core.weight import Weight
from moteroom.receiving.ticket import ModuleTicket
from moteroom.receiving.yard import (
    ORDINARY,
    STALE,
    URGENT,
    WET,
    ModuleYard,
    days_waiting,
    is_wet,
    priority_of,
)

DAY = date(2025, 10, 14)


def ticket(number: int, **overrides: Any) -> ModuleTicket:
    fields: dict[str, Any] = {
        "number": number,
        "module": ModuleId(f"HW-{number:06d}"),
        "producer": "BLYTHE",
        "farm": "3312",
        "weighed_on": DAY,
        "gross": Weight(38_400),
        "tare": Weight(17_200),
        "moisture": Decimal("9.4"),
    }
    fields.update(overrides)
    return ModuleTicket(**fields)


def yard(*tickets: ModuleTicket) -> ModuleYard:
    made = ModuleYard()
    made.extend(tickets)
    return made


def test_a_wet_module_is_over_the_line():
    assert is_wet(ticket(1, moisture=Decimal("11.1")))
    assert not is_wet(ticket(1, moisture=Decimal("11.0")))


def test_days_waiting_counts_the_day_it_came_in():
    assert days_waiting(ticket(1), DAY) == 1
    assert days_waiting(ticket(1), date(2025, 10, 20)) == 7


def test_asking_before_it_came_in():
    with pytest.raises(ValidationError):
        days_waiting(ticket(1), date(2025, 10, 13))


@pytest.mark.parametrize(
    ("moisture", "as_of", "expected"),
    [
        ("9.4", DAY, ORDINARY),
        ("9.4", date(2025, 12, 1), STALE),
        ("12.0", DAY, WET),
        ("12.0", date(2025, 10, 20), WET),
        ("12.0", date(2025, 10, 21), URGENT),
    ],
)
def test_the_running_order_is_decided_by_wet_then_age(moisture, as_of, expected):
    assert priority_of(ticket(1, moisture=Decimal(moisture)), as_of) == expected


def test_a_module_goes_in_and_comes_out():
    held = yard(ticket(1))
    assert held.holds(1)
    assert len(held) == 1
    assert held.gin(1).number == 1
    assert not held.holds(1)
    assert len(held) == 0


def test_a_module_cannot_go_in_twice():
    held = yard(ticket(1))
    with pytest.raises(ConflictError):
        held.receive(ticket(1))


def test_a_ginned_module_cannot_come_back():
    held = yard(ticket(1))
    held.gin(1)
    with pytest.raises(ConflictError):
        held.receive(ticket(1))


def test_a_correction_does_not_put_anything_in_the_yard():
    held = yard(ticket(1))
    with pytest.raises(ValidationError):
        held.receive(ticket(2, voids=1))


def test_ginning_a_module_nobody_received():
    with pytest.raises(NotFoundError):
        yard().gin(9)


def test_the_wet_one_goes_first():
    held = yard(ticket(1), ticket(2, moisture=Decimal("12.0")))
    order = held.running_order(DAY)
    assert [line.ticket.number for line in order] == [2, 1]
    assert order[0].reason == "wet"


def test_the_wet_one_held_too_long_goes_ahead_of_the_merely_wet():
    held = yard(
        ticket(1, moisture=Decimal("12.0")),
        ticket(2, moisture=Decimal("12.5"), weighed_on=date(2025, 10, 1)),
    )
    order = held.running_order(DAY)
    assert order[0].ticket.number == 2
    assert order[0].is_urgent
    assert [line.ticket.number for line in held.urgent(DAY)] == [2]


def test_the_oldest_goes_first_inside_a_band():
    held = yard(ticket(1), ticket(2, weighed_on=date(2025, 10, 10)))
    assert [line.ticket.number for line in held.running_order(DAY)] == [2, 1]


def test_the_next_module_is_the_top_of_the_order():
    held = yard(ticket(1), ticket(2, moisture=Decimal("12.0")))
    found = held.next_module(DAY)
    assert found is not None
    assert found.ticket.number == 2
    assert held.next_module(DAY) is not None


def test_an_empty_yard_has_nothing_next():
    assert yard().next_module(DAY) is None
    assert yard().urgent(DAY) == []


def test_the_yard_weighs_what_is_still_in_it():
    held = yard(ticket(1), ticket(2))
    assert held.net_waiting() == Weight(42_400)
    held.gin(1)
    assert held.net_waiting() == Weight(21_200)


def test_the_yard_lists_who_is_waiting():
    held = yard(ticket(1), ticket(2, producer="MERRITT"))
    assert held.producers() == ["BLYTHE", "MERRITT"]
    assert [str(module) for module in held.modules()] == ["HW-000001", "HW-000002"]


def test_a_waiting_line_prints_why_it_is_there():
    held = yard(ticket(1, moisture=Decimal("12.0")))
    assert str(held.running_order(DAY)[0]) == "module HW-000001 1 days, wet"
