from datetime import date
from decimal import Decimal

import pytest

from moteroom.core.season import Season
from moteroom.service import closing
from moteroom.storage.book import Book

SEASON = Season(2025)


@pytest.fixture()
def book():
    with Book.open() as opened:
        yield opened


def test_an_empty_season_closes_because_nothing_is_outstanding(book):
    made = closing.check(book, SEASON)
    assert made.can_close
    assert str(made) == "2025/26 can close"
    assert len(made.checks) == 5


def test_every_check_has_a_name(book):
    made = closing.check(book, SEASON)
    for name in (
        "modules ginned",
        "bales classed",
        "lots reconcile",
        "bales placed",
        "producers settled",
    ):
        assert made.named(name).passed


def test_a_check_nobody_has(book):
    with pytest.raises(KeyError):
        closing.check(book, SEASON).named("the weather")


def test_a_check_prints_its_line(book):
    assert str(closing.check(book, SEASON).named("modules ginned")).startswith("ok  ")


def test_a_module_left_in_the_yard_holds_the_season_open(book):
    from moteroom.core.ids import ModuleId
    from moteroom.core.weight import Weight
    from moteroom.receiving.party import Producer
    from moteroom.receiving.ticket import ModuleTicket
    from moteroom.storage.producers import ProducerRepository
    from moteroom.storage.tickets import TicketRepository

    ProducerRepository(book.connection).add(Producer("BLYTHE", "Blythe Farms"))
    TicketRepository(book.connection).add(
        ModuleTicket(
            number=1,
            module=ModuleId("HW-000001"),
            producer="BLYTHE",
            farm="3312",
            weighed_on=date(2025, 10, 14),
            gross=Weight(38_400),
            tare=Weight(17_200),
            moisture=Decimal("9.4"),
        )
    )
    made = closing.check(book, SEASON)
    assert not made.can_close
    assert "1 still in the yard" in made.named("modules ginned").detail
    assert "BLYTHE not settled" in made.named("producers settled").detail
    assert len(made.outstanding) == 2
    assert "2 things outstanding" in str(made)
