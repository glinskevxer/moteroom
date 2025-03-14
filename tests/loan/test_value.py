from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.ids import BaleId, GinCode, LotId
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.loan.value import IneligibleError, rate_for, value_for, value_on
from moteroom.press.bale import Bale

GIN = GinCode("41207")
SEASON = Season(2025)
BALE_ID = BaleId.build(SEASON, GIN, 1_204)
BASE = CentsPerPound.of("52.00")


def card(**overrides: Any) -> ClassingRecord:
    fields: dict[str, Any] = {
        "bale_id": BALE_ID,
        "classed_on": date(2025, 10, 22),
        "office": "MEMPHIS",
        "micronaire": Micronaire(Decimal("4.3")),
        "staple": Staple(36),
        "strength": Strength(Decimal("29.4")),
        "uniformity": Uniformity(Decimal("81.2")),
        "color": ColorGrade(41),
        "leaf": LeafGrade(3),
        "trash": Trash(Decimal("0.42")),
    }
    fields.update(overrides)
    return ClassingRecord(**fields)


def bale(**overrides: Any) -> Bale:
    fields: dict[str, Any] = {
        "bale_id": BALE_ID,
        "lot": LotId(SEASON, 42),
        "pressed_on": date(2025, 10, 16),
        "gross": Weight(523),
        "tare": Weight(23),
        "moisture": Decimal("6.4"),
    }
    fields.update(overrides)
    return Bale(**fields)


def test_the_base_grade_prices_at_the_base_rate_plus_what_it_earns():
    breakdown = rate_for(card(), BASE)
    assert breakdown.color == Decimal("0.00")
    assert breakdown.leaf == Decimal("0.00")
    assert breakdown.staple == Decimal("0.00")
    assert breakdown.micronaire == Decimal("-0.15")
    assert breakdown.strength == Decimal("0.35")
    assert breakdown.uniformity == Decimal("0.00")
    assert breakdown.adjustments == Decimal("0.20")
    assert breakdown.rate == CentsPerPound.of("52.20")


def test_a_better_bale_prices_higher():
    better = rate_for(card(color=ColorGrade(21), staple=Staple(38)), BASE)
    assert better.rate > rate_for(card(), BASE).rate


def test_extraneous_matter_comes_straight_off():
    with_bark = rate_for(card(extraneous=(Extraneous.parse("B2"),)), BASE)
    assert with_bark.extraneous == Decimal("-2.25")
    assert with_bark.rate == CentsPerPound.of("49.95")


def test_two_findings_both_come_off():
    both = rate_for(card(extraneous=(Extraneous.parse("B1"), Extraneous.parse("G1"))), BASE)
    assert both.extraneous == Decimal("-1.35")


def test_a_below_grade_bale_is_not_priced_at_all():
    with pytest.raises(IneligibleError) as caught:
        rate_for(card(leaf=LeafGrade(8)), BASE)
    assert "below grade" in caught.value.reason


def test_the_rate_never_goes_below_nothing():
    thin = CentsPerPound.of("2.00")
    breakdown = rate_for(card(color=ColorGrade(65), staple=Staple(26)), thin)
    assert breakdown.rate == CentsPerPound.of("0.00")
    assert breakdown.is_floored


def test_an_ordinary_bale_is_not_floored():
    assert not rate_for(card(), BASE).is_floored


def test_the_breakdown_prints_every_line_in_order():
    lines = rate_for(card(), BASE).lines()
    assert [name for name, _ in lines] == [
        "base",
        "color",
        "leaf",
        "staple",
        "micronaire",
        "strength",
        "uniformity",
        "extraneous",
        "rate",
    ]
    assert str(rate_for(card(), BASE)).endswith("52.20c")


def test_the_value_is_the_rate_on_the_net_weight():
    assert value_for(bale(), card(), BASE) == Money.parse("261.00")


def test_a_heavier_bale_is_worth_more_at_the_same_rate():
    heavy = value_for(bale(gross=Weight(573)), card(), BASE)
    assert heavy > value_for(bale(), card(), BASE)


def test_a_card_for_another_bale_is_refused():
    other = BaleId.build(SEASON, GIN, 1_205)
    with pytest.raises(IneligibleError):
        value_for(bale(), card(bale_id=other), BASE)


def test_a_share_of_the_lint_prices_at_the_same_rate():
    assert value_on(Weight(500), card(), BASE) == Money.parse("261.00")
    assert value_on(Weight(250), card(), BASE) == Money.parse("130.50")
