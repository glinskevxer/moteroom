from decimal import Decimal

import pytest

from moteroom.classing.measure import (
    Micronaire,
    Staple,
    Strength,
    Trash,
    Uniformity,
)
from moteroom.core.errors import ValidationError


def test_mike_reads_to_a_tenth():
    assert str(Micronaire.parse(" 4.3 ")) == "4.3"


@pytest.mark.parametrize("reading", ["1.9", "7.0", "4.35"])
def test_mike_outside_what_the_instrument_reports(reading):
    with pytest.raises(ValidationError):
        Micronaire(Decimal(reading))


def test_mike_must_be_a_number():
    with pytest.raises(ValidationError):
        Micronaire(4.3)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("reading", "premium"), [("3.6", False), ("3.7", True), ("4.2", True), ("4.3", False)]
)
def test_the_premium_mike_range_has_two_edges(reading, premium):
    assert Micronaire(Decimal(reading)).is_premium is premium


def test_a_low_mike_is_the_one_that_discounts_hardest():
    assert Micronaire(Decimal("3.4")).is_low
    assert not Micronaire(Decimal("4.8")).is_low


def test_mike_sorts():
    assert Micronaire(Decimal("3.4")) < Micronaire(Decimal("4.8"))


def test_staple_is_thirty_seconds_of_an_inch():
    assert str(Staple(36)) == "36"
    assert Staple(36).inches == Decimal("1.13")
    assert Staple(32).inches == Decimal("1.00")


@pytest.mark.parametrize("length", ["1.13", "1.125"])
def test_staple_comes_off_the_instrument_length(length):
    if length == "1.125":
        with pytest.raises(ValidationError):
            Staple.from_inches(Decimal(length))
    else:
        assert Staple.from_inches(Decimal(length)) == Staple(36)


def test_staple_rounds_half_up_off_the_chart():
    assert Staple.from_inches(Decimal("1.11")) == Staple(36)
    assert Staple.from_inches(Decimal("1.09")) == Staple(35)


@pytest.mark.parametrize("value", [23, 46])
def test_staple_off_the_chart_is_refused(value):
    with pytest.raises(ValidationError):
        Staple(value)


def test_staple_is_not_a_bool_or_a_decimal():
    with pytest.raises(ValidationError):
        Staple(True)
    with pytest.raises(ValidationError):
        Staple(Decimal("36"))  # type: ignore[arg-type]


def test_strength_reads_to_a_tenth():
    assert str(Strength(Decimal("29.4"))) == "29.4"


@pytest.mark.parametrize("value", ["14.9", "40.1", "29.44"])
def test_strength_outside_the_instrument_range(value):
    with pytest.raises(ValidationError):
        Strength(Decimal(value))


def test_uniformity_reads_to_a_tenth():
    assert str(Uniformity(Decimal("81.2"))) == "81.2"


@pytest.mark.parametrize("value", ["69.9", "90.1", "81.22"])
def test_uniformity_outside_the_instrument_range(value):
    with pytest.raises(ValidationError):
        Uniformity(Decimal(value))


def test_trash_reads_to_a_hundredth():
    assert str(Trash(Decimal("0.42"))) == "0.42"


@pytest.mark.parametrize("value", ["-0.01", "10.00", "0.425"])
def test_trash_outside_the_instrument_range(value):
    with pytest.raises(ValidationError):
        Trash(Decimal(value))


def test_readings_accept_text_off_a_card():
    assert Strength("29.4") == Strength(Decimal("29.4"))  # type: ignore[arg-type]
    assert Uniformity("81.2") == Uniformity(Decimal("81.2"))  # type: ignore[arg-type]
    assert Trash("0.42") == Trash(Decimal("0.42"))  # type: ignore[arg-type]
