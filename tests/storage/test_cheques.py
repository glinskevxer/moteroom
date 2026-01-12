from datetime import date

import pytest

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.receiving.party import Producer
from moteroom.settlement.cheque import Cheque
from moteroom.storage.book import Book
from moteroom.storage.cheques import ChequeRepository
from moteroom.storage.producers import ProducerRepository

SEASON = Season(2025)
ISSUED = date(2026, 2, 3)


def cheque(number: str = "1001", payee: str = "BLYTHE") -> Cheque:
    return Cheque(number, payee, Money.parse("10885.72"), ISSUED)


@pytest.fixture()
def cheques():
    with Book.open() as book:
        people = ProducerRepository(book.connection)
        people.add(Producer("BLYTHE", "Blythe Farms"))
        people.add(Producer("MERRITT", "Merritt"))
        yield ChequeRepository(book.connection)


def test_a_cheque_saves_and_reads_back(cheques):
    cheques.issue(cheque(), SEASON)
    assert cheques.get("1001") == cheque()


def test_a_number_is_used_once(cheques):
    cheques.issue(cheque(), SEASON)
    with pytest.raises(ConflictError):
        cheques.issue(cheque(), SEASON)


def test_a_cheque_to_a_producer_nobody_added(cheques):
    with pytest.raises(ConflictError):
        cheques.issue(cheque(payee="GHOST"), SEASON)


def test_a_cheque_nobody_wrote(cheques):
    with pytest.raises(NotFoundError):
        cheques.get("1001")


def test_clearing_and_voiding_hold(cheques):
    cheques.issue(cheque(), SEASON)
    cheques.issue(cheque(number="1002", payee="MERRITT"), SEASON)
    cheques.clear("1001", date(2026, 2, 10))
    cheques.void("1002", date(2026, 2, 10), "lost")
    assert cheques.get("1001").cleared_on == date(2026, 2, 10)
    assert cheques.get("1002").is_voided
    assert cheques.get("1002").void_reason == "lost"


def test_a_cleared_cheque_cannot_be_voided(cheques):
    cheques.issue(cheque(), SEASON)
    cheques.clear("1001", date(2026, 2, 10))
    with pytest.raises(ValidationError):
        cheques.void("1001", date(2026, 2, 11), "lost")


def test_the_register_rebuilds_off_the_book(cheques):
    cheques.issue(cheque(), SEASON)
    cheques.issue(cheque(number="1002", payee="MERRITT"), SEASON)
    register = cheques.register(SEASON)
    assert len(register) == 2
    assert register.next_number() == "1003"
    assert register.owed() == Money.parse("21771.44")


def test_cheques_read_back_per_payee(cheques):
    cheques.issue(cheque(), SEASON)
    assert [one.number for one in cheques.for_payee(SEASON, "BLYTHE")] == ["1001"]
    assert cheques.for_payee(SEASON, "MERRITT") == []
