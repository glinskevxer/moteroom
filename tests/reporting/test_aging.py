from datetime import date
from typing import Any

from moteroom.core.ids import BaleId, GinCode
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.reporting.aging import aging, bucket_of, label, net_in_store, over, running_up
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.storage import Tariff

GIN = GinCode("41207")
SEASON = Season(2025)
AS_OF = date(2026, 2, 1)
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


def test_a_bucket_is_named_the_way_the_trade_says_it():
    assert label(0, 30) == "0 to 30 days"
    assert label(181, 10_000) == "181 days and over"


def test_every_age_falls_in_exactly_one_bucket():
    for days in range(0, 400):
        low, high = bucket_of(days)
        assert low <= days <= high


def test_the_page_puts_each_bale_in_one_bucket():
    made = aging([receipt(1), receipt(2, received_on=date(2026, 1, 20))], TARIFF, AS_OF)
    counted = dict(zip(made.column("age"), made.column("bales"), strict=True))
    assert counted["91 to 180 days"] == "1"
    assert counted["0 to 30 days"] == "1"
    assert counted["181 days and over"] == "0"


def test_the_page_carries_what_the_bales_have_run_up():
    made = aging([receipt(1)], TARIFF, AS_OF)
    charges = dict(zip(made.column("age"), made.column("charges"), strict=True))
    assert charges["91 to 180 days"] != "$0.00"


def test_an_empty_store_says_so():
    made = aging([], TARIFF, AS_OF)
    assert made.notes == ("nothing in store",)
    assert made.column("bales") == ["0"] * 5


def test_the_notes_say_how_old_the_oldest_is():
    made = aging([receipt(1)], TARIFF, AS_OF)
    assert "the oldest has been there 105 days" in made.notes[1]


def test_a_released_bale_is_not_in_store():
    released = receipt(1).release(date(2025, 12, 1), "CALCOT")
    assert aging([released], TARIFF, AS_OF).notes == ("nothing in store",)
    assert net_in_store([released], AS_OF).is_zero


def test_a_receipt_from_after_the_date_is_not_counted():
    later = receipt(1, received_on=date(2026, 3, 1))
    assert aging([later], TARIFF, AS_OF).notes == ("nothing in store",)


def test_the_old_ones_come_back_oldest_first():
    held = [receipt(1), receipt(2, received_on=date(2025, 9, 1))]
    assert [one.number for one in over(held, 90, AS_OF)] == ["MW00000002", "MW00000001"]
    assert over(held, 400, AS_OF) == []


def test_what_the_store_has_run_up():
    assert running_up([receipt(1)], TARIFF, AS_OF) > Money.zero()
    assert running_up([], TARIFF, AS_OF).is_zero
    assert net_in_store([receipt(1)], AS_OF) == Weight(515)
