from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.receiving.freight import FreightLedger, Haul, Rate

DAY = date(2025, 10, 14)


def rate(**overrides: Any) -> Rate:
    fields: dict[str, Any] = {
        "hauler": "TRUXTON",
        "per_module": Money.parse("42.00"),
        "per_mile": Money.parse("3.10"),
        "minimum": Money.parse("250.00"),
    }
    fields.update(overrides)
    return Rate(**fields)


def haul(**overrides: Any) -> Haul:
    fields: dict[str, Any] = {
        "hauler": "TRUXTON",
        "hauled_on": DAY,
        "tickets": (1, 2, 3),
        "miles": 18,
    }
    fields.update(overrides)
    return Haul(**fields)


def test_a_rate_names_a_hauler_and_holds_three_numbers():
    assert str(rate()).startswith("TRUXTON $42.00 a module")


@pytest.mark.parametrize("field", ["per_module", "per_mile", "minimum"])
def test_a_negative_rate_is_refused(field):
    with pytest.raises(ValidationError):
        rate(**{field: Money.parse("-0.01")})


def test_a_rate_and_a_load_both_name_a_hauler():
    with pytest.raises(ValidationError):
        rate(hauler=" ")
    with pytest.raises(ValidationError):
        haul(hauler=" ")


def test_a_load_carries_something_and_only_once():
    with pytest.raises(ValidationError):
        haul(tickets=())
    with pytest.raises(ValidationError):
        haul(tickets=(1, 1))


@pytest.mark.parametrize("miles", [0, 501, -1])
def test_a_run_off_the_map_is_refused(miles):
    with pytest.raises(ValidationError):
        haul(miles=miles)


def test_a_load_prices_both_ways_and_takes_the_floor():
    charge = haul().charge(rate())
    assert charge.modules == Money.parse("126.00")
    assert charge.miles == Money.parse("55.80")
    assert charge.bound_by == "minimum"
    assert charge.total == Money.parse("250.00")


def test_a_load_bound_by_the_modules():
    charge = haul().charge(rate(minimum=Money.parse("100.00")))
    assert charge.bound_by == "modules"
    assert charge.total == Money.parse("181.80")


def test_a_long_run_is_bound_by_the_mileage():
    charge = haul(miles=120).charge(rate())
    assert charge.bound_by == "mileage"
    assert charge.total == Money.parse("498.00")


def test_a_short_load_is_bound_by_the_minimum():
    charge = haul(tickets=(1,), miles=2).charge(rate())
    assert charge.bound_by == "minimum"
    assert charge.total == Money.parse("250.00")
    assert str(charge) == "$250.00 on the minimum"


def test_a_load_cannot_be_priced_by_another_hauler():
    with pytest.raises(ValidationError):
        haul().charge(rate(hauler="OTHER"))


def test_the_ledger_posts_rates_once():
    ledger = FreightLedger([rate()])
    with pytest.raises(ValidationError):
        ledger.post(rate())
    ledger.post(rate(hauler="OTHER"))
    assert ledger.haulers() == ["OTHER", "TRUXTON"]


def test_a_load_from_a_hauler_with_no_rates():
    with pytest.raises(ValidationError):
        FreightLedger().haul(haul())


def test_the_ledger_totals_what_the_haulers_are_owed():
    ledger = FreightLedger([rate()])
    ledger.haul(haul())
    ledger.haul(haul(tickets=(4, 5), miles=120))
    assert len(ledger) == 2
    assert ledger.owed() == Money.parse("250.00") + Money.parse("456.00")
    assert ledger.owed("OTHER").is_zero


def test_the_freight_reaches_each_module():
    ledger = FreightLedger([rate()])
    ledger.haul(haul())
    charged = ledger.per_ticket()
    assert sorted(charged) == [1, 2, 3]
    assert sum(one.amount for one in charged.values()) == Money.parse("250.00").amount


def test_the_freight_on_a_producer_s_modules():
    ledger = FreightLedger([rate()])
    ledger.haul(haul())
    assert ledger.for_tickets([1, 2]) == Money.parse("166.67")
    assert ledger.for_tickets([9]).is_zero
    assert ledger.for_tickets([]).is_zero


def test_loads_come_back_oldest_first():
    ledger = FreightLedger([rate()])
    ledger.haul(haul(hauled_on=date(2025, 10, 20), tickets=(9,)))
    ledger.haul(haul())
    assert [one.hauled_on for one in ledger.hauls()] == [DAY, date(2025, 10, 20)]
