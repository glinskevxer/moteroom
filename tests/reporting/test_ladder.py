from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.reporting.ladder import band_ladder, grade_ladder, leaf_ladder, money_moved

GIN = GinCode("41207")
SEASON = Season(2025)


def card(number: int, **overrides: Any) -> ClassingRecord:
    fields: dict[str, Any] = {
        "bale_id": BaleId.build(SEASON, GIN, number),
        "classed_on": date(2025, 10, 22),
        "office": "MEMPHIS",
        "micronaire": Micronaire(Decimal("4.0")),
        "staple": Staple(36),
        "strength": Strength(Decimal("28.0")),
        "uniformity": Uniformity(Decimal("81.0")),
        "color": ColorGrade(41),
        "leaf": LeafGrade(3),
        "trash": Trash(Decimal("0.42")),
    }
    fields.update(overrides)
    return ClassingRecord(**fields)


def test_money_moved_prices_a_rung():
    assert money_moved(Decimal("1.05"), Weight(1_000)) == Money.parse("10.50")
    assert money_moved(Decimal("-2.25"), Weight(1_000)) == Money.parse("-22.50")
    assert money_moved(Decimal("1.05"), Weight.zero()).is_zero


def test_a_band_ladder_counts_the_bales_onto_the_rungs():
    made = band_ladder("micronaire", [card(1), card(2)], Weight(1_000))
    rungs = dict(zip(made.column("band"), made.column("bales"), strict=True))
    assert rungs["3.7 to 4.2"] == "2"
    assert rungs["2.0 to 2.6"] == "0"
    assert "2 cards" in made.notes[0]


def test_a_rung_with_bales_on_it_shows_what_it_moved():
    made = band_ladder("staple", [card(1, staple=Staple(38))], Weight(500))
    moved = dict(zip(made.column("band"), made.column("moved"), strict=True))
    assert moved["38 to 38"] == "$5.25"
    assert moved["36 to 36"] == "$0.00"


def test_a_ladder_nobody_has():
    with pytest.raises(KeyError):
        band_ladder("colour", [], Weight.zero())


def test_an_empty_season_still_prints_every_rung():
    made = band_ladder("micronaire", [], Weight.zero())
    assert not made.is_empty
    assert set(made.column("bales")) == {"0"}
    assert set(made.column("percent")) == {"0.00"}


def test_the_colour_ladder_runs_best_first():
    made = grade_ladder([card(1), card(2, color=ColorGrade(31))], Weight(1_000))
    assert made.column("code")[0] == "11"
    assert made.column("cents")[0].startswith("+")
    counted = dict(zip(made.column("code"), made.column("bales"), strict=True))
    assert counted["41"] == "1"
    assert counted["31"] == "1"
    assert "2 of 20 codes used" in made.notes[0]


def test_the_leaf_ladder_only_falls():
    made = leaf_ladder([card(1), card(2, leaf=LeafGrade(5))], Weight(1_000))
    cents = [Decimal(value) for value in made.column("cents")]
    assert cents == sorted(cents, reverse=True)
    counted = dict(zip(made.column("grade"), made.column("bales"), strict=True))
    assert counted["3"] == "1"
    assert counted["5"] == "1"


def test_a_worse_leaf_moves_money_the_wrong_way():
    made = leaf_ladder([card(1, leaf=LeafGrade(6))], Weight(500))
    moved = dict(zip(made.column("grade"), made.column("moved"), strict=True))
    assert moved["6"] == "-$13.25"


def test_an_empty_colour_and_leaf_ladder():
    assert grade_ladder([], Weight.zero()).column("bales")[0] == "0"
    assert leaf_ladder([], Weight.zero()).column("bales")[0] == "0"
