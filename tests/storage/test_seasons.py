from datetime import date
from decimal import Decimal

import pytest

from moteroom.core.ids import LotId, ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.storage.book import Book
from moteroom.storage.registry import Repositories

SEASON = Season(2025)


@pytest.fixture()
def repos():
    with Book.open() as book:
        made = Repositories(book.connection)
        made.producers.add(Producer("BLYTHE", "Blythe Farms"))
        yield made


def ticket(number: int, season: Season) -> ModuleTicket:
    return ModuleTicket(
        number=number,
        module=ModuleId(f"HW-{number:06d}"),
        producer="BLYTHE",
        farm="3312",
        weighed_on=date(season.year, 10, 14),
        gross=Weight(38_400),
        tare=Weight(17_200),
        moisture=Decimal("9.4"),
    )


def test_an_empty_book_holds_no_seasons(repos):
    assert repos.seasons.years() == []
    assert repos.seasons.all() == []
    assert repos.seasons.latest() is None


def test_a_ticket_puts_its_season_in_the_book(repos):
    repos.tickets.add(ticket(1, SEASON))
    assert repos.seasons.years() == [SEASON]
    assert repos.seasons.latest() == SEASON


def test_two_seasons_come_back_oldest_first(repos):
    repos.tickets.add(ticket(1, SEASON))
    repos.tickets.add(ticket(1, Season(2026)))
    assert repos.seasons.years() == [SEASON, Season(2026)]
    assert repos.seasons.latest() == Season(2026)


def test_what_a_season_holds_is_counted(repos):
    repos.tickets.add(ticket(1, SEASON))
    repos.lots.add(
        GinRun(
            lot=LotId(SEASON, 1),
            ginned_on=date(2025, 10, 16),
            tickets=(1,),
            seed_cotton=Weight(21_200),
            lint=Weight(7_400),
            seed=Weight(11_800),
            motes=Weight(1_300),
        )
    )
    held = repos.seasons.held(SEASON)
    assert held.tickets == 1
    assert held.lots == 1
    assert held.bales == 0
    assert not held.is_empty
    assert not held.is_settled
    assert "1 tickets, 1 lots" in str(held)


def test_a_season_nobody_put_anything_in(repos):
    held = repos.seasons.held(Season(2030))
    assert held.is_empty
    assert str(held) == "2030/31 nothing in it"


def test_the_seasons_are_listed_with_their_counts(repos):
    repos.tickets.add(ticket(1, SEASON))
    listed = repos.seasons.all()
    assert [one.season for one in listed] == [SEASON]
    assert listed[0].tickets == 1
