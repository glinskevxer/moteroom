from datetime import date
from decimal import Decimal

import pytest

from moteroom.core.ids import LotId, ModuleId
from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.service.producer import standing
from moteroom.settlement.statement import Advance
from moteroom.storage.book import Book
from moteroom.storage.registry import Repositories

SEASON = Season(2025)
LOT = LotId(SEASON, 1)


@pytest.fixture()
def book():
    with Book.open() as opened:
        repos = Repositories(opened.connection)
        repos.producers.add(Producer("BLYTHE", "Blythe Farms"))
        repos.producers.add(Producer("MERRITT", "Merritt"))
        for number, producer, moisture in ((1, "BLYTHE", "7.5"), (2, "MERRITT", "12.0")):
            repos.tickets.add(
                ModuleTicket(
                    number=number,
                    module=ModuleId(f"HW-{number:06d}"),
                    producer=producer,
                    farm="3312",
                    weighed_on=date(2025, 10, 14),
                    gross=Weight(38_400),
                    tare=Weight(17_200),
                    moisture=Decimal(moisture),
                )
            )
        repos.lots.add(
            GinRun(
                lot=LOT,
                ginned_on=date(2025, 10, 16),
                tickets=(1, 2),
                seed_cotton=Weight(42_400),
                lint=Weight(14_900),
                seed=Weight(23_600),
                motes=Weight(2_600),
            )
        )
        yield opened


def test_a_producer_reads_their_own_numbers(book):
    made = standing(book, SEASON, "BLYTHE")
    assert made.modules == 1
    assert made.seed_cotton == Weight(21_200)
    assert made.average_module == Weight(21_200)
    assert made.lots == ("2025-0001",)
    assert str(made).startswith("BLYTHE 2025/26")


def test_a_wet_producer_shows_the_water(book):
    dry = standing(book, SEASON, "BLYTHE")
    wet = standing(book, SEASON, "MERRITT")
    assert dry.wet_share == Decimal("0.00")
    assert wet.wet_share > Decimal("4.00")


def test_the_wet_producer_earns_less_lint_off_the_same_scale_weight(book):
    assert standing(book, SEASON, "MERRITT").lint < standing(book, SEASON, "BLYTHE").lint


def test_the_turnout_is_stated_against_the_plant(book):
    made = standing(book, SEASON, "BLYTHE")
    assert made.plant_turnout == Decimal("35.14")
    assert made.against_the_plant == made.turnout - made.plant_turnout


def test_a_producer_with_nothing_in_divides_by_nothing_safely(book):
    Repositories(book.connection).producers.add(Producer("COLE", "Cole"))
    made = standing(book, SEASON, "COLE")
    assert made.modules == 0
    assert made.average_module.is_zero
    assert made.wet_share == Decimal("0.00")
    assert made.lots == ()
    assert dict(made.lines())["lots"] == "none"


def test_the_money_lines_read_off_the_book(book):
    repos = Repositories(book.connection)
    repos.advances.add(
        SEASON, "BLYTHE", Advance("A-114", Money.parse("500.00")), date(2025, 11, 3)
    )
    made = standing(book, SEASON, "BLYTHE")
    assert made.advanced == Money.parse("500.00")
    assert not made.settled
    assert made.net.is_zero
    assert made.cheques == 0


def test_the_lines_come_out_in_the_order_somebody_asks(book):
    names = [name for name, _ in standing(book, SEASON, "BLYTHE").lines()]
    assert names[0] == "producer"
    assert names[-1] == "cheques"
    assert "turnout" in names
