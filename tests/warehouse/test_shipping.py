from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.shipping import (
    ShippingOrder,
    check_against,
    load_weight,
    plan_loads,
)

GIN = GinCode("41207")
SEASON = Season(2025)


def receipt(number: int, **overrides: Any) -> Receipt:
    fields: dict[str, Any] = {
        "number": f"MW{number:08d}",
        "warehouse": "MW14",
        "bale_id": BaleId.build(SEASON, GIN, number),
        "received_on": date(2025, 10, 20),
        "net": Weight(515),
        "holder": "BLYTHE",
    }
    fields.update(overrides)
    return Receipt(**fields)


def order(*numbers: int, **overrides: Any) -> ShippingOrder:
    fields: dict[str, Any] = {
        "number": "SO000141",
        "warehouse": "MW14",
        "ordered_on": date(2026, 1, 12),
        "buyer": "CALCOT",
        "receipts": tuple(f"MW{n:08d}" for n in (numbers or (1, 2))),
    }
    fields.update(overrides)
    return ShippingOrder(**fields)


def test_an_order_reads_back():
    assert order().count == 2
    assert order().covers("MW00000001")
    assert str(order()) == "order SO000141 2 bales for CALCOT"


@pytest.mark.parametrize("number", ["", "SO12345", "so000141", "SO0001411"])
def test_an_order_number_has_a_shape(number):
    with pytest.raises(ValidationError):
        order(number=number)


def test_an_order_names_a_buyer_and_a_bale():
    with pytest.raises(ValidationError):
        order(buyer="  ")
    with pytest.raises(ValidationError):
        order(receipts=())


def test_an_order_cannot_name_a_receipt_twice():
    with pytest.raises(ValidationError):
        order(receipts=("MW00000001", "MW00000001"))


def test_an_order_cannot_ship_before_it_was_written():
    with pytest.raises(ValidationError):
        order(ship_by=date(2026, 1, 11))


def test_the_truck_count_rounds_up():
    assert order(*range(1, 45)).loads == 1
    assert order(*range(1, 46)).loads == 2
    assert order(1).loads == 1


def test_an_order_lines_up_against_the_receipt_file():
    picked = check_against(order(1, 2), [receipt(1), receipt(2), receipt(3)])
    assert [r.number for r in picked] == ["MW00000001", "MW00000002"]


def test_an_order_naming_a_receipt_nobody_holds():
    with pytest.raises(ConflictError):
        check_against(order(1, 9), [receipt(1)])


def test_an_order_naming_a_receipt_at_another_house():
    with pytest.raises(ConflictError):
        check_against(order(1), [receipt(1, warehouse="MW15")])


def test_an_order_naming_a_receipt_already_released():
    released = receipt(1).release(date(2025, 12, 1), "CALCOT")
    with pytest.raises(ConflictError):
        check_against(order(1), [released])


def test_loads_split_in_receipt_order():
    receipts = [receipt(n) for n in range(1, 6)]
    loads = plan_loads(receipts, per_truck=2)
    assert [len(load) for load in loads] == [2, 2, 1]
    assert loads[0][0] == receipts[0].bale_id


def test_a_load_of_nothing_is_no_loads():
    assert plan_loads([]) == []


def test_a_truck_has_to_carry_something():
    with pytest.raises(ValidationError):
        plan_loads([receipt(1)], per_truck=0)


def test_a_load_weighs_what_its_receipts_weigh():
    assert load_weight([receipt(1), receipt(2)]) == Weight(1_030)
    assert load_weight([]).is_zero
