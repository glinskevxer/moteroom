"""Arithmetic invariants swept over wide ranges.

Rounding is where money goes missing, so the rules that have to hold whatever
the numbers are get checked over a fixed sweep rather than on the two examples
that happened to be written first.
"""

from decimal import Decimal

import pytest

from moteroom.core.money import CentsPerPound, Money, total_money
from moteroom.core.reading import ratio, share
from moteroom.core.weight import Weight
from moteroom.receiving.party import ShareSplit
from moteroom.settlement.allocation import divide, divide_count


@pytest.mark.parametrize("shares", [[1, 1], [1, 1, 1], [3, 1], [5, 3, 2], [7, 0, 1]])
def test_money_always_allocates_to_exactly_what_went_in(shares):
    for cents in range(0, 1_000, 7):
        amount = Money(Decimal(cents) / Decimal(100))
        parts = amount.allocate(shares)
        assert total_money(parts) == amount
        assert len(parts) == len(shares)


def test_a_negative_amount_allocates_to_itself_too():
    for cents in range(0, 500, 3):
        amount = Money(Decimal(-cents) / Decimal(100))
        assert total_money(amount.allocate([1, 1, 1])) == amount


@pytest.mark.parametrize(
    "basis", [{"A": 2, "B": 1}, {"A": 1, "B": 1, "C": 1}, {"A": 9, "B": 1}]
)
def test_weight_always_divides_to_exactly_what_went_in(basis):
    weights = {name: Weight(pounds) for name, pounds in basis.items()}
    for pounds in range(1, 2_000, 13):
        parts = divide(Weight(pounds), weights)
        assert sum(part.pounds for part in parts.values()) == pounds


def test_a_bale_count_always_divides_to_the_count():
    basis = {"A": Weight(42_400), "B": Weight(21_200), "C": Weight(7_000)}
    for count in range(0, 200):
        parts = divide_count(count, basis)
        assert sum(parts.values()) == count


def test_a_lease_split_never_loses_a_pound_or_a_penny():
    split = ShareSplit.parse("BLYTHE:3,MERRITT:1,COLE:1")
    for pounds in range(1, 3_000, 11):
        parts = split.split_weight(Weight(pounds))
        assert sum(one.pounds for one in parts.values()) == pounds
    for cents in range(1, 3_000, 11):
        amount = Money(Decimal(cents) / Decimal(100))
        assert total_money(list(split.split_money(amount).values())) == amount


def test_a_rate_on_a_weight_is_monotonic():
    rate = CentsPerPound.of("52.34")
    last = Money.zero()
    for pounds in range(0, 2_000, 7):
        now = rate.on(Weight(pounds))
        assert now >= last
        last = now


def test_a_heavier_bale_is_never_worth_less_at_the_same_rate():
    for cents in range(1, 200, 3):
        rate = CentsPerPound(Decimal(cents) / Decimal(100))
        assert rate.on(Weight(500)) <= rate.on(Weight(501))


def test_a_percentage_of_a_whole_is_never_more_than_a_hundred():
    for part in range(0, 1_000, 7):
        assert ratio(part, 1_000) <= Decimal("100.00")
        assert share(part, 1_000) <= Decimal("100.00")


def test_hundredweight_and_pounds_agree():
    for pounds in range(0, 100_000, 137):
        assert Weight(pounds).hundredweight() * Decimal(100) == Decimal(pounds)


def test_a_share_of_a_weight_never_exceeds_it():
    for pounds in range(0, 5_000, 17):
        for numerator in (0, 1, 2, 3):
            assert Weight(pounds).share(numerator, 3).pounds <= pounds + 1
