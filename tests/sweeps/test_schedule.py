"""The schedule swept against the instruments that feed it.

Two tables written in two modules have to agree on every value that can pass
between them. The colour chart can only produce codes the schedule prices, the
instrument ranges have to be inside the bands, and the ladders have to run the
way the trade says they run. None of that is visible in either module on its
own, and all of it is the kind of thing that breaks when somebody edits one
table and not the other.
"""

from decimal import Decimal

import pytest

from moteroom.classing.color import CLASS_NAMES, GRADE_BANDS, ColorGrade
from moteroom.classing.defect import BELOW_GRADE_LEAF, LEAF_NAMES
from moteroom.classing.measure import (
    MAX_MIKE,
    MAX_STAPLE,
    MAX_STRENGTH,
    MAX_UNIFORMITY,
    MIN_MIKE,
    MIN_STAPLE,
    MIN_STRENGTH,
    MIN_UNIFORMITY,
)
from moteroom.core.errors import ValidationError
from moteroom.loan.schedule import (
    COLOR_POINTS,
    EXTRANEOUS_POINTS,
    LEAF_POINTS,
    MICRONAIRE,
    STAPLE,
    STRENGTH,
    UNIFORMITY,
    extraneous_points,
    leaf_points,
)


def steps(low: Decimal, high: Decimal, step: str = "0.1") -> list[Decimal]:
    made = []
    value = low
    while value <= high:
        made.append(value)
        value += Decimal(step)
    return made


def test_every_colour_the_chart_can_produce_is_priced():
    for rd in steps(Decimal("40.0"), Decimal("85.0"), "0.5"):
        for plus_b in steps(Decimal("4.0"), Decimal("18.0"), "0.5"):
            code = ColorGrade.from_reading(rd, plus_b).code
            assert code in COLOR_POINTS, f"{rd}/{plus_b} makes {code} and nothing prices it"


def test_every_code_the_chart_lays_out_is_priced():
    for color_class, bands in GRADE_BANDS.items():
        for grade, _ in bands:
            assert grade * 10 + color_class in COLOR_POINTS


def test_every_priced_colour_is_a_code_the_chart_could_make():
    for code in COLOR_POINTS:
        made = ColorGrade(code)
        assert made.color_class in CLASS_NAMES
        assert made.grade in {digit for digit, _ in GRADE_BANDS[made.color_class]}


def test_every_leaf_grade_but_below_grade_is_priced():
    for grade in LEAF_NAMES:
        if grade == BELOW_GRADE_LEAF:
            with pytest.raises(ValidationError):
                leaf_points(grade)
        else:
            assert leaf_points(grade) == LEAF_POINTS[grade]


def test_every_mike_the_instrument_reports_falls_in_a_band():
    for value in steps(MIN_MIKE, MAX_MIKE):
        assert MICRONAIRE.covers(value), f"mike {value} is off the schedule"


def test_every_staple_the_instrument_reports_falls_in_a_band():
    for value in range(MIN_STAPLE, MAX_STAPLE + 1):
        assert STAPLE.covers(Decimal(value)), f"staple {value} is off the schedule"


def test_every_strength_and_uniformity_falls_in_a_band():
    for value in steps(MIN_STRENGTH, MAX_STRENGTH):
        assert STRENGTH.covers(value)
    for value in steps(MIN_UNIFORMITY, MAX_UNIFORMITY):
        assert UNIFORMITY.covers(value)


def test_the_colour_ladder_falls_as_the_grade_falls():
    for color_class, bands in GRADE_BANDS.items():
        grades = [grade for grade, _ in bands]
        points = [COLOR_POINTS[grade * 10 + color_class] for grade in sorted(grades)]
        assert points == sorted(points, reverse=True), f"class {color_class} does not fall"


def test_white_is_never_worth_less_than_the_same_grade_spotted():
    for grade in range(1, 8):
        white = COLOR_POINTS.get(grade * 10 + 1)
        spotted = COLOR_POINTS.get(grade * 10 + 3)
        if white is not None and spotted is not None:
            assert white > spotted


def test_the_staple_ladder_only_rises():
    points = [band.points for band in STAPLE.bands]
    assert points == sorted(points)


def test_heavy_extraneous_matter_always_costs_more_than_light():
    for code, points in EXTRANEOUS_POINTS.items():
        if code.endswith("2"):
            assert points < EXTRANEOUS_POINTS[code[0] + "1"]
        assert extraneous_points(code) == points


def test_no_band_in_any_table_overlaps_its_neighbour():
    for table in (MICRONAIRE, STAPLE, STRENGTH, UNIFORMITY):
        for earlier, later in zip(table.bands, table.bands[1:], strict=False):
            assert earlier.high < later.low, f"{table.name} overlaps at {later.low}"


def test_no_band_in_any_table_leaves_a_gap():
    for table, step in (
        (MICRONAIRE, "0.1"),
        (STAPLE, "1"),
        (STRENGTH, "0.1"),
        (UNIFORMITY, "0.1"),
    ):
        for earlier, later in zip(table.bands, table.bands[1:], strict=False):
            assert later.low - earlier.high == Decimal(step), f"{table.name} has a gap"
