from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, ValidationError
from moteroom.core.money import Money
from moteroom.settlement.deferred import Deferral, DeferralBook

AGREED = date(2025, 9, 1)
PAY = date(2026, 1, 15)


def deferral(**overrides: Any) -> Deferral:
    fields: dict[str, Any] = {
        "producer": "BLYTHE",
        "amount": Money.parse("10000.00"),
        "agreed_on": AGREED,
        "pay_on": PAY,
        "rate": Decimal("4.00"),
    }
    fields.update(overrides)
    return Deferral(**fields)


def test_a_deferral_holds_money_to_a_named_day():
    made = deferral()
    assert made.days == 136
    assert str(made) == "BLYTHE $10,000.00 held to 2026-01-15"


def test_a_deferral_has_to_hold_money_for_somebody():
    with pytest.raises(ValidationError):
        deferral(producer=" ")
    with pytest.raises(ValidationError):
        deferral(amount=Money.zero())


def test_paying_in_the_same_year_defers_nothing():
    with pytest.raises(ValidationError) as caught:
        deferral(pay_on=date(2025, 12, 31))
    assert "defers nothing" in caught.value.message


def test_a_pay_day_before_the_agreement_is_refused():
    with pytest.raises(ValidationError):
        deferral(pay_on=date(2025, 8, 1))


@pytest.mark.parametrize("rate", ["-0.01", "15.01"])
def test_a_rate_off_the_scale_is_refused(rate):
    with pytest.raises(ValidationError):
        deferral(rate=Decimal(rate))


def test_interest_runs_from_the_agreement():
    assert deferral().interest(AGREED).is_zero
    assert deferral().interest(date(2025, 12, 1)) == Money.parse("99.73")


def test_interest_stops_on_the_pay_day():
    at_maturity = deferral().interest(PAY)
    assert deferral().interest(date(2026, 6, 1)) == at_maturity


def test_asking_before_the_agreement_holds_nothing():
    assert deferral().held_days(date(2025, 8, 1)) == 0
    assert deferral().interest(date(2025, 8, 1)).is_zero


def test_a_deferral_with_no_interest_pays_back_what_it_held():
    made = deferral(rate=Decimal("0.00"))
    assert made.due(PAY) == Money.parse("10000.00")


def test_a_deferral_matures_on_its_day():
    assert not deferral().is_matured(date(2026, 1, 14))
    assert deferral().is_matured(PAY)


def test_the_book_refuses_two_deferrals_to_the_same_day():
    book = DeferralBook()
    book.agree(deferral())
    with pytest.raises(ConflictError):
        book.agree(deferral(amount=Money.parse("1.00")))
    book.agree(deferral(pay_on=date(2026, 2, 15)))
    assert len(book) == 2


def test_the_book_lists_soonest_first():
    book = DeferralBook()
    book.extend([deferral(pay_on=date(2026, 3, 1)), deferral()])
    assert [one.pay_on for one in book.deferrals()] == [PAY, date(2026, 3, 1)]
    assert book.producers() == ["BLYTHE"]


def test_the_book_totals_what_it_is_holding():
    book = DeferralBook()
    book.extend([deferral(), deferral(producer="MERRITT", amount=Money.parse("5000.00"))])
    assert book.held() == Money.parse("15000.00")
    assert book.owed(date(2025, 12, 1)) > book.held()


def test_the_book_finds_what_has_come_due():
    book = DeferralBook()
    book.extend([deferral(), deferral(pay_on=date(2026, 3, 1))])
    assert [one.pay_on for one in book.maturing(date(2026, 2, 1))] == [PAY]
    assert book.maturing(date(2025, 12, 1)) == []


def test_one_producer_reads_out_of_the_book():
    book = DeferralBook()
    book.extend([deferral(), deferral(producer="MERRITT")])
    assert [one.producer for one in book.deferrals("MERRITT")] == ["MERRITT"]
