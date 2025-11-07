import pytest

from moteroom.core.errors import ConflictError, ValidationError
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.settlement.equity import EquityLedger, Holding, allocate_margin

SEASON = Season(2025)
VOLUME = {"BLYTHE": Weight(42_400), "MERRITT": Weight(21_200)}


def test_the_margin_splits_on_ginned_volume():
    made = allocate_margin(SEASON, Money.parse("30000.00"), VOLUME)
    assert made.for_producer("BLYTHE").allocated == Money.parse("20000.00")
    assert made.for_producer("MERRITT").allocated == Money.parse("10000.00")
    assert made.members == 2


def test_the_split_keeps_every_penny():
    made = allocate_margin(SEASON, Money.parse("100.01"), VOLUME)
    assert made.cash + made.retained == Money.parse("100.01")


def test_the_cash_and_equity_shares_divide_each_allocation():
    made = allocate_margin(SEASON, Money.parse("30000.00"), VOLUME)
    blythe = made.for_producer("BLYTHE")
    assert blythe.cash == Money.parse("4000.00")
    assert blythe.retained == Money.parse("16000.00")
    assert str(blythe).startswith("BLYTHE $20,000.00 allocated")


def test_paying_it_all_in_cash_retains_nothing():
    made = allocate_margin(
        SEASON, Money.parse("30000.00"), VOLUME, cash_shares=1, equity_shares=0
    )
    assert made.retained.is_zero
    assert made.cash == Money.parse("30000.00")


def test_retaining_all_of_it_pays_no_cash():
    made = allocate_margin(
        SEASON, Money.parse("30000.00"), VOLUME, cash_shares=0, equity_shares=1
    )
    assert made.cash.is_zero


def test_a_loss_is_not_allocated():
    with pytest.raises(ValidationError):
        allocate_margin(SEASON, Money.parse("-1.00"), VOLUME)


def test_nobody_ginning_anything_is_refused():
    with pytest.raises(ValidationError):
        allocate_margin(SEASON, Money.parse("100.00"), {})
    with pytest.raises(ValidationError):
        allocate_margin(SEASON, Money.parse("100.00"), {"BLYTHE": Weight.zero()})


@pytest.mark.parametrize(("cash", "equity"), [(-1, 1), (1, -1), (0, 0), (900, 900)])
def test_a_bad_share_split_is_refused(cash, equity):
    with pytest.raises(ValidationError):
        allocate_margin(SEASON, Money.parse("100.00"), VOLUME, cash, equity)


def test_asking_for_a_member_who_ginned_nothing():
    made = allocate_margin(SEASON, Money.parse("100.00"), VOLUME)
    with pytest.raises(ValidationError):
        made.for_producer("COLE")


def test_the_ledger_credits_a_season_once():
    ledger = EquityLedger()
    ledger.credit(SEASON, "BLYTHE", Money.parse("16000.00"))
    with pytest.raises(ConflictError):
        ledger.credit(SEASON, "BLYTHE", Money.parse("1.00"))


def test_the_ledger_refuses_an_empty_credit():
    ledger = EquityLedger()
    with pytest.raises(ValidationError):
        ledger.credit(SEASON, "BLYTHE", Money.zero())


def test_an_allocation_credits_the_whole_ledger():
    ledger = EquityLedger()
    ledger.credit_all(allocate_margin(SEASON, Money.parse("30000.00"), VOLUME))
    assert ledger.balance("BLYTHE") == Money.parse("16000.00")
    assert ledger.total() == Money.parse("24000.00")
    assert ledger.members() == ["BLYTHE", "MERRITT"]


def test_an_allocation_with_no_equity_credits_nothing():
    ledger = EquityLedger()
    ledger.credit_all(
        allocate_margin(SEASON, Money.parse("30000.00"), VOLUME, cash_shares=1, equity_shares=0)
    )
    assert len(ledger) == 0


def test_holdings_come_back_oldest_first():
    ledger = EquityLedger()
    ledger.credit(Season(2026), "BLYTHE", Money.parse("100.00"))
    ledger.credit(SEASON, "BLYTHE", Money.parse("200.00"))
    assert [held.season.year for held in ledger.holdings()] == [2025, 2026]
    assert ledger.seasons() == [SEASON, Season(2026)]


def test_a_balance_adds_every_year_a_member_holds():
    ledger = EquityLedger()
    ledger.credit(SEASON, "BLYTHE", Money.parse("200.00"))
    ledger.credit(Season(2026), "BLYTHE", Money.parse("100.00"))
    assert ledger.balance("BLYTHE") == Money.parse("300.00")
    assert ledger.balance("MERRITT").is_zero


def test_retiring_takes_the_oldest_year_and_only_that_one():
    ledger = EquityLedger()
    ledger.credit(SEASON, "BLYTHE", Money.parse("200.00"))
    ledger.credit(SEASON, "MERRITT", Money.parse("100.00"))
    ledger.credit(Season(2026), "BLYTHE", Money.parse("50.00"))
    retired = ledger.retire(SEASON)
    assert [held.producer for held in retired] == ["BLYTHE", "MERRITT"]
    assert ledger.total() == Money.parse("50.00")
    assert ledger.oldest_season() == Season(2026)


def test_retiring_out_of_order_is_refused():
    ledger = EquityLedger()
    ledger.credit(SEASON, "BLYTHE", Money.parse("200.00"))
    ledger.credit(Season(2026), "BLYTHE", Money.parse("50.00"))
    with pytest.raises(ValidationError):
        ledger.retire(Season(2026))


def test_retiring_an_empty_ledger():
    with pytest.raises(ValidationError):
        EquityLedger().retire(SEASON)
    assert EquityLedger().oldest_season() is None


def test_a_ledger_loads_from_holdings():
    ledger = EquityLedger()
    ledger.load([Holding(SEASON, "BLYTHE", Money.parse("200.00"))])
    assert ledger.balance("BLYTHE") == Money.parse("200.00")
