import pytest

from moteroom.storage.book import Book
from moteroom.storage.cards import CardRepository
from moteroom.storage.registry import Repositories
from moteroom.storage.tickets import TicketRepository


@pytest.fixture()
def repos():
    with Book.open() as book:
        yield Repositories(book.connection)


def test_the_registry_holds_one_of_each(repos):
    assert isinstance(repos.tickets, TicketRepository)
    assert isinstance(repos.cards, CardRepository)
    assert len(repos.names()) == 17


def test_every_repository_shares_the_one_connection(repos):
    assert repos.tickets.connection is repos.bales.connection
    assert repos.cards.connection is repos.connection


def test_the_registry_names_what_it_holds(repos):
    names = repos.names()
    assert "tickets" in names
    assert "connection" not in names
    assert names == sorted(names)


def test_a_write_through_one_repository_is_seen_by_another(repos):
    from moteroom.receiving.party import Producer

    repos.producers.add(Producer("BLYTHE", "Blythe Farms"))
    assert repos.producers.has("BLYTHE")
    assert repos.farms.for_producer("BLYTHE") == []
