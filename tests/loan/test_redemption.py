from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.weight import Weight
from moteroom.loan.redemption import Redemption, interest_on


def redemption(**overrides: Any) -> Redemption:
    fields: dict[str, Any] = {
        "bale_id": "541207012049",
        "net": Weight(500),
        "loan_rate": CentsPerPound.of("52.00"),
        "world_price": CentsPerPound.of("58.00"),
        "days": 90,
        "annual_rate": Decimal("6.25"),
    }
    fields.update(overrides)
    return Redemption(**fields)


def test_interest_is_simple_and_on_a_365_day_year():
    assert interest_on(Money.parse("1000.00"), Decimal("6.25"), 365) == Money.parse("62.50")
    assert interest_on(Money.parse("1000.00"), Decimal("6.25"), 0).is_zero


def test_interest_refuses_a_negative_or_absurd_rate():
    with pytest.raises(ValidationError):
        interest_on(Money.parse("100.00"), Decimal("-1"), 30)
    with pytest.raises(ValidationError):
        interest_on(Money.parse("100.00"), Decimal("30"), 30)
    with pytest.raises(ValidationError):
        interest_on(Money.parse("100.00"), Decimal("6.25"), -1)


def test_the_loan_value_is_the_rate_on_the_bale():
    assert redemption().loan_value == Money.parse("260.00")


def test_a_price_above_the_loan_repays_the_loan_with_interest():
    made = redemption()
    assert not made.below_loan
    assert made.repayment == Money.parse("260.00")
    assert made.market_gain.is_zero
    assert made.interest == Money.parse("4.01")
    assert made.due == Money.parse("264.01")


def test_a_price_below_the_loan_repays_at_the_price_and_owes_no_interest():
    made = redemption(world_price=CentsPerPound.of("46.00"))
    assert made.below_loan
    assert made.repayment == Money.parse("230.00")
    assert made.market_gain == Money.parse("30.00")
    assert made.interest.is_zero
    assert made.due == Money.parse("230.00")


def test_a_price_exactly_at_the_loan_rate_is_not_below_it():
    made = redemption(world_price=CentsPerPound.of("52.00"))
    assert not made.below_loan
    assert made.market_gain.is_zero
    assert made.interest > Money.zero()


def test_the_lines_add_the_way_the_statement_reads():
    named = dict(redemption(world_price=CentsPerPound.of("46.00")).lines())
    assert named["loan value"] - named["market gain"] == named["repayment"]
    assert named["repayment"] + named["interest"] == named["due"]


def test_a_longer_loan_costs_more_interest():
    assert redemption(days=180).interest > redemption(days=90).interest
    assert redemption(days=0).interest.is_zero


def test_a_heavier_bale_owes_more():
    assert redemption(net=Weight(600)).due > redemption().due


def test_a_bale_has_to_weigh_something():
    with pytest.raises(ValidationError):
        redemption(net=Weight.zero())


@pytest.mark.parametrize("days", [-1])
def test_a_negative_term_is_refused(days):
    with pytest.raises(ValidationError):
        redemption(days=days)


@pytest.mark.parametrize("rate", ["-0.01", "25.01"])
def test_a_rate_off_the_scale_is_refused(rate):
    with pytest.raises(ValidationError):
        redemption(annual_rate=Decimal(rate))


def test_a_redemption_prints_which_path_it_took():
    assert str(redemption()).endswith("at the loan rate for $264.01")
    assert "at the world price" in str(redemption(world_price=CentsPerPound.of("46.00")))
