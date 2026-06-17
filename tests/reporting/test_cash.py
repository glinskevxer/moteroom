from datetime import date
from decimal import Decimal

from moteroom.core.money import Money
from moteroom.reporting.cash import coming_due, position, stale_cheques
from moteroom.settlement.cheque import Cheque
from moteroom.settlement.deferred import Deferral
from moteroom.settlement.late import Account

AS_OF = date(2026, 3, 1)


def cheque(number: str = "1001", issued: date = date(2026, 2, 3)) -> Cheque:
    return Cheque(number, "BLYTHE", Money.parse("1000.00"), issued)


def deferral(pay_on: date = date(2026, 3, 15)) -> Deferral:
    return Deferral("BLYTHE", Money.parse("5000.00"), date(2025, 9, 1), pay_on, Decimal("0.00"))


def account(billed: date = date(2026, 1, 3)) -> Account:
    return Account("MERRITT", Money.parse("2000.00"), billed, Decimal("9.00"))


def test_the_page_carries_all_four_obligations():
    made = position([cheque()], [deferral()], [account()], Money.parse("24000.00"), AS_OF)
    named = dict(zip(made.column("what"), made.column("amount"), strict=True))
    assert named["cheques outstanding"] == "$1,000.00"
    assert named["deferrals held"] == "$5,000.00"
    assert named["equity standing"] == "$24,000.00"
    assert named["owed to the gin"].startswith("$2,0")


def test_the_net_is_the_four_against_each_other():
    made = position([cheque()], [], [], Money.zero(), AS_OF)
    named = dict(zip(made.column("what"), made.column("amount"), strict=True))
    assert named["net obligation"] == "$1,000.00"


def test_a_cleared_cheque_is_not_outstanding():
    cleared = cheque().clear(date(2026, 2, 10))
    made = position([cleared], [], [], Money.zero(), AS_OF)
    assert (
        dict(zip(made.column("what"), made.column("amount"), strict=True))[
            "cheques outstanding"
        ]
        == "$0.00"
    )


def test_a_quiet_page_says_nothing_needs_chasing():
    made = position([cheque()], [deferral()], [account(billed=AS_OF)], Money.zero(), AS_OF)
    assert made.notes == ("nothing needs chasing",)


def test_the_page_names_what_needs_chasing():
    made = position(
        [cheque(issued=date(2025, 6, 1))],
        [deferral(pay_on=date(2026, 1, 15))],
        [account()],
        Money.zero(),
        AS_OF,
    )
    assert any("stale" in note for note in made.notes)
    assert any("come due" in note for note in made.notes)
    assert any("grace period" in note for note in made.notes)


def test_the_stale_cheques_page_lists_them_oldest_first():
    made = stale_cheques(
        [cheque(issued=date(2025, 6, 1)), cheque("1002", issued=date(2025, 5, 1)), cheque()],
        AS_OF,
    )
    assert made.column("cheque") == ["1002", "1001"]
    assert "2 to rewrite" in made.notes[0]


def test_a_page_with_no_stale_cheques():
    assert stale_cheques([cheque()], AS_OF).is_empty


def test_the_deferrals_coming_due_are_listed_soonest_first():
    made = coming_due([deferral(), deferral(pay_on=date(2026, 3, 5))], AS_OF)
    assert made.column("pays") == ["2026-03-05", "2026-03-15"]
    assert made.column("days") == ["4", "14"]


def test_a_deferral_past_or_far_off_is_left_out():
    made = coming_due(
        [deferral(pay_on=date(2026, 1, 1)), deferral(pay_on=date(2026, 9, 1))], AS_OF
    )
    assert made.is_empty
    assert "0 to pay" in made.notes[0]
