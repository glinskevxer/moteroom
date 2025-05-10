from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.settlement.statement import Advance, Statement


def statement(**overrides: Any) -> Statement:
    fields: dict[str, Any] = {
        "producer": "BLYTHE",
        "season": Season(2025),
        "bales": 44,
        "lint": Weight(22_300),
        "lint_proceeds": Money.parse("11648.60"),
        "gin_charges": Money.parse("3263.00"),
        "seed_credit": Money.parse("2500.12"),
    }
    fields.update(overrides)
    return Statement(**fields)


def test_the_net_is_proceeds_and_seed_less_charges():
    assert statement().net == Money.parse("10885.72")
    assert statement().is_payable


def test_advances_come_off_the_net():
    with_advance = statement(advances=(Advance("A-114", Money.parse("5000.00")),))
    assert with_advance.advanced == Money.parse("5000.00")
    assert with_advance.net == Money.parse("5885.72")


def test_a_statement_can_come_out_owing():
    owing = statement(advances=(Advance("A-114", Money.parse("20000.00")),))
    assert not owing.is_payable
    assert owing.net.amount < 0
    assert str(owing).endswith("owing")


def test_the_lines_add_back_to_the_net():
    made = statement(advances=(Advance("A-114", Money.parse("5000.00")),))
    named = made.lines()
    assert named[-1][0] == "net"
    body = sum((amount.amount for _, amount in named[:-1]), start=Money.zero().amount)
    assert body == made.net.amount


def test_an_advance_appears_on_its_own_line():
    made = statement(advances=(Advance("A-114", Money.parse("5000.00")),))
    assert ("advance A-114", Money.parse("-5000.00")) in made.lines()


def test_a_producer_has_to_be_named():
    with pytest.raises(ValidationError):
        statement(producer="  ")


def test_a_negative_bale_count_is_refused():
    with pytest.raises(ValidationError):
        statement(bales=-1)


def test_gin_charges_are_stated_positive():
    with pytest.raises(ValidationError):
        statement(gin_charges=Money.parse("-100.00"))


def test_the_same_advance_cannot_be_taken_twice():
    twice = (Advance("A-114", Money.parse("100.00")), Advance("A-114", Money.parse("200.00")))
    with pytest.raises(ValidationError):
        statement(advances=twice)


@pytest.mark.parametrize("amount", ["0.00", "-1.00"])
def test_an_advance_has_to_be_money(amount):
    with pytest.raises(ValidationError):
        Advance("A-114", Money.parse(amount))


def test_an_advance_needs_a_reference():
    with pytest.raises(ValidationError):
        Advance("  ", Money.parse("100.00"))


def test_a_statement_prints_its_summary():
    assert str(statement()) == "BLYTHE 2025/26 44 bales 10885.72 due"
