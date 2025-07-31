from datetime import date
from typing import Any

from moteroom.core.ids import BaleId, GinCode
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.reporting.position import (
    by_holder,
    by_house,
    money_in_store,
    net_in_store,
    oldest_bale,
    paper_outstanding,
    storage_owed,
)
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.storage import Tariff

GIN = GinCode("41207")
SEASON = Season(2025)
AS_OF = date(2025, 12, 1)
TARIFF = Tariff(
    handling=Money.parse("2.85"),
    daily=Money.parse("0.14"),
    free_days=30,
    minimum_days=60,
)


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


def test_position_by_house_counts_the_outstanding_ones():
    made = by_house([receipt(1), receipt(2, warehouse="MW15")], AS_OF)
    assert made.column("house") == ["MW14", "MW15"]
    assert made.column("bales") == ["1", "1"]
    assert "1,030 lb" in made.notes[0]


def test_position_drops_a_released_receipt():
    released = receipt(2).release(date(2025, 11, 1), "CALCOT")
    made = by_house([receipt(1), released], AS_OF)
    assert made.column("bales") == ["1"]
    assert made.notes[1] == "1 released"


def test_position_by_holder_keys_on_who_holds_it():
    made = by_holder([receipt(1), receipt(2, holder="MERRITT")], AS_OF)
    assert made.column("holder") == ["BLYTHE", "MERRITT"]


def test_position_reports_the_oldest_and_the_average_days():
    made = by_house([receipt(1), receipt(2, received_on=date(2025, 11, 20))], AS_OF)
    assert made.column("oldest") == ["2025-10-20"]
    assert made.column("average days") == ["27"]


def test_an_empty_position_is_empty():
    made = by_house([], AS_OF)
    assert made.is_empty
    assert made.notes[0].startswith("0 outstanding")


def test_storage_owed_bills_every_receipt():
    made = storage_owed([receipt(1), receipt(2)], TARIFF, AS_OF)
    assert made.column("days") == ["43", "43"]
    assert made.column("billed") == ["60", "60"]
    assert "$22.50 owed" in made.notes[0]


def test_storage_skips_a_receipt_from_after_the_date():
    made = storage_owed([receipt(1, received_on=date(2026, 1, 5))], TARIFF, AS_OF)
    assert made.is_empty


def test_storage_counts_what_is_still_free():
    made = storage_owed([receipt(1, received_on=date(2025, 11, 25))], TARIFF, AS_OF)
    assert "1 still inside the free period" in made.notes[1]


def test_paper_receipts_are_picked_out():
    held = [receipt(1), receipt(2, electronic=False)]
    assert [one.number for one in paper_outstanding(held)] == ["MW00000002"]


def test_the_oldest_bale_is_found_and_nothing_is_not_an_error():
    held = [receipt(1, received_on=date(2025, 11, 1)), receipt(2)]
    found = oldest_bale(held)
    assert found is not None
    assert found.number == "MW00000002"
    assert oldest_bale([]) is None


def test_the_totals_read_off_the_outstanding_receipts():
    released = receipt(2).release(date(2025, 11, 1), "CALCOT")
    assert net_in_store([receipt(1), released]) == Weight(515)
    assert money_in_store([receipt(1), released], TARIFF, AS_OF) == Money.parse("11.25")
