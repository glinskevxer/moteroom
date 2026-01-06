from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.warehouse.movement import arrive, send
from moteroom.warehouse.receipt import Receipt

GIN = GinCode("41207")
SEASON = Season(2025)
LEFT = date(2026, 1, 12)


def receipt(**overrides: Any) -> Receipt:
    fields: dict[str, Any] = {
        "number": "MW00000001",
        "warehouse": "MW14",
        "bale_id": BaleId.build(SEASON, GIN, 1),
        "received_on": date(2025, 10, 20),
        "net": Weight(515),
        "holder": "BLYTHE",
    }
    fields.update(overrides)
    return Receipt(**fields)


def test_a_bale_leaves_one_house_and_is_in_transit():
    made = send(receipt(), "mw15", LEFT)
    assert made.in_transit
    assert made.left == "MW14"
    assert made.arrived == "MW15"
    assert made.new_receipt is None
    assert "in transit" in str(made)


def test_a_released_receipt_cannot_be_sent():
    released = receipt().release(date(2025, 12, 1), "CALCOT")
    with pytest.raises(ConflictError):
        send(released, "MW15", LEFT)


def test_a_movement_names_where_it_is_going():
    with pytest.raises(ValidationError):
        send(receipt(), "  ", LEFT)


def test_a_bale_does_not_move_to_the_house_it_is_in():
    with pytest.raises(ValidationError):
        send(receipt(), "MW14", LEFT)


def test_a_movement_cannot_start_before_the_bale_arrived():
    with pytest.raises(ValidationError):
        send(receipt(), "MW15", date(2025, 10, 1))


def test_arriving_issues_the_second_house_its_own_receipt():
    moved, made = arrive(
        send(receipt(), "MW15", LEFT), "MX00000001", date(2026, 1, 14), "blythe"
    )
    assert not moved.in_transit
    assert moved.new_receipt == "MX00000001"
    assert made.warehouse == "MW15"
    assert made.holder == "BLYTHE"
    assert made.net == Weight(515)
    assert str(moved) == f"{made.bale_id} moved MW14 to MW15"


def test_a_bale_only_arrives_once():
    moved, _ = arrive(send(receipt(), "MW15", LEFT), "MX00000001", date(2026, 1, 14), "BLYTHE")
    with pytest.raises(ConflictError):
        arrive(moved, "MX00000002", date(2026, 1, 15), "BLYTHE")


def test_a_bale_cannot_arrive_before_it_left():
    with pytest.raises(ValidationError):
        arrive(send(receipt(), "MW15", LEFT), "MX00000001", date(2026, 1, 11), "BLYTHE")


def test_the_days_on_the_truck_are_counted():
    made = send(receipt(), "MW15", LEFT)
    assert made.days_in_transit(date(2026, 1, 14)) == 2
    moved, _ = arrive(made, "MX00000001", date(2026, 1, 14), "BLYTHE")
    assert moved.days_in_transit(date(2026, 2, 1)) == 2


def test_asking_before_the_bale_left():
    with pytest.raises(ValidationError):
        send(receipt(), "MW15", LEFT).days_in_transit(date(2026, 1, 11))


def test_a_movement_that_arrived_without_a_receipt_is_refused():
    from moteroom.warehouse.movement import Movement

    with pytest.raises(ValidationError):
        Movement(
            bale_id=BaleId.build(SEASON, GIN, 1),
            net=Weight(515),
            left="MW14",
            arrived="MW15",
            left_on=LEFT,
            arrived_on=date(2026, 1, 14),
            old_receipt="MW00000001",
            new_receipt=None,
        )
