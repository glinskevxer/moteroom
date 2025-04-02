from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.register import ReceiptRegister

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


def register(*receipts: Receipt) -> ReceiptRegister:
    made = ReceiptRegister("MW14")
    for one in receipts:
        made.issue(one)
    return made


def test_a_register_needs_a_house():
    with pytest.raises(ValidationError):
        ReceiptRegister("  ")


def test_a_receipt_issues_and_reads_back():
    held = register(receipt(1))
    assert held.get("MW00000001").holder == "BLYTHE"
    assert len(held) == 1


def test_a_receipt_for_another_house_is_refused():
    with pytest.raises(ValidationError):
        register().issue(receipt(1, warehouse="MW15"))


def test_the_same_receipt_number_twice_is_refused():
    held = register(receipt(1))
    with pytest.raises(ConflictError):
        held.issue(receipt(1))


def test_a_second_live_receipt_on_one_bale_is_refused():
    held = register(receipt(1))
    with pytest.raises(ConflictError) as caught:
        held.issue(receipt(2, bale_id=BaleId.build(SEASON, GIN, 1)))
    assert caught.value.kind == "bale"


def test_a_bale_can_be_receipted_again_once_the_first_is_released():
    held = register(receipt(1))
    held.release("MW00000001", date(2025, 12, 1), "CALCOT")
    held.issue(receipt(2, bale_id=BaleId.build(SEASON, GIN, 1)))
    assert len(held) == 2


def test_releasing_replaces_the_receipt_in_the_register():
    held = register(receipt(1))
    released = held.release("MW00000001", date(2025, 12, 1), "CALCOT")
    assert released.holder == "CALCOT"
    assert held.get("MW00000001").released_on == date(2025, 12, 1)
    assert held.outstanding() == []
    assert [r.number for r in held.released()] == ["MW00000001"]


def test_releasing_twice_is_refused():
    held = register(receipt(1))
    held.release("MW00000001", date(2025, 12, 1), "CALCOT")
    with pytest.raises(ConflictError):
        held.release("MW00000001", date(2025, 12, 2), "CALCOT")


def test_releasing_a_receipt_nobody_issued():
    with pytest.raises(NotFoundError):
        register().release("MW00000009", date(2025, 12, 1), "CALCOT")


def test_the_register_finds_the_live_receipt_on_a_bale():
    held = register(receipt(1))
    assert held.for_bale(BaleId.build(SEASON, GIN, 1)) is not None
    assert held.for_bale(BaleId.build(SEASON, GIN, 9)) is None


def test_holders_and_their_bales_come_off_the_outstanding_ones():
    held = register(receipt(1), receipt(2, holder="MERRITT"))
    held.release("MW00000002", date(2025, 12, 1), "CALCOT")
    assert held.holders() == ["BLYTHE"]
    assert [r.number for r in held.for_holder("BLYTHE")] == ["MW00000001"]
    assert held.for_holder("MERRITT") == []


def test_the_register_weighs_what_is_still_in_store():
    held = register(receipt(1), receipt(2))
    assert held.net_outstanding() == Weight(1_030)
    held.release("MW00000001", date(2025, 12, 1), "CALCOT")
    assert held.net_outstanding() == Weight(515)


def test_the_register_walks_in_receipt_order():
    held = register(receipt(2), receipt(1))
    assert [r.number for r in held] == ["MW00000001", "MW00000002"]
