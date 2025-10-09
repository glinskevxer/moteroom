from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.settlement.contract import (
    Contract,
    delivered_price,
    fill_of,
    grade_adjustment,
)

GIN = GinCode("41207")
SEASON = Season(2025)


def contract(**overrides: Any) -> Contract:
    fields: dict[str, Any] = {
        "number": "C000141",
        "buyer": "CALCOT",
        "signed_on": date(2025, 6, 2),
        "bales": 400,
        "delivery_from": date(2025, 11, 1),
        "delivery_to": date(2026, 1, 31),
        "price": CentsPerPound.of("68.50"),
    }
    fields.update(overrides)
    return Contract(**fields)


def card(**overrides: Any) -> ClassingRecord:
    fields: dict[str, Any] = {
        "bale_id": BaleId.build(SEASON, GIN, 1),
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


def test_a_flat_contract_knows_its_price():
    made = contract()
    assert not made.is_basis
    assert made.price_against() == CentsPerPound.of("68.50")
    assert made.value(Weight(500)) == Money.parse("342.50")


def test_a_basis_contract_has_no_price_until_futures_are_put_against_it():
    made = contract(price=None, basis=CentsPerPound.of("-3.25"))
    assert made.is_basis
    with pytest.raises(ValidationError):
        made.price_against()
    assert made.price_against(CentsPerPound.of("71.00")) == CentsPerPound.of("67.75")


def test_a_contract_is_priced_one_way_or_the_other():
    with pytest.raises(ValidationError):
        contract(basis=CentsPerPound.of("-3.25"))
    with pytest.raises(ValidationError):
        contract(price=None)


@pytest.mark.parametrize("number", ["", "C12345", "c000141", "C0001411"])
def test_a_contract_number_has_a_shape(number):
    with pytest.raises(ValidationError):
        contract(number=number)


def test_a_contract_names_a_buyer():
    with pytest.raises(ValidationError):
        contract(buyer="  ")


@pytest.mark.parametrize("bales", [0, 50_001])
def test_a_contract_quantity_has_bounds(bales):
    with pytest.raises(ValidationError):
        contract(bales=bales)


def test_a_contract_quantity_is_not_a_bool():
    with pytest.raises(ValidationError):
        contract(bales=True)


def test_the_window_has_to_run_forwards():
    with pytest.raises(ValidationError):
        contract(delivery_to=date(2025, 10, 1))


def test_the_window_cannot_open_before_the_contract():
    with pytest.raises(ValidationError):
        contract(delivery_from=date(2025, 5, 1))


def test_the_window_covers_both_of_its_ends():
    made = contract()
    assert made.covers(date(2025, 11, 1))
    assert made.covers(date(2026, 1, 31))
    assert not made.covers(date(2026, 2, 1))
    assert made.window_days == 92


def test_a_base_grade_bale_is_paid_the_contract_price():
    assert grade_adjustment(card()) == Decimal("0.00")
    assert delivered_price(contract(), card()) == CentsPerPound.of("68.50")


def test_a_better_bale_is_paid_more_and_a_worse_one_less():
    better = delivered_price(contract(), card(color=ColorGrade(21), staple=Staple(38)))
    worse = delivered_price(contract(), card(color=ColorGrade(53), leaf=LeafGrade(5)))
    assert better > CentsPerPound.of("68.50")
    assert worse < CentsPerPound.of("68.50")


def test_extraneous_matter_comes_off_the_contract_price_too():
    barky = delivered_price(contract(), card(extraneous=(Extraneous.parse("B2"),)))
    assert barky == CentsPerPound.of("66.25")


def test_a_delivered_price_never_goes_below_nothing():
    thin = contract(price=CentsPerPound.of("1.00"))
    assert delivered_price(thin, card(color=ColorGrade(65), staple=Staple(26))) == (
        CentsPerPound.of("0.00")
    )


def test_a_basis_contract_prices_a_delivery_off_the_futures():
    made = contract(price=None, basis=CentsPerPound.of("-3.25"))
    assert delivered_price(made, card(), CentsPerPound.of("71.00")) == CentsPerPound.of("67.75")


def test_a_fill_counts_what_is_left():
    made = fill_of(contract(), [100, 150])
    assert made.delivered == 250
    assert made.remaining == 150
    assert not made.is_complete
    assert str(made) == "contract C000141 short 150"


def test_a_filled_contract_says_so():
    assert fill_of(contract(), [400]).is_complete
    assert str(fill_of(contract(), [400])) == "contract C000141 filled"


def test_delivering_more_than_promised_is_counted():
    made = fill_of(contract(), [400, 20])
    assert made.over == 20
    assert made.remaining == 0
    assert "20 over" in str(made)


def test_a_negative_delivery_is_refused():
    with pytest.raises(ValidationError):
        fill_of(contract(), [-1])


def test_a_contract_prints_which_kind_it_is():
    assert "flat 68.50c" in str(contract())
    assert "basis -3.25c" in str(contract(price=None, basis=CentsPerPound.of("-3.25")))
