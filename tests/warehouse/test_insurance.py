from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.warehouse.insurance import Policy, exposure, premium
from moteroom.warehouse.receipt import Receipt

GIN = GinCode("41207")
SEASON = Season(2025)
AS_OF = date(2025, 12, 1)
PRICE = CentsPerPound.of("68.50")


def policy(**overrides: Any) -> Policy:
    fields: dict[str, Any] = {
        "insurer": "DELTA MUTUAL",
        "number": "P-4471",
        "per_bale": Money.parse("350.00"),
        "limit": Money.parse("700.00"),
        "starts_on": date(2025, 8, 1),
        "ends_on": date(2026, 7, 31),
    }
    fields.update(overrides)
    return Policy(**fields)


def receipt(number: int) -> Receipt:
    return Receipt(
        number=f"MW{number:08d}",
        warehouse="MW14",
        bale_id=BaleId.build(SEASON, GIN, number),
        received_on=date(2025, 10, 20),
        net=Weight(515),
        holder="BLYTHE",
    )


def test_a_policy_reads_back():
    assert str(policy()).startswith("DELTA MUTUAL P-4471 at $350.00 a bale")
    assert policy().bales_covered() == 2
    assert policy().covers(AS_OF)
    assert not policy().covers(date(2026, 8, 1))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("insurer", " "),
        ("number", " "),
        ("per_bale", Money.zero()),
        ("limit", Money.zero()),
        ("deductible", Money.parse("-1.00")),
    ],
)
def test_a_policy_refuses_junk(field, value):
    with pytest.raises(ValidationError):
        policy(**{field: value})


def test_a_policy_has_to_run_forwards():
    with pytest.raises(ValidationError):
        policy(ends_on=date(2025, 8, 1))


def test_a_bale_in_store_is_covered_when_the_value_is_under_the_declared():
    made = exposure([receipt(1)], policy(), PRICE, AS_OF)
    assert made.in_force
    assert made.market_value == Money.parse("352.78")
    assert made.declared == Money.parse("350.00")
    assert made.payable == Money.parse("350.00")
    assert made.shortfall == Money.parse("2.78")
    assert not made.is_covered
    assert "short by" in str(made)


def test_a_generous_policy_covers_it():
    made = exposure([receipt(1)], policy(per_bale=Money.parse("500.00")), PRICE, AS_OF)
    assert made.is_covered
    assert made.shortfall.is_zero
    assert str(made) == "1 bales covered"


def test_the_limit_caps_what_would_be_paid():
    made = exposure([receipt(1), receipt(2), receipt(3)], policy(), PRICE, AS_OF)
    assert made.over_limit
    assert made.payable == Money.parse("700.00")
    assert made.shortfall.amount > 0


def test_a_deductible_comes_off_what_would_be_paid():
    made = exposure([receipt(1)], policy(deductible=Money.parse("100.00")), PRICE, AS_OF)
    assert made.payable == Money.parse("250.00")


def test_a_deductible_bigger_than_the_cover_pays_nothing():
    made = exposure([receipt(1)], policy(deductible=Money.parse("500.00")), PRICE, AS_OF)
    assert made.payable.is_zero


def test_a_policy_out_of_force_pays_nothing():
    made = exposure([receipt(1)], policy(), PRICE, date(2026, 9, 1))
    assert not made.in_force
    assert made.payable.is_zero
    assert "no cover" in str(made)


def test_a_released_bale_is_not_in_store():
    released = receipt(1).release(date(2025, 11, 1), "CALCOT")
    made = exposure([released], policy(), PRICE, AS_OF)
    assert made.bales == 0
    assert made.lint.is_zero
    assert made.is_covered


def test_the_lines_read_in_order():
    names = [name for name, _ in exposure([receipt(1)], policy(), PRICE, AS_OF).lines()]
    assert names[0] == "policy"
    assert names[-1] == "shortfall"


def test_the_premium_is_quoted_per_hundred_of_declared_value():
    assert premium(policy(), Money.parse("0.45"), 100) == Money.parse("157.50")
    assert premium(policy(), Money.parse("0.45"), 0).is_zero


def test_a_negative_premium_or_count_is_refused():
    with pytest.raises(ValidationError):
        premium(policy(), Money.parse("-0.01"), 10)
    with pytest.raises(ValidationError):
        premium(policy(), Money.parse("0.45"), -1)
