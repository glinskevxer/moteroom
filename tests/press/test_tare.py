from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.press.tare import BAGS, TIES, Delivery, TareStore

DAY = date(2025, 9, 1)


def delivery(**overrides: Any) -> Delivery:
    fields: dict[str, Any] = {
        "kind": BAGS,
        "arrived_on": DAY,
        "count": 500,
        "cost_each": Money.parse("6.40"),
        "supplier": "WRAPCO",
    }
    fields.update(overrides)
    return Delivery(**fields)


def stocked(bags: int = 500, ties: int = 4_000) -> TareStore:
    store = TareStore()
    store.extend(
        [
            delivery(count=bags),
            delivery(kind=TIES, count=ties, cost_each=Money.parse("0.85")),
        ]
    )
    return store


def test_a_delivery_prices_itself():
    assert delivery().value == Money.parse("3200.00")
    assert str(delivery()) == "500 bags from WRAPCO at $6.40"


@pytest.mark.parametrize("kind", ["", "string", "BAGS"])
def test_wrap_the_plant_does_not_buy(kind):
    with pytest.raises(ValidationError):
        delivery(kind=kind)


def test_a_delivery_brings_something_from_somebody():
    with pytest.raises(ValidationError):
        delivery(count=0)
    with pytest.raises(ValidationError):
        delivery(supplier=" ")
    with pytest.raises(ValidationError):
        delivery(count=True)
    with pytest.raises(ValidationError):
        delivery(cost_each=Money.parse("-0.01"))


def test_the_store_counts_both_kinds_apart():
    store = stocked()
    assert store.on_hand(BAGS) == 500
    assert store.on_hand(TIES) == 4_000
    assert store.bales_left() == 500


def test_pressing_uses_a_bag_and_eight_ties():
    store = stocked()
    store.press(10)
    assert store.on_hand(BAGS) == 490
    assert store.on_hand(TIES) == 3_920
    assert store.used(BAGS) == 10


def test_the_store_runs_out_on_whichever_is_shorter():
    store = stocked(bags=500, ties=800)
    assert store.bales_left() == 100


def test_pressing_more_than_the_store_holds_is_refused():
    store = stocked(bags=5, ties=4_000)
    with pytest.raises(ValidationError) as caught:
        store.press(6)
    assert "only 5 left" in caught.value.message
    assert store.used(BAGS) == 0


def test_a_negative_run_is_refused():
    with pytest.raises(ValidationError):
        stocked().press(-1)
    with pytest.raises(ValidationError):
        stocked().short_for(-1)


def test_the_store_says_what_has_to_be_bought():
    store = stocked(bags=100, ties=400)
    assert store.short_for(100) == {TIES: 400}
    assert store.short_for(50) == {}
    assert store.short_for(200) == {BAGS: 100, TIES: 1_200}


def test_the_store_values_what_is_on_hand():
    store = stocked()
    assert store.value() == Money.parse("6600.00")
    store.press(100)
    assert store.value() == Money.parse("5280.00")


def test_the_cost_of_wrapping_one_bale():
    assert stocked().cost_per_bale() == Money.parse("13.20")


def test_an_empty_store_is_worth_nothing_and_wraps_nothing():
    store = TareStore()
    assert store.value().is_zero
    assert store.cost_per_bale().is_zero
    assert store.bales_left() == 0
    assert store.on_hand(BAGS) == 0


def test_asking_about_wrap_the_plant_does_not_buy():
    with pytest.raises(ValidationError):
        TareStore().on_hand("string")


def test_deliveries_come_back_oldest_first():
    store = stocked()
    store.receive(delivery(arrived_on=date(2025, 8, 1), count=100))
    assert [one.arrived_on for one in store.deliveries(BAGS)][0] == date(2025, 8, 1)
    assert len(store.deliveries()) == 3
