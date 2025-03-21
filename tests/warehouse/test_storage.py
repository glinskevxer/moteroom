from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.storage import Tariff, charge_for, days_billed

GIN = GinCode("41207")
BALE = BaleId.build(Season(2025), GIN, 1_204)


def tariff(**overrides: Any) -> Tariff:
    fields: dict[str, Any] = {
        "handling": Money.parse("2.85"),
        "daily": Money.parse("0.14"),
        "free_days": 30,
        "minimum_days": 60,
        "compression": Money.parse("4.10"),
    }
    fields.update(overrides)
    return Tariff(**fields)


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


@pytest.mark.parametrize("field", ["handling", "daily", "compression"])
def test_a_negative_rate_is_refused(field):
    with pytest.raises(ValidationError):
        tariff(**{field: Money.parse("-0.01")})


@pytest.mark.parametrize("field", ["free_days", "minimum_days"])
def test_a_negative_day_count_is_refused(field):
    with pytest.raises(ValidationError):
        tariff(**{field: -1})


def test_nothing_is_billed_inside_the_free_period():
    assert days_billed(30, tariff()) == 0
    assert days_billed(1, tariff()) == 0


def test_the_first_day_past_the_free_period_hits_the_floor():
    assert days_billed(31, tariff()) == 60


def test_past_the_floor_it_is_day_for_day():
    assert days_billed(91, tariff()) == 61
    assert days_billed(120, tariff()) == 90


def test_a_tariff_with_no_free_period_or_floor():
    plain = tariff(free_days=0, minimum_days=0)
    assert days_billed(1, plain) == 1
    assert days_billed(0, plain) == 0


def test_a_negative_day_count_will_not_bill():
    with pytest.raises(ValidationError):
        days_billed(-1, tariff())


def test_a_bale_inside_the_free_period_still_pays_handling():
    billed = charge_for(receipt(), tariff(), date(2025, 11, 1))
    assert billed.is_free_period
    assert billed.storage.is_zero
    assert billed.total == Money.parse("2.85")


def test_a_bale_past_the_free_period_pays_the_floor():
    billed = charge_for(receipt(), tariff(), date(2025, 11, 20))
    assert billed.days_stored == 32
    assert billed.days_billed == 60
    assert billed.storage == Money.parse("8.40")
    assert billed.total == Money.parse("11.25")


def test_compression_is_only_charged_when_it_happened():
    plain = charge_for(receipt(), tariff(), date(2025, 11, 20))
    pressed = charge_for(receipt(), tariff(), date(2025, 11, 20), compressed=True)
    assert plain.compression.is_zero
    assert pressed.compression == Money.parse("4.10")
    assert pressed.total - plain.total == Money.parse("4.10")


def test_a_released_bale_stops_accruing():
    released = receipt().release(date(2025, 12, 1), "MERRITT")
    billed = charge_for(released, tariff(), date(2026, 6, 1))
    assert billed.days_stored == 43
    assert billed.days_billed == 60


def test_a_charge_prints_its_line():
    billed = charge_for(receipt(), tariff(), date(2025, 11, 20))
    assert str(billed) == f"bale {BALE} 60 days $11.25"
