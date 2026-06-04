from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.settlement.late import Account, late_on, outstanding, owed_on

BILLED = date(2026, 2, 3)


def account(**overrides: Any) -> Account:
    fields: dict[str, Any] = {
        "producer": "BLYTHE",
        "owed": Money.parse("4000.00"),
        "billed_on": BILLED,
        "rate": Decimal("9.00"),
    }
    fields.update(overrides)
    return Account(**fields)


def test_an_account_exists_only_when_something_is_owed():
    with pytest.raises(ValidationError):
        account(owed=Money.zero())
    with pytest.raises(ValidationError):
        account(owed=Money.parse("-1.00"))


def test_an_account_names_somebody_at_a_sane_rate():
    with pytest.raises(ValidationError):
        account(producer=" ")
    with pytest.raises(ValidationError):
        account(rate=Decimal("24.01"))
    with pytest.raises(ValidationError):
        account(grace_days=-1)


def test_the_grace_period_holds_the_interest_off():
    made = account()
    assert made.due_on == date(2026, 3, 5)
    assert made.days_late(date(2026, 3, 5)) == 0
    assert made.interest(date(2026, 3, 5)).is_zero
    assert made.due(date(2026, 3, 5)) == Money.parse("4000.00")


def test_interest_runs_once_the_grace_period_is_past():
    made = account()
    assert made.days_late(date(2026, 4, 5)) == 31
    assert made.interest(date(2026, 4, 5)) == Money.parse("30.58")
    assert made.is_late(date(2026, 4, 5))


def test_a_longer_grace_period_holds_it_off_longer():
    assert account(grace_days=90).interest(date(2026, 4, 5)).is_zero


def test_paying_stops_the_clock():
    paid = account().settle(date(2026, 4, 5))
    assert paid.is_paid
    assert paid.days_late(date(2027, 1, 1)) == 31
    assert paid.due(date(2027, 1, 1)).is_zero
    assert not paid.is_late(date(2027, 1, 1))
    assert str(paid) == "BLYTHE paid $4,000.00"


def test_an_account_is_paid_once():
    paid = account().settle(date(2026, 4, 5))
    with pytest.raises(ValidationError):
        paid.settle(date(2026, 5, 1))


def test_paying_before_the_bill_went_out():
    with pytest.raises(ValidationError):
        account(paid_on=date(2026, 1, 1))


def test_an_open_account_prints_what_it_owes():
    assert str(account()) == "BLYTHE owes $4,000.00 from 2026-02-03"


def test_the_open_accounts_come_back_oldest_first():
    held = [
        account(billed_on=date(2026, 3, 1)),
        account(producer="MERRITT"),
        account(producer="COLE").settle(date(2026, 4, 1)),
    ]
    assert [one.producer for one in outstanding(held)] == ["MERRITT", "BLYTHE"]


def test_what_the_gin_is_owed_counts_the_interest():
    held = [account(), account(producer="MERRITT", owed=Money.parse("1000.00"))]
    assert owed_on(held, date(2026, 3, 1)) == Money.parse("5000.00")
    assert owed_on(held, date(2026, 4, 5)) > Money.parse("5000.00")


def test_the_late_accounts_come_back_worst_first():
    held = [
        account(billed_on=date(2026, 3, 1)),
        account(producer="MERRITT"),
    ]
    late = late_on(held, date(2026, 5, 1))
    assert [one.producer for one in late] == ["MERRITT", "BLYTHE"]
    assert late_on(held, date(2026, 2, 4)) == []
