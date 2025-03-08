from decimal import Decimal

import pytest

from moteroom.core.errors import ValidationError
from moteroom.loan.schedule import (
    BASE_COLOR,
    BASE_LEAF,
    BASE_STAPLE,
    MICRONAIRE,
    STAPLE,
    STRENGTH,
    UNIFORMITY,
    Band,
    BandTable,
    color_points,
    extraneous_points,
    leaf_points,
)


def test_a_band_holds_both_of_its_ends():
    band = Band(Decimal("3.7"), Decimal("4.2"), Decimal("0.00"))
    assert band.holds(Decimal("3.7"))
    assert band.holds(Decimal("4.2"))
    assert not band.holds(Decimal("4.3"))


def test_a_band_that_runs_backwards_is_refused():
    with pytest.raises(ValidationError):
        Band(Decimal("4.2"), Decimal("3.7"), Decimal("0.00"))


def test_a_band_finer_than_a_hundredth_is_refused():
    with pytest.raises(ValidationError):
        Band(Decimal("3.7"), Decimal("4.2"), Decimal("0.005"))


def test_a_table_needs_bands():
    with pytest.raises(ValidationError):
        BandTable("empty", [])


def test_a_table_refuses_overlapping_bands():
    with pytest.raises(ValidationError):
        BandTable("mike", [("2.0", "3.0", "0.00"), ("2.9", "4.0", "0.00")])


def test_the_base_grade_costs_nothing():
    assert color_points(BASE_COLOR) == Decimal("0.00")
    assert leaf_points(BASE_LEAF) == Decimal("0.00")
    assert STAPLE.lookup(Decimal(BASE_STAPLE)) == Decimal("0.00")


def test_the_premium_mike_range_costs_nothing_and_both_sides_do():
    assert MICRONAIRE.lookup(Decimal("3.7")) == Decimal("0.00")
    assert MICRONAIRE.lookup(Decimal("4.2")) == Decimal("0.00")
    assert MICRONAIRE.lookup(Decimal("3.6")) == Decimal("-0.35")
    assert MICRONAIRE.lookup(Decimal("4.3")) == Decimal("-0.15")


def test_low_mike_is_discounted_hardest():
    assert MICRONAIRE.lookup(Decimal("2.5")) < MICRONAIRE.lookup(Decimal("5.5"))


def test_long_staple_pays_a_premium_and_short_staple_does_not():
    assert STAPLE.lookup(Decimal(38)) > Decimal("0.00")
    assert STAPLE.lookup(Decimal(30)) < Decimal("0.00")


def test_strength_and_uniformity_run_the_right_way():
    assert STRENGTH.lookup(Decimal("31.0")) > STRENGTH.lookup(Decimal("20.0"))
    assert UNIFORMITY.lookup(Decimal("86.0")) > UNIFORMITY.lookup(Decimal("71.0"))


@pytest.mark.parametrize("table", [MICRONAIRE, STAPLE, STRENGTH, UNIFORMITY])
def test_every_table_covers_its_own_range_with_no_gaps(table):
    step = Decimal("1") if table.name == "staple" else Decimal("0.1")
    value = table.low
    while value <= table.high:
        assert table.covers(value), f"{table.name} has a gap at {value}"
        value += step


@pytest.mark.parametrize("table", [MICRONAIRE, STAPLE, STRENGTH, UNIFORMITY])
def test_a_reading_off_the_end_of_a_table_is_refused(table):
    with pytest.raises(ValidationError):
        table.lookup(table.high + Decimal("1"))
    with pytest.raises(ValidationError):
        table.lookup(table.low - Decimal("1"))


def test_white_is_worth_more_than_spotted_at_the_same_grade():
    assert color_points(31) > color_points(33)
    assert color_points(41) > color_points(43)


def test_the_leaf_ladder_only_falls():
    grades = [leaf_points(grade) for grade in range(1, 8)]
    assert grades == sorted(grades, reverse=True)


def test_below_grade_leaf_is_not_priced():
    with pytest.raises(ValidationError):
        leaf_points(8)


def test_a_colour_code_the_schedule_does_not_price():
    with pytest.raises(ValidationError):
        color_points(72)


def test_extraneous_matter_is_priced_by_code():
    assert extraneous_points("B2") < extraneous_points("B1")
    assert extraneous_points("P2") < Decimal("-4.00")


def test_an_extraneous_code_nobody_priced():
    with pytest.raises(ValidationError):
        extraneous_points("Z9")


def test_every_table_has_its_bands_counted():
    assert len(MICRONAIRE) == 9
    assert len(STAPLE) == 9
