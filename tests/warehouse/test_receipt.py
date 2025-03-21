from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.warehouse.receipt import Receipt

GIN = GinCode("41207")
BALE = BaleId.build(Season(2025), GIN, 1_204)


def receipt(**overrides: Any) -> Receipt:
    fields: dict[str, Any] = {
        "number": "MW00041207",
        "warehouse": "MW14",
        "bale_id": BALE,
        "received_on": date(2025, 10, 20),
        "net": Weight(515),
        "holder": "BLYTHE",
    }
    fields.update(overrides)
    return Receipt(**fields)


def test_a_receipt_reads_back():
    assert receipt().is_outstanding
    assert str(receipt()) == f"receipt MW00041207 {BALE} outstanding"


@pytest.mark.parametrize("number", ["", "M00041207", "MW0004120", "mw00041207", "MW0004120A"])
def test_a_receipt_number_has_a_shape(number):
    with pytest.raises(ValidationError):
        receipt(number=number)


@pytest.mark.parametrize("code", ["", "MW1", "MW14MW14M", "mw14"])
def test_a_warehouse_code_has_a_shape(code):
    with pytest.raises(ValidationError):
        receipt(warehouse=code)


def test_a_receipt_names_a_holder():
    with pytest.raises(ValidationError):
        receipt(holder="  ")


@pytest.mark.parametrize("pounds", [299, 701])
def test_a_receipt_only_covers_a_bale_weight(pounds):
    with pytest.raises(ValidationError):
        receipt(net=Weight(pounds))


def test_a_release_before_the_bale_arrived_is_refused():
    with pytest.raises(ValidationError):
        receipt(released_on=date(2025, 10, 19))


def test_releasing_makes_a_new_receipt_rather_than_editing():
    held = receipt()
    released = held.release(date(2025, 12, 1), "MERRITT")
    assert held.is_outstanding
    assert not released.is_outstanding
    assert released.holder == "MERRITT"
    assert str(released).endswith("released")


def test_a_receipt_is_only_released_once():
    released = receipt().release(date(2025, 12, 1), "MERRITT")
    with pytest.raises(ValidationError):
        released.release(date(2025, 12, 2), "COLE")


def test_a_release_names_who_took_it():
    with pytest.raises(ValidationError):
        receipt().release(date(2025, 12, 1), " ")


def test_days_in_store_count_the_day_it_arrived():
    assert receipt().days_stored(date(2025, 10, 20)) == 1
    assert receipt().days_stored(date(2025, 11, 20)) == 32


def test_days_in_store_stop_at_the_release():
    released = receipt().release(date(2025, 11, 1), "MERRITT")
    assert released.days_stored(date(2025, 12, 31)) == 13


def test_days_in_store_before_it_arrived_is_refused():
    with pytest.raises(ValidationError):
        receipt().days_stored(date(2025, 10, 19))


def test_paper_has_to_be_surrendered_and_electronic_does_not():
    assert receipt(electronic=False).needs_surrender
    assert not receipt().needs_surrender
    assert not receipt(electronic=False).release(date(2025, 12, 1), "MERRITT").needs_surrender
