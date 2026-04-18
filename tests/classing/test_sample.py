from datetime import date
from decimal import Decimal

import pytest

from moteroom.classing.sample import SIDE_A, SIDE_B, Pair, Sample, cut
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season

GIN = GinCode("41207")
SEASON = Season(2025)
BALE = BaleId.build(SEASON, GIN, 1_204)
DAY = date(2025, 10, 18)


def sample(side: str = SIDE_A, **overrides: object) -> Sample:
    fields = {"bale_id": BALE, "side": side, "cut_on": DAY, "grams": 100, "cut_by": "TALLEY"}
    fields.update(overrides)
    return Sample(**fields)  # type: ignore[arg-type]


def test_a_sample_reads_back():
    assert str(sample()) == f"{BALE} side a 100g"


@pytest.mark.parametrize("side", ["", "c", "A"])
def test_a_side_nobody_cuts(side):
    with pytest.raises(ValidationError):
        sample(side=side)


@pytest.mark.parametrize("grams", [59, 201])
def test_a_cut_off_the_scale_is_refused(grams):
    with pytest.raises(ValidationError):
        sample(grams=grams)


def test_a_cut_is_whole_grams_by_somebody():
    with pytest.raises(ValidationError):
        sample(grams=True)
    with pytest.raises(ValidationError):
        sample(cut_by=" ")


def test_both_cuts_make_a_pair():
    made = cut(BALE, DAY, "TALLEY")
    assert made.bale_id == BALE
    assert made.grams == 200
    assert made.is_enough
    assert str(made).endswith("both sides, 200g")


def test_a_pair_has_to_be_off_the_same_bale_and_day():
    other = BaleId.build(SEASON, GIN, 1_205)
    with pytest.raises(ValidationError):
        Pair(sample(), sample(SIDE_B, bale_id=other))
    with pytest.raises(ValidationError):
        Pair(sample(), sample(SIDE_B, cut_on=date(2025, 10, 19)))


def test_a_pair_has_to_be_two_sides():
    with pytest.raises(ValidationError):
        Pair(sample(), sample(SIDE_A))


def test_two_sides_that_read_alike_are_uniform():
    made = cut(BALE, DAY, "TALLEY")
    assert made.uniform(Decimal("0.2"), 1)
    assert not made.uniform(Decimal("0.4"), 1)
    assert not made.uniform(Decimal("0.2"), 2)


def test_a_gap_is_a_distance_not_a_direction():
    with pytest.raises(ValidationError):
        cut(BALE, DAY, "TALLEY").uniform(Decimal("-0.1"), 1)
    with pytest.raises(ValidationError):
        cut(BALE, DAY, "TALLEY").uniform(Decimal("0.1"), -1)


def test_a_light_cut_is_not_enough_to_class_and_hold():
    made = Pair(sample(), sample(SIDE_B, grams=60))
    assert made.is_enough
    assert made.grams == 160
