from datetime import date
from decimal import Decimal
from typing import Any

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.reading import share
from moteroom.core.season import Season
from moteroom.reporting.quality import (
    averages,
    class_distribution,
    colour_distribution,
    findings_report,
    leaf_distribution,
    staple_distribution,
)

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


def test_share_is_a_percentage_to_a_hundredth():
    assert share(1, 3) == Decimal("33.33")
    assert share(0, 0) == Decimal("0.00")
    assert share(1, 0) == Decimal("0.00")


def test_colour_counts_by_code():
    made = colour_distribution([card(1), card(2), card(3, color=ColorGrade(31))])
    assert made.column("code") == ["31", "41"]
    assert made.column("bales") == ["1", "2"]
    assert made.column("percent") == ["33.33", "66.67"]


def test_colour_counts_by_class_as_well():
    made = class_distribution([card(1), card(2, color=ColorGrade(33))])
    assert made.column("class") == ["spotted", "white"]


def test_leaf_and_staple_count_the_same_way():
    cards = [card(1), card(2, leaf=LeafGrade(4), staple=Staple(34))]
    assert leaf_distribution(cards).column("grade") == ["3", "4"]
    assert staple_distribution(cards).column("staple") == ["34", "36"]


def test_an_empty_distribution_is_empty_rather_than_broken():
    made = colour_distribution([])
    assert made.is_empty
    assert made.notes == ("0 cards",)


def test_findings_count_by_code_and_name_the_gin_faults():
    cards = [
        card(1, extraneous=(Extraneous.parse("B2"),)),
        card(2, extraneous=(Extraneous.parse("B2"), Extraneous.parse("P1"))),
        card(3),
    ]
    made = findings_report(cards)
    assert made.column("code") == ["B2", "P1"]
    assert made.column("bales") == ["2", "1"]
    assert "1 carry" in made.notes[1]


def test_findings_on_a_clean_season():
    made = findings_report([card(1), card(2)])
    assert made.is_empty
    assert "0 carry" in made.notes[1]


def test_the_averages_read_off_the_cards():
    cards = [card(1), card(2, micronaire=Micronaire(Decimal("4.4")), staple=Staple(38))]
    made = averages(cards)
    named = dict(zip(made.column("measure"), made.column("value"), strict=True))
    assert named["micronaire"] == "4.20"
    assert named["staple"] == "37.00"
    assert named["white"] == "100.00%"


def test_the_averages_count_bark_separately():
    cards = [card(1, extraneous=(Extraneous.parse("B1"),)), card(2)]
    named = dict(
        zip(averages(cards).column("measure"), averages(cards).column("value"), strict=True)
    )
    assert named["bark"] == "50.00%"


def test_averages_with_no_cards_say_so():
    made = averages([])
    assert made.is_empty
    assert made.notes == ("no cards back yet",)
