from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode, LotId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.press.bale import Bale

GIN = GinCode("41207")
LOT = LotId(Season(2025), 42)


def bale(**overrides: Any) -> Bale:
    fields: dict[str, Any] = {
        "bale_id": BaleId.build(Season(2025), GIN, 1_204),
        "lot": LOT,
        "pressed_on": date(2025, 10, 16),
        "gross": Weight(538),
        "tare": Weight(23),
        "moisture": Decimal("6.4"),
    }
    fields.update(overrides)
    return Bale(**fields)


def test_net_is_gross_less_the_bagging_and_ties():
    assert bale().net == Weight(515)
    assert bale().number == 1_204


def test_a_bale_prints_its_tag_in_groups():
    assert str(bale()).startswith("bale 5-41207-01204-")
    assert str(bale()).endswith("515 lb")


def test_a_bale_is_pressed_inside_its_lot_season():
    with pytest.raises(ValidationError) as caught:
        bale(pressed_on=date(2026, 8, 2))
    assert caught.value.field == "pressed_on"


def test_a_tag_from_another_season_is_refused():
    with pytest.raises(ValidationError):
        bale(bale_id=BaleId.build(Season(2026), GIN, 1_204))


@pytest.mark.parametrize("tare", [3, 41])
def test_the_tare_has_to_look_like_bagging_and_ties(tare):
    with pytest.raises(ValidationError):
        bale(tare=Weight(tare))


def test_the_tare_cannot_swallow_the_bale():
    with pytest.raises(ValidationError):
        bale(gross=Weight(20), tare=Weight(23))


@pytest.mark.parametrize("gross", [320, 730])
def test_a_bale_off_the_press_has_to_weigh_like_one(gross):
    with pytest.raises(ValidationError):
        bale(gross=Weight(gross))


@pytest.mark.parametrize("moisture", ["2.9", "10.1", "6.44"])
def test_bale_moisture_stays_inside_the_probe_range(moisture):
    with pytest.raises(ValidationError):
        bale(moisture=Decimal(moisture))


def test_a_light_bale_is_flagged_for_the_warehouse():
    assert bale(gross=Weight(420), tare=Weight(23)).is_light
    assert not bale().is_light


def test_a_heavy_bale_is_flagged_too():
    assert bale(gross=Weight(650), tare=Weight(23)).is_heavy
    assert not bale().is_heavy


def test_the_flags_are_off_on_an_ordinary_bale():
    assert not bale().is_light
    assert not bale().is_heavy
