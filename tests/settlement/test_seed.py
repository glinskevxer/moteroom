from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.core.weight import Weight
from moteroom.settlement.seed import SeedTerms, credit, tons


def terms(**overrides: Any) -> SeedTerms:
    fields: dict[str, Any] = {
        "price_per_ton": Money.parse("205.00"),
        "gin_shares": 1,
        "producer_shares": 3,
        "hauling_per_ton": Money.parse("12.50"),
    }
    fields.update(overrides)
    return SeedTerms(**fields)


def test_seed_is_invoiced_in_tons_to_three_places():
    assert tons(Weight(2_000)) == Decimal("1.000")
    assert tons(Weight(35_400)) == Decimal("17.700")
    assert tons(Weight(2)) == Decimal("0.001")


@pytest.mark.parametrize("field", ["price_per_ton", "hauling_per_ton"])
def test_a_negative_rate_is_refused(field):
    with pytest.raises(ValidationError):
        terms(**{field: Money.parse("-0.01")})


def test_a_negative_share_is_refused():
    with pytest.raises(ValidationError):
        terms(gin_shares=-1)


def test_shares_cannot_both_be_zero():
    with pytest.raises(ValidationError):
        terms(gin_shares=0, producer_shares=0)


def test_the_gross_is_the_price_on_the_tons():
    found = credit(Weight(35_400), terms())
    assert found.gross == Money.parse("3628.50")


def test_the_gin_keeps_its_share():
    found = credit(Weight(35_400), terms())
    assert found.gin_share == Money.parse("907.13")
    assert found.producer_share == Money.parse("2721.37")


def test_hauling_comes_off_the_producer_side():
    found = credit(Weight(35_400), terms())
    assert found.hauling == Money.parse("221.25")
    assert found.net == Money.parse("2500.12")


def test_the_lines_add_back_to_the_credit():
    found = credit(Weight(35_400), terms())
    named = dict(found.lines())
    assert named["seed value"] + named["gin share"] + named["hauling"] == named["seed credit"]


def test_a_gin_that_keeps_nothing():
    found = credit(Weight(35_400), terms(gin_shares=0, hauling_per_ton=Money.zero()))
    assert found.gin_share.is_zero
    assert found.net == found.gross


def test_a_gin_that_keeps_all_of_it():
    found = credit(Weight(35_400), terms(producer_shares=0, hauling_per_ton=Money.zero()))
    assert found.gin_share == found.gross
    assert found.net.is_zero


def test_no_seed_credits_nothing():
    found = credit(Weight.zero(), terms())
    assert found.gross.is_zero
    assert found.net.is_zero


def test_a_credit_prints_its_line():
    assert str(credit(Weight(35_400), terms())) == "35,400 lb of seed, credit $2,500.12"
