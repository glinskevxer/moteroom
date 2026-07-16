"""Money followed from the lot sheet to the cheque.

Every step in a settlement rounds. Lint is divided between producers, a rate
is applied to a weight, seed is split on shares, and a cheque is written for
the total. Each of those rounds to the pound or to the cent, and the question
that matters is whether the roundings ever add up to a loss.

They are swept here rather than exampled: the same chain is run over a range
of weights and shares and the invariant is checked every time.
"""

from decimal import Decimal

import pytest

from moteroom.core.money import CentsPerPound, Money, total_money
from moteroom.core.season import Season
from moteroom.core.weight import Weight, total
from moteroom.receiving.party import ShareSplit
from moteroom.settlement.allocation import divide, divide_count
from moteroom.settlement.charges import ChargeSchedule, bill
from moteroom.settlement.seed import SeedTerms, credit
from moteroom.settlement.statement import Statement

SEASON = Season(2025)
RATE = CentsPerPound.of("52.34")
CHARGES = ChargeSchedule(
    ginning_per_cwt=Money.parse("4.25"),
    bagging_and_ties=Money.parse("11.50"),
    module_handling=Money.parse("18.00"),
)
SEED = SeedTerms(price_per_ton=Money.parse("205.00"), gin_shares=1, producer_shares=3)


@pytest.mark.parametrize(
    "basis", [{"A": 3, "B": 1}, {"A": 1, "B": 1, "C": 1}, {"A": 5, "B": 2}]
)
def test_the_lint_divided_between_producers_is_the_lint_the_lot_made(basis):
    weights = {name: Weight(pounds * 1_000) for name, pounds in basis.items()}
    for lint in range(1, 40_000, 977):
        parts = divide(Weight(lint), weights)
        assert total(list(parts.values())) == Weight(lint)


@pytest.mark.parametrize("bales", [0, 1, 7, 44, 145])
def test_the_bales_divided_between_producers_are_the_bales_pressed(bales):
    weights = {"A": Weight(42_400), "B": Weight(21_200), "C": Weight(7_003)}
    assert sum(divide_count(bales, weights).values()) == bales


def test_paying_each_producer_at_the_same_rate_never_loses_a_cent():
    weights = {"A": Weight(42_400), "B": Weight(21_200), "C": Weight(7_003)}
    for lint in range(1_000, 30_000, 1_013):
        parts = divide(Weight(lint), weights)
        paid = total_money([RATE.on(one) for one in parts.values()])
        whole = RATE.on(Weight(lint))
        assert abs(paid.amount - whole.amount) <= Decimal("0.03")


def test_the_seed_credit_and_the_gin_share_add_back_to_the_seed():
    for seed in range(0, 60_000, 1_301):
        made = credit(Weight(seed), SEED)
        assert made.gin_share + made.producer_share == made.gross


def test_the_gin_bill_lines_add_to_the_total():
    for pounds in range(2_000, 90_000, 3_701):
        made = bill(CHARGES, Weight(pounds), bales=max(pounds // 1_500, 1), modules=3)
        named = dict(made.lines())
        body = sum(
            (amount.amount for name, amount in made.lines() if name != "total"),
            start=Decimal("0.00"),
        )
        assert body == named["total"].amount


def test_a_statement_always_adds_to_its_own_lines():
    for cents in range(0, 20_000, 719):
        made = Statement(
            producer="BLYTHE",
            season=SEASON,
            bales=44,
            lint=Weight(22_300),
            lint_proceeds=Money(Decimal(cents) / Decimal(100)),
            gin_charges=Money.parse("3263.00"),
            seed_credit=Money.parse("2500.12"),
            freight=Money.parse("250.00"),
            byproduct_credit=Money.parse("100.00"),
        )
        body = sum(
            (amount.amount for name, amount in made.lines() if name != "net"),
            start=Decimal("0.00"),
        )
        assert body == made.net.amount


def test_a_lease_split_of_a_settlement_pays_out_the_settlement():
    split = ShareSplit.parse("BLYTHE:3,MERRITT:1")
    for cents in range(1, 50_000, 811):
        amount = Money(Decimal(cents) / Decimal(100))
        assert total_money(list(split.split_money(amount).values())) == amount


def test_the_whole_chain_holds_from_lint_to_cheque():
    weights = {"BLYTHE": Weight(42_400), "MERRITT": Weight(21_200)}
    for lint in range(2_000, 40_000, 2_003):
        shares = divide(Weight(lint), weights)
        assert total(list(shares.values())) == Weight(lint)
        proceeds = {name: RATE.on(one) for name, one in shares.items()}
        cheques = total_money(list(proceeds.values()))
        assert abs(cheques.amount - RATE.on(Weight(lint)).amount) <= Decimal("0.02")
