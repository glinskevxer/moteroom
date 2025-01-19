from decimal import Decimal

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import CentsPerPound, Money, total_money
from moteroom.core.weight import Weight


def test_money_is_exact_to_the_cent():
    assert Money.parse("1234.56").amount == Decimal("1234.56")
    assert Money.dollars(12).amount == Decimal("12.00")


def test_money_refuses_a_third_decimal():
    with pytest.raises(ValidationError):
        Money(Decimal("1.005"))
    with pytest.raises(ValidationError):
        Money.parse("1.005")


def test_money_refuses_a_float():
    with pytest.raises(ValidationError):
        Money(1.5)  # type: ignore[arg-type]


@pytest.mark.parametrize("text", ["", "  ", "cotton", "$"])
def test_money_refuses_junk(text):
    with pytest.raises(ValidationError):
        Money.parse(text)


def test_money_reads_a_statement_line():
    assert Money.parse(" $1,234.56 ") == Money.dollars("1234.56")


def test_money_can_go_negative_because_deductions_do():
    assert (Money.dollars(10) - Money.dollars(25)).amount == Decimal("-15.00")
    assert str(Money.dollars(10) - Money.dollars(25)) == "-$15.00"


def test_money_prints_with_separators():
    assert str(Money.parse("48320.07")) == "$48,320.07"


def test_money_arithmetic():
    assert Money.dollars(3) + Money.dollars(4) == Money.dollars(7)
    assert (-Money.dollars(3)).amount == Decimal("-3.00")
    assert Money.dollars(3).times(4) == Money.dollars(12)
    assert Money.zero().is_zero


def test_total_money_adds_a_column():
    assert total_money([Money.dollars(1), Money.dollars(2)]) == Money.dollars(3)
    assert total_money([]) == Money.zero()


def test_allocate_keeps_every_penny():
    parts = Money.parse("100.00").allocate([1, 1, 1])
    assert [str(p) for p in parts] == ["$33.34", "$33.33", "$33.33"]
    assert total_money(parts) == Money.parse("100.00")


def test_allocate_on_uneven_shares():
    parts = Money.parse("1000.00").allocate([3, 1])
    assert parts == [Money.parse("750.00"), Money.parse("250.00")]


def test_allocate_skips_a_zero_share():
    parts = Money.parse("0.05").allocate([0, 1, 1])
    assert parts[0].is_zero
    assert total_money(parts) == Money.parse("0.05")


def test_allocate_of_a_negative_still_balances():
    parts = Money.parse("-100.00").allocate([1, 1, 1])
    assert total_money(parts) == Money.parse("-100.00")


@pytest.mark.parametrize("shares", [[], [-1, 2], [0, 0]])
def test_allocate_refuses_a_bad_split(shares):
    with pytest.raises(ValidationError):
        Money.parse("10.00").allocate(shares)


def test_rate_is_exact_to_a_hundredth_of_a_cent():
    assert CentsPerPound.parse("52.34").cents == Decimal("52.34")
    assert str(CentsPerPound.of(52)) == "52.00c"


def test_rate_reads_a_quote_with_a_c_on_it():
    assert CentsPerPound.parse("52.34c") == CentsPerPound.of("52.34")


def test_rate_refuses_a_third_decimal():
    with pytest.raises(ValidationError):
        CentsPerPound(Decimal("52.345"))
    with pytest.raises(ValidationError):
        CentsPerPound.parse("52.345")


def test_rate_refuses_a_float():
    with pytest.raises(ValidationError):
        CentsPerPound(52.3)  # type: ignore[arg-type]


def test_rate_arithmetic():
    assert CentsPerPound.of(50) + CentsPerPound.of("2.34") == CentsPerPound.of("52.34")
    assert CentsPerPound.of(50) - CentsPerPound.of("2.34") == CentsPerPound.of("47.66")


def test_rate_on_a_bale_rounds_half_up():
    assert CentsPerPound.of("52.34").on(Weight(500)) == Money.parse("261.70")
    assert CentsPerPound.of("52.35").on(Weight(501)) == Money.parse("262.27")
    assert CentsPerPound.of("52.34").on(Weight.zero()).is_zero
