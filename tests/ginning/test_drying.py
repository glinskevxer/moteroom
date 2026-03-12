from decimal import Decimal

import pytest

from moteroom.core.errors import ValidationError
from moteroom.ginning.drying import (
    DAMAGE_LINE,
    MAX_TEMPERATURE,
    SETTINGS,
    Setting,
    recommended,
    settings_for,
)


def test_wetter_cotton_calls_for_more_heat():
    assert recommended(Decimal("6.0")) == 140
    assert recommended(Decimal("12.0")) == 280
    assert recommended(Decimal("6.0")) < recommended(Decimal("12.0"))


def test_every_moisture_the_probe_reports_has_a_setting():
    reading = Decimal("2.0")
    while reading <= Decimal("25.0"):
        assert recommended(reading) <= MAX_TEMPERATURE
        reading += Decimal("0.1")


def test_the_bands_run_up_and_leave_no_gap():
    for earlier, later in zip(SETTINGS, SETTINGS[1:], strict=False):
        assert later[0] - earlier[1] == Decimal("0.1")
        assert later[2] > earlier[2]


def test_a_moisture_off_the_probe_has_no_setting():
    with pytest.raises(ValidationError):
        recommended(Decimal("30.0"))


def test_a_sound_setting_says_so():
    made = Setting(Decimal("12.0"), 280, 220)
    assert made.is_sound
    assert made.warnings() == ()
    assert str(made).endswith("is sound")


def test_a_stage_at_the_damage_line_is_caught():
    made = Setting(Decimal("18.0"), DAMAGE_LINE, 300)
    assert made.over_the_damage_line
    assert "damage line" in made.warnings()[0]


def test_a_trim_stage_running_hot_is_caught():
    made = Setting(Decimal("12.0"), 280, 270)
    assert made.second_runs_hotter
    assert not made.is_sound
    assert "trim stage" in str(made)


def test_a_setting_colder_than_the_cotton_calls_for():
    made = Setting(Decimal("16.0"), 180, 140)
    assert made.under_set
    assert "colder" in made.warnings()[0]


def test_a_setting_hotter_than_the_cotton_calls_for():
    made = Setting(Decimal("6.0"), 300, 200)
    assert made.over_set
    assert any("hotter" in warning for warning in made.warnings())


def test_a_setting_inside_the_margin_is_not_complained_about():
    assert Setting(Decimal("12.0"), 290, 230).is_sound
    assert Setting(Decimal("12.0"), 270, 210).is_sound


@pytest.mark.parametrize("temperature", [119, 351])
def test_a_temperature_off_the_dial_is_refused(temperature):
    with pytest.raises(ValidationError):
        Setting(Decimal("12.0"), temperature, 200)
    with pytest.raises(ValidationError):
        Setting(Decimal("12.0"), 280, temperature)


def test_a_temperature_is_whole_degrees():
    with pytest.raises(ValidationError):
        Setting(Decimal("12.0"), True, 200)


def test_the_plant_setting_for_a_moisture_is_sound_at_every_reading():
    reading = Decimal("2.0")
    while reading <= Decimal("25.0"):
        made = settings_for(reading)
        assert made.first == recommended(reading)
        assert made.second < made.first
        assert not made.under_set
        assert not made.over_set
        reading += Decimal("0.5")


def test_the_hottest_plant_setting_stays_off_the_damage_line():
    assert not settings_for(Decimal("25.0")).over_the_damage_line
