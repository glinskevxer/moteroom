from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.receiving.party import Producer
from moteroom.settlement.statement import Advance, Statement
from moteroom.storage.book import Book
from moteroom.storage.producers import ProducerRepository
from moteroom.storage.settlement import AdvanceRepository, StatementRepository

SEASON = Season(2025)


def statement(**overrides: Any) -> Statement:
    fields: dict[str, Any] = {
        "producer": "BLYTHE",
        "season": SEASON,
        "bales": 44,
        "lint": Weight(22_300),
        "lint_proceeds": Money.parse("11648.60"),
        "gin_charges": Money.parse("3263.00"),
        "seed_credit": Money.parse("2500.12"),
    }
    fields.update(overrides)
    return Statement(**fields)


@pytest.fixture()
def book():
    with Book.open() as opened:
        people = ProducerRepository(opened.connection)
        people.add(Producer("BLYTHE", "Blythe Farms"))
        people.add(Producer("MERRITT", "Merritt"))
        yield opened


def test_a_statement_saves_and_reads_back(book):
    statements = StatementRepository(book.connection)
    statements.save(statement(), date(2026, 2, 3))
    read = statements.get(SEASON, "BLYTHE")
    assert read.net == statement().net
    assert statements.settled_on(SEASON, "BLYTHE") == date(2026, 2, 3)


def test_settling_the_same_producer_twice_is_refused(book):
    statements = StatementRepository(book.connection)
    statements.save(statement(), date(2026, 2, 3))
    with pytest.raises(ConflictError):
        statements.save(statement(), date(2026, 2, 4))


def test_a_statement_nobody_settled(book):
    statements = StatementRepository(book.connection)
    with pytest.raises(NotFoundError):
        statements.get(SEASON, "BLYTHE")
    with pytest.raises(NotFoundError):
        statements.settled_on(SEASON, "BLYTHE")


def test_a_statement_for_a_producer_nobody_added(book):
    with pytest.raises(ConflictError):
        StatementRepository(book.connection).save(statement(producer="GHOST"), date(2026, 2, 3))


def test_advances_are_picked_up_when_the_statement_loads(book):
    advances = AdvanceRepository(book.connection)
    advances.add(SEASON, "BLYTHE", Advance("A-114", Money.parse("5000.00")), date(2025, 11, 3))
    advances.add(SEASON, "BLYTHE", Advance("A-119", Money.parse("2000.00")), date(2025, 12, 3))
    statements = StatementRepository(book.connection)
    statements.save(statement(), date(2026, 2, 3))
    read = statements.get(SEASON, "BLYTHE")
    assert [a.reference for a in read.advances] == ["A-114", "A-119"]
    assert read.advanced == Money.parse("7000.00")
    assert read.net == statement().net - Money.parse("7000.00")


def test_the_same_advance_reference_twice_is_refused(book):
    advances = AdvanceRepository(book.connection)
    advances.add(SEASON, "BLYTHE", Advance("A-114", Money.parse("5000.00")), date(2025, 11, 3))
    with pytest.raises(ConflictError):
        advances.add(
            SEASON, "BLYTHE", Advance("A-114", Money.parse("10.00")), date(2025, 11, 4)
        )


def test_advances_are_kept_apart_by_producer(book):
    advances = AdvanceRepository(book.connection)
    advances.add(SEASON, "BLYTHE", Advance("A-114", Money.parse("5000.00")), date(2025, 11, 3))
    assert advances.total(SEASON, "BLYTHE") == Money.parse("5000.00")
    assert advances.total(SEASON, "MERRITT").is_zero
    assert advances.for_producer(SEASON, "MERRITT") == ()


def test_statements_come_back_in_producer_order(book):
    statements = StatementRepository(book.connection)
    statements.save(statement(producer="MERRITT"), date(2026, 2, 3))
    statements.save(statement(), date(2026, 2, 3))
    assert [s.producer for s in statements.for_season(SEASON)] == ["BLYTHE", "MERRITT"]


def test_an_advance_refused_by_a_constraint_names_the_reference(book):
    advances = AdvanceRepository(book.connection)
    advances.add(SEASON, "BLYTHE", Advance("A-114", Money.parse("5000.00")), date(2025, 11, 3))
    with pytest.raises(ConflictError) as caught:
        advances.add(SEASON, "BLYTHE", Advance("A-114", Money.parse("1.00")), date(2025, 11, 4))
    assert caught.value.key == "A-114"
