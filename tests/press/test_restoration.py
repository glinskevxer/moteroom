from decimal import Decimal

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.weight import Weight
from moteroom.press.restoration import CEILING, Restoration, to_target


def test_the_fibre_does_not_change_when_water_goes_in():
    made = Restoration(Weight(500), Decimal("5.0"), Decimal("7.0"))
    assert made.fibre == Decimal("475.0")
    assert made.restored == Weight(511)
    assert made.added == Weight(11)


def test_restoring_to_the_same_moisture_adds_nothing():
    made = Restoration(Weight(500), Decimal("5.0"), Decimal("5.0"))
    assert made.added.is_zero
    assert made.gain == Decimal("0.00")


def test_moisture_cannot_be_taken_out_this_way():
    with pytest.raises(ValidationError):
        Restoration(Weight(500), Decimal("7.0"), Decimal("5.0"))


@pytest.mark.parametrize("value", ["2.9", "10.1", "5.55"])
def test_a_reading_off_the_range_is_refused(value):
    with pytest.raises(ValidationError):
        Restoration(Weight(500), Decimal(value), Decimal("7.0"))


def test_there_has_to_be_something_to_restore():
    with pytest.raises(ValidationError):
        Restoration(Weight.zero(), Decimal("5.0"), Decimal("7.0"))


def test_the_ceiling_is_where_the_plant_says_it_is():
    assert not Restoration(Weight(500), Decimal("5.0"), CEILING).over_ceiling
    assert Restoration(Weight(500), Decimal("5.0"), Decimal("7.6")).over_ceiling


def test_the_gain_is_the_water_as_a_share_of_what_went_in():
    made = Restoration(Weight(500), Decimal("5.0"), Decimal("7.0"))
    assert made.gain == Decimal("2.20")


def test_the_water_can_be_priced():
    made = Restoration(Weight(500), Decimal("5.0"), Decimal("7.0"))
    assert made.value_of_water(CentsPerPound.of("52.00")) == Money.parse("5.72")


def test_restoring_to_a_target_stops_at_the_ceiling():
    assert to_target(Weight(500), Decimal("5.0")).after == CEILING
    with pytest.raises(ValidationError):
        to_target(Weight(500), Decimal("5.0"), Decimal("8.0"))


def test_a_restoration_prints_what_it_did():
    assert (
        str(Restoration(Weight(500), Decimal("5.0"), Decimal("7.0"))) == "11 lb restored, 2.20%"
    )
    assert "over the ceiling" in str(Restoration(Weight(500), Decimal("5.0"), Decimal("8.0")))


def test_a_wetter_target_puts_more_water_in():
    dry = Restoration(Weight(500), Decimal("5.0"), Decimal("6.0"))
    wet = Restoration(Weight(500), Decimal("5.0"), Decimal("7.5"))
    assert wet.added > dry.added
