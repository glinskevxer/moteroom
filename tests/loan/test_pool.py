from datetime import date
from decimal import Decimal
from typing import Any

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.ids import BaleId, GinCode, LotId
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.loan import pool
from moteroom.press.bale import Bale

GIN = GinCode("41207")
SEASON = Season(2025)
BASE = CentsPerPound.of("52.00")


def card(number: int, **overrides: Any) -> ClassingRecord:
    fields: dict[str, Any] = {
        "bale_id": BaleId.build(SEASON, GIN, number),
        "classed_on": date(2025, 10, 22),
        "office": "MEMPHIS",
        "micronaire": Micronaire(Decimal("4.0")),
        "staple": Staple(36),
        "strength": Strength(Decimal("27.0")),
        "uniformity": Uniformity(Decimal("81.0")),
        "color": ColorGrade(41),
        "leaf": LeafGrade(3),
        "trash": Trash(Decimal("0.42")),
    }
    fields.update(overrides)
    return ClassingRecord(**fields)


def bale(number: int, gross: int = 523) -> Bale:
    return Bale(
        bale_id=BaleId.build(SEASON, GIN, number),
        lot=LotId(SEASON, 42),
        pressed_on=date(2025, 10, 16),
        gross=Weight(gross),
        tare=Weight(23),
        moisture=Decimal("6.4"),
    )


def test_an_empty_pool_is_empty_rather_than_broken():
    built = pool.build([], BASE)
    assert built.bales == 0
    assert built.lint.is_zero
    assert built.value.is_zero
    assert built.average_rate == CentsPerPound.of(0)
    assert built.average_bale.is_zero


def test_a_pool_adds_the_bales_up():
    built = pool.build([(bale(1), card(1)), (bale(2, gross=573), card(2))], BASE)
    assert built.bales == 2
    assert built.lint == Weight(1_050)
    assert built.value == Money.parse("546.00")
    assert built.average_bale == Weight(525)


def test_the_average_rate_is_value_over_weight():
    built = pool.build(
        [(bale(1), card(1)), (bale(2, gross=623), card(2, staple=Staple(38)))], BASE
    )
    assert built.average_rate.cents > Decimal("52.00")
    assert built.average_rate.cents < Decimal("53.05")


def test_a_below_grade_bale_is_set_aside_with_its_reason():
    built = pool.build([(bale(1), card(1, leaf=LeafGrade(8))), (bale(2), card(2))], BASE)
    assert built.bales == 1
    assert built.ineligible[0][1] == "is below grade"


def test_a_card_for_the_wrong_bale_is_set_aside():
    built = pool.build([(bale(1), card(2))], BASE)
    assert built.bales == 0
    assert built.ineligible[0][1] == "card is for another bale"


def test_the_pool_counts_by_colour_class_and_staple():
    built = pool.build(
        [
            (bale(1), card(1)),
            (bale(2), card(2, color=ColorGrade(33), staple=Staple(34))),
            (bale(3), card(3, color=ColorGrade(31))),
        ],
        BASE,
    )
    assert built.by_color_class() == {1: 2, 3: 1}
    assert built.by_staple() == {34: 1, 36: 2}


def test_a_pool_prints_its_totals():
    built = pool.build([(bale(1), card(1))], BASE)
    assert str(built) == "1 bales, 500 lb, $260.00 at 52.00c"
