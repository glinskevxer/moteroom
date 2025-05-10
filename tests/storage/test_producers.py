from decimal import Decimal

import pytest

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.receiving.party import Farm, Producer
from moteroom.storage.book import Book
from moteroom.storage.producers import FarmRepository, ProducerRepository


@pytest.fixture()
def book():
    with Book.open() as opened:
        yield opened


def test_a_producer_saves_and_reads_back(book):
    people = ProducerRepository(book.connection)
    people.add(Producer("BLYTHE", "Blythe Farms"))
    assert people.get("BLYTHE").name == "Blythe Farms"
    assert people.exists("BLYTHE")
    assert people.count() == 1


def test_a_producer_nobody_added(book):
    people = ProducerRepository(book.connection)
    with pytest.raises(NotFoundError):
        people.get("BLYTHE")
    assert not people.exists("BLYTHE")


def test_the_same_code_twice_is_refused(book):
    people = ProducerRepository(book.connection)
    people.add(Producer("BLYTHE", "Blythe Farms"))
    with pytest.raises(ConflictError):
        people.add(Producer("BLYTHE", "Blythe Brothers"))


def test_a_producer_can_be_renamed(book):
    people = ProducerRepository(book.connection)
    people.add(Producer("BLYTHE", "Blythe Farms"))
    people.rename("BLYTHE", "Blythe Brothers")
    assert people.get("BLYTHE").name == "Blythe Brothers"


def test_renaming_somebody_who_is_not_there(book):
    with pytest.raises(NotFoundError):
        ProducerRepository(book.connection).rename("BLYTHE", "Blythe Brothers")


def test_producers_come_back_in_code_order(book):
    people = ProducerRepository(book.connection)
    people.add(Producer("MERRITT", "Merritt"))
    people.add(Producer("BLYTHE", "Blythe Farms"))
    assert [p.code for p in people.all()] == ["BLYTHE", "MERRITT"]


def test_a_farm_saves_against_its_producer(book):
    ProducerRepository(book.connection).add(Producer("BLYTHE", "Blythe Farms"))
    farms = FarmRepository(book.connection)
    farms.add(Farm("3312", "1140", "BLYTHE", Decimal("284.50")))
    assert farms.get("3312", "1140").acres == Decimal("284.50")
    assert [f.key for f in farms.all()] == ["3312-1140"]


def test_a_farm_for_a_producer_nobody_added(book):
    farms = FarmRepository(book.connection)
    with pytest.raises(ConflictError):
        farms.add(Farm("3312", "1140", "GHOST", Decimal("10.00")))


def test_the_same_farm_and_tract_twice_is_refused(book):
    ProducerRepository(book.connection).add(Producer("BLYTHE", "Blythe Farms"))
    farms = FarmRepository(book.connection)
    farms.add(Farm("3312", "1140", "BLYTHE", Decimal("284.50")))
    with pytest.raises(ConflictError):
        farms.add(Farm("3312", "1140", "BLYTHE", Decimal("10.00")))


def test_a_farm_nobody_added(book):
    with pytest.raises(NotFoundError):
        FarmRepository(book.connection).get("3312", "1140")


def test_farms_and_acres_come_back_per_producer(book):
    people = ProducerRepository(book.connection)
    people.add(Producer("BLYTHE", "Blythe Farms"))
    people.add(Producer("MERRITT", "Merritt"))
    farms = FarmRepository(book.connection)
    farms.add(Farm("3312", "1140", "BLYTHE", Decimal("284.50")))
    farms.add(Farm("3312", "1141", "BLYTHE", Decimal("120.25")))
    farms.add(Farm("4410", "2200", "MERRITT", Decimal("64.00")))
    assert [f.key for f in farms.for_producer("BLYTHE")] == ["3312-1140", "3312-1141"]
    assert farms.acres_for("BLYTHE") == Decimal("404.75")
    assert farms.acres_for("NOBODY") == Decimal("0.00")
