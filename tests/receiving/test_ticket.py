from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.receiving.ticket import ModuleTicket, clean_moisture


def ticket(**overrides: Any) -> ModuleTicket:
    fields: dict[str, Any] = {
        "number": 1,
        "module": ModuleId("HW-004182"),
        "producer": "BLYTHE",
        "farm": "3312",
        "weighed_on": date(2025, 10, 14),
        "gross": Weight(38_400),
        "tare": Weight(17_200),
        "moisture": Decimal("9.4"),
    }
    fields.update(overrides)
    return ModuleTicket(**fields)


def test_net_is_the_difference_across_the_scale():
    assert ticket().net == Weight(21_200)


def test_the_season_comes_off_the_weigh_date():
    assert ticket().season == Season(2025)
    assert ticket(weighed_on=date(2026, 1, 6)).season == Season(2025)


def test_a_ticket_prints_the_way_the_scale_house_reads_it():
    assert str(ticket()) == "ticket 1 module HW-004182 21,200 lb"


def test_tare_must_weigh_less_than_gross():
    with pytest.raises(ValidationError) as caught:
        ticket(tare=Weight(38_400))
    assert caught.value.field == "tare"


def test_a_module_that_is_too_light_is_refused():
    with pytest.raises(ValidationError):
        ticket(gross=Weight(18_000), tare=Weight(17_200))


def test_a_module_that_is_too_heavy_is_refused():
    with pytest.raises(ValidationError):
        ticket(gross=Weight(60_000), tare=Weight(17_200))


@pytest.mark.parametrize("number", [0, -3])
def test_a_ticket_has_to_be_numbered(number):
    with pytest.raises(ValidationError):
        ticket(number=number)


def test_a_ticket_number_is_not_a_bool():
    with pytest.raises(ValidationError):
        ticket(number=True)


@pytest.mark.parametrize("blank", ["", "   "])
def test_producer_and_farm_are_required(blank):
    with pytest.raises(ValidationError):
        ticket(producer=blank)
    with pytest.raises(ValidationError):
        ticket(farm=blank)


def test_a_correction_names_the_ticket_it_voids():
    corrected = ticket(number=8, voids=5)
    assert corrected.is_correction
    assert not ticket().is_correction


def test_a_correction_cannot_void_a_later_ticket():
    with pytest.raises(ValidationError):
        ticket(number=5, voids=8)


@pytest.mark.parametrize("reading", ["2.0", "9.4", "25.0"])
def test_moisture_inside_the_probe_range(reading):
    assert clean_moisture(reading) == Decimal(reading)


@pytest.mark.parametrize("reading", ["1.9", "25.1", "9.44"])
def test_moisture_outside_the_probe_range(reading):
    with pytest.raises(ValidationError):
        clean_moisture(reading)


def test_moisture_must_be_a_number():
    with pytest.raises(ValidationError):
        clean_moisture(9.4)  # type: ignore[arg-type]


def test_dry_weight_takes_water_out():
    dry = ticket(moisture=Decimal("12.5")).dry_weight()
    assert dry < ticket().net
    assert dry == Weight(20_054)


def test_dry_weight_at_the_reference_changes_nothing():
    assert ticket(moisture=Decimal("7.5")).dry_weight() == Weight(21_200)


def test_a_wetter_module_dries_down_further():
    wet = ticket(moisture=Decimal("14.0")).dry_weight()
    dryer = ticket(moisture=Decimal("8.0")).dry_weight()
    assert wet < dryer


def test_dry_weight_refuses_a_reference_off_the_scale():
    with pytest.raises(ValidationError):
        ticket().dry_weight(Decimal("40.0"))
