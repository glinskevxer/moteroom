from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.settlement.cheque import Cheque, Register

ISSUED = date(2026, 2, 3)


def cheque(**overrides: Any) -> Cheque:
    fields: dict[str, Any] = {
        "number": "1001",
        "payee": "BLYTHE",
        "amount": Money.parse("10885.72"),
        "issued_on": ISSUED,
    }
    fields.update(overrides)
    return Cheque(**fields)


@pytest.mark.parametrize("number", ["", "101", "123456789", "10a1"])
def test_a_cheque_number_has_a_shape(number):
    with pytest.raises(ValidationError):
        cheque(number=number)


def test_a_cheque_names_a_payee_and_an_amount():
    with pytest.raises(ValidationError):
        cheque(payee="  ")
    with pytest.raises(ValidationError):
        cheque(amount=Money.zero())


def test_a_new_cheque_is_outstanding():
    assert cheque().is_outstanding
    assert not cheque().is_voided
    assert str(cheque()).endswith("outstanding")


def test_clearing_makes_a_new_record():
    cleared = cheque().clear(date(2026, 2, 10))
    assert not cleared.is_outstanding
    assert cleared.cleared_on == date(2026, 2, 10)
    assert cheque().is_outstanding
    assert str(cleared).endswith("cleared")


def test_a_cheque_clears_or_voids_once():
    cleared = cheque().clear(date(2026, 2, 10))
    with pytest.raises(ValidationError):
        cleared.clear(date(2026, 2, 11))
    with pytest.raises(ValidationError):
        cleared.void(date(2026, 2, 11), "lost")


def test_voiding_needs_a_reason():
    voided = cheque().void(date(2026, 2, 10), "lost in the post")
    assert voided.is_voided
    assert "lost in the post" in str(voided)
    with pytest.raises(ValidationError):
        cheque().void(date(2026, 2, 10), "  ")


def test_a_date_before_the_cheque_was_written_is_refused():
    with pytest.raises(ValidationError):
        cheque(cleared_on=date(2026, 2, 1))
    with pytest.raises(ValidationError):
        cheque(voided_on=date(2026, 2, 1))


def test_a_cheque_cannot_be_cleared_and_voided():
    with pytest.raises(ValidationError):
        cheque(cleared_on=ISSUED, voided_on=ISSUED, void_reason="lost")


def test_a_cheque_goes_stale_after_six_months():
    assert not cheque().is_stale(date(2026, 8, 1))
    assert cheque().is_stale(date(2026, 8, 3))
    assert not cheque().clear(date(2026, 2, 10)).is_stale(date(2027, 1, 1))


def test_the_register_holds_cheques_in_number_order():
    register = Register()
    register.extend([cheque(number="1002"), cheque(number="1001")])
    assert [one.number for one in register.cheques()] == ["1001", "1002"]
    assert len(register) == 2


def test_a_number_is_used_once():
    register = Register()
    register.issue(cheque())
    with pytest.raises(ValidationError):
        register.issue(cheque())


def test_a_cheque_nobody_wrote():
    with pytest.raises(ValidationError):
        Register().get("1001")


def test_the_register_clears_and_voids_in_place():
    register = Register()
    register.extend([cheque(), cheque(number="1002")])
    register.clear("1001", date(2026, 2, 10))
    register.void("1002", date(2026, 2, 10), "lost")
    assert register.outstanding() == []
    assert register.paid() == Money.parse("10885.72")
    assert register.owed().is_zero


def test_the_register_totals_what_is_still_out():
    register = Register()
    register.extend([cheque(), cheque(number="1002", amount=Money.parse("100.00"))])
    assert register.owed() == Money.parse("10985.72")
    assert register.paid().is_zero


def test_the_register_finds_stale_cheques_and_a_payee():
    register = Register()
    register.extend([cheque(), cheque(number="1002", payee="MERRITT")])
    assert [one.number for one in register.stale(date(2026, 9, 1))] == ["1001", "1002"]
    assert [one.number for one in register.for_payee("MERRITT")] == ["1002"]


def test_the_next_number_follows_the_highest():
    register = Register()
    assert register.next_number() == "1001"
    register.issue(cheque(number="1040"))
    assert register.next_number() == "1041"
