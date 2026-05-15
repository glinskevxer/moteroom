from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.ginning.energy import EnergyLog, Reading

DAY = date(2025, 10, 16)
POWER = Money.parse("0.11")
GAS = Money.parse("0.95")


def reading(**overrides: Any) -> Reading:
    fields: dict[str, Any] = {
        "day": DAY,
        "bales": 360,
        "kilowatt_hours": 12_600,
        "therms": 540,
        "moisture": Decimal("9.4"),
    }
    fields.update(overrides)
    return Reading(**fields)


def test_a_day_reads_per_bale():
    made = reading()
    assert made.power_per_bale() == Decimal("35.000")
    assert made.gas_per_bale() == Decimal("1.500")
    assert str(made).endswith("35.000 kWh a bale")


def test_a_day_prices_at_the_rates_the_plant_is_on():
    assert reading().cost(POWER, GAS) == Money.parse("1899.00")


@pytest.mark.parametrize("field", ["bales", "kilowatt_hours", "therms"])
def test_a_negative_meter_is_refused(field):
    with pytest.raises(ValidationError):
        reading(**{field: -1})
    with pytest.raises(ValidationError):
        reading(**{field: True})


def test_burning_energy_and_making_nothing_is_refused():
    with pytest.raises(ValidationError):
        reading(bales=0)


def test_a_day_that_did_nothing_at_all_is_allowed():
    made = reading(bales=0, kilowatt_hours=0, therms=0)
    assert made.power_per_bale() == Decimal("0.000")
    assert made.cost(POWER, GAS).is_zero


def test_a_negative_rate_is_refused():
    with pytest.raises(ValidationError):
        reading().cost(Money.parse("-0.01"), GAS)
    with pytest.raises(ValidationError):
        reading().cost(POWER, Money.parse("-0.01"))


def test_a_moisture_off_the_probe_is_refused():
    with pytest.raises(ValidationError):
        reading(moisture=Decimal("30.0"))


def test_the_log_weights_the_season_by_bales():
    log = EnergyLog()
    log.extend(
        [
            reading(),
            reading(day=date(2025, 10, 17), bales=100, kilowatt_hours=5_000, therms=300),
        ]
    )
    assert log.bales() == 460
    assert log.power_per_bale() == Decimal("38.261")
    assert log.gas_per_bale() == Decimal("1.826")


def test_a_day_is_logged_once():
    log = EnergyLog()
    log.add(reading())
    with pytest.raises(ValidationError):
        log.add(reading())


def test_the_log_prices_the_season_and_the_bale():
    log = EnergyLog()
    log.add(reading())
    assert log.cost(POWER, GAS) == Money.parse("1899.00")
    assert log.cost_per_bale(POWER, GAS) == Money.parse("5.28")


def test_an_empty_log_divides_by_nothing_safely():
    log = EnergyLog()
    assert log.power_per_bale() == Decimal("0.000")
    assert log.gas_per_bale() == Decimal("0.000")
    assert log.cost_per_bale(POWER, GAS).is_zero
    assert log.wettest() is None
    assert len(log) == 0


def test_the_wettest_day_is_where_the_gas_went():
    log = EnergyLog()
    log.extend([reading(), reading(day=date(2025, 10, 17), moisture=Decimal("13.0"))])
    found = log.wettest()
    assert found is not None
    assert found.day == date(2025, 10, 17)
    assert [one.day for one in log.readings()][0] == DAY
