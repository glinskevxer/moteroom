from decimal import Decimal

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.core.errors import ValidationError


def test_a_code_splits_into_grade_and_class():
    white = ColorGrade(41)
    assert white.grade == 4
    assert white.color_class == 1
    assert white.is_white
    assert white.name == "strict low middling white"
    assert str(white) == "41"


def test_a_code_reads_off_a_card():
    assert ColorGrade.parse(" 31 ") == ColorGrade(31)


@pytest.mark.parametrize("text", ["", "3a", "white"])
def test_a_code_refuses_junk(text):
    with pytest.raises(ValidationError):
        ColorGrade.parse(text)


@pytest.mark.parametrize("code", [10, 100, 19, 91, 72])
def test_a_code_that_names_no_grade_is_refused(code):
    with pytest.raises(ValidationError):
        ColorGrade(code)


def test_a_code_is_not_a_bool():
    with pytest.raises(ValidationError):
        ColorGrade(True)


def test_a_bright_white_bale_reads_high():
    assert ColorGrade.from_reading(Decimal("80.2"), Decimal("8.1")) == ColorGrade(11)


def test_a_middling_white_bale():
    assert ColorGrade.from_reading(Decimal("74.0"), Decimal("8.5")) == ColorGrade(31)


def test_yellowness_moves_the_bale_out_of_white():
    assert ColorGrade.from_reading(Decimal("74.0"), Decimal("9.1")).color_class == 2
    assert ColorGrade.from_reading(Decimal("74.0"), Decimal("11.0")).color_class == 3


def test_a_dull_bale_moves_class_even_when_it_is_not_yellow():
    assert ColorGrade.from_reading(Decimal("66.0"), Decimal("8.0")).color_class == 2
    assert ColorGrade.from_reading(Decimal("60.0"), Decimal("8.0")).color_class == 3


def test_a_stained_bale_falls_all_the_way_through():
    stained = ColorGrade.from_reading(Decimal("50.0"), Decimal("16.0"))
    assert stained.color_class == 5
    assert stained.name.endswith("yellow stained")


def test_the_class_boundary_is_where_it_says_it_is():
    inside = ColorGrade.from_reading(Decimal("68.0"), Decimal("9.0"))
    outside = ColorGrade.from_reading(Decimal("67.9"), Decimal("9.0"))
    assert inside.color_class == 1
    assert outside.color_class == 2


@pytest.mark.parametrize(
    ("rd", "plus_b"),
    [("39.9", "8.0"), ("85.1", "8.0"), ("70.0", "3.9"), ("70.0", "18.1"), ("70.05", "8.0")],
)
def test_a_reading_off_the_instrument_range_is_refused(rd, plus_b):
    with pytest.raises(ValidationError):
        ColorGrade.from_reading(Decimal(rd), Decimal(plus_b))


def test_a_reading_has_to_be_a_decimal():
    with pytest.raises(ValidationError):
        ColorGrade.from_reading(70.0, Decimal("8.0"))  # type: ignore[arg-type]


def test_class_outranks_grade_when_comparing():
    assert ColorGrade(41).is_better_than(ColorGrade(31 + 1))
    assert ColorGrade(31).is_better_than(ColorGrade(41))
    assert not ColorGrade(41).is_better_than(ColorGrade(41))


def test_every_band_in_the_chart_produces_a_legal_code():
    rd = Decimal("40.0")
    while rd <= Decimal("85.0"):
        plus_b = Decimal("4.0")
        while plus_b <= Decimal("18.0"):
            ColorGrade.from_reading(rd, plus_b)
            plus_b += Decimal("0.5")
        rd += Decimal("0.5")
