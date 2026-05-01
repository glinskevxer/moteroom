from datetime import date
from decimal import Decimal

import pytest

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.ids import ModuleId
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.byproduct import MOTES, TRASH, Sale
from moteroom.receiving.freight import Haul, Rate
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.storage.book import Book
from moteroom.storage.registry import Repositories

SEASON = Season(2025)
DAY = date(2025, 10, 14)


def rate(hauler: str = "TRUXTON") -> Rate:
    return Rate(
        hauler=hauler,
        per_module=Money.parse("42.00"),
        per_mile=Money.parse("3.10"),
        minimum=Money.parse("250.00"),
    )


@pytest.fixture()
def repos():
    with Book.open() as book:
        made = Repositories(book.connection)
        made.producers.add(Producer("BLYTHE", "Blythe Farms"))
        for number in (1, 2, 3):
            made.tickets.add(
                ModuleTicket(
                    number=number,
                    module=ModuleId(f"HW-{number:06d}"),
                    producer="BLYTHE",
                    farm="3312",
                    weighed_on=DAY,
                    gross=Weight(38_400),
                    tare=Weight(17_200),
                    moisture=Decimal("9.4"),
                )
            )
        yield made


def test_a_hauler_posts_once_a_season(repos):
    repos.freight.post(SEASON, rate())
    with pytest.raises(ConflictError):
        repos.freight.post(SEASON, rate())
    assert [one.hauler for one in repos.freight.rates(SEASON)] == ["TRUXTON"]


def test_a_hauler_nobody_posted(repos):
    with pytest.raises(NotFoundError):
        repos.freight.rate(SEASON, "TRUXTON")


def test_a_load_saves_with_its_tickets(repos):
    repos.freight.post(SEASON, rate())
    repos.freight.haul(SEASON, Haul("TRUXTON", DAY, (1, 2), 18))
    loads = repos.freight.hauls(SEASON)
    assert loads[0].tickets == (1, 2)
    assert loads[0].miles == 18


def test_a_load_from_a_hauler_with_no_rates(repos):
    with pytest.raises(NotFoundError):
        repos.freight.haul(SEASON, Haul("TRUXTON", DAY, (1,), 18))


def test_a_load_naming_a_ticket_nobody_wrote(repos):
    repos.freight.post(SEASON, rate())
    with pytest.raises(ConflictError):
        repos.freight.haul(SEASON, Haul("TRUXTON", DAY, (9,), 18))
    assert repos.freight.hauls(SEASON) == []


def test_the_ledger_rebuilds_and_prices(repos):
    repos.freight.post(SEASON, rate())
    repos.freight.haul(SEASON, Haul("TRUXTON", DAY, (1, 2), 18))
    ledger = repos.freight.ledger(SEASON)
    assert len(ledger) == 1
    assert ledger.owed() == Money.parse("250.00")
    assert ledger.for_tickets([1]) == Money.parse("125.00")


def test_an_empty_season_has_no_freight(repos):
    assert len(repos.freight.ledger(SEASON)) == 0
    assert repos.freight.hauls(SEASON) == []


def test_a_sale_saves_and_reads_back(repos):
    sale = Sale(MOTES, DAY, Weight(24_000), Money.parse("180.00"), "MILL")
    repos.byproducts.sell(SEASON, sale)
    assert repos.byproducts.sales(SEASON) == [sale]


def test_the_byproduct_ledger_rebuilds(repos):
    repos.byproducts.sell(
        SEASON, Sale(MOTES, DAY, Weight(24_000), Money.parse("180.00"), "MILL")
    )
    repos.byproducts.sell(
        SEASON, Sale(TRASH, DAY, Weight(24_000), Money.parse("-22.50"), "FEEDLOT")
    )
    ledger = repos.byproducts.ledger(SEASON)
    assert ledger.proceeds() == Money.parse("1890.00")
    assert len(ledger.disposals()) == 1


def test_two_seasons_of_byproducts_are_kept_apart(repos):
    repos.byproducts.sell(
        SEASON, Sale(MOTES, DAY, Weight(24_000), Money.parse("180.00"), "MILL")
    )
    assert repos.byproducts.sales(Season(2026)) == []
    assert len(repos.byproducts.ledger(Season(2026))) == 0
