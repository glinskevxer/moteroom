from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.press.bale import Bale
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.storage.book import Book
from moteroom.storage.lots import BaleRepository, LotRepository
from moteroom.storage.producers import ProducerRepository
from moteroom.storage.tickets import TicketRepository

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 42)


def run(**overrides: Any) -> GinRun:
    fields: dict[str, Any] = {
        "lot": LOT,
        "ginned_on": date(2025, 10, 16),
        "tickets": (1, 2),
        "seed_cotton": Weight(42_400),
        "lint": Weight(14_900),
        "seed": Weight(23_600),
        "motes": Weight(2_600),
    }
    fields.update(overrides)
    return GinRun(**fields)


def bale(number: int, **overrides: Any) -> Bale:
    fields: dict[str, Any] = {
        "bale_id": BaleId.build(SEASON, GIN, number),
        "lot": LOT,
        "pressed_on": date(2025, 10, 16),
        "gross": Weight(538),
        "tare": Weight(23),
        "moisture": Decimal("6.4"),
    }
    fields.update(overrides)
    return Bale(**fields)


@pytest.fixture()
def book():
    with Book.open() as opened:
        ProducerRepository(opened.connection).add(Producer("BLYTHE", "Blythe Farms"))
        tickets = TicketRepository(opened.connection)
        for number in (1, 2):
            tickets.add(
                ModuleTicket(
                    number=number,
                    module=ModuleId(f"HW-{number:06d}"),
                    producer="BLYTHE",
                    farm="3312",
                    weighed_on=date(2025, 10, 14),
                    gross=Weight(38_400),
                    tare=Weight(17_200),
                    moisture=Decimal("9.4"),
                )
            )
        yield opened


def test_a_lot_saves_with_its_tickets(book):
    lots = LotRepository(book.connection)
    lots.add(run())
    read = lots.get(LOT)
    assert read == run()
    assert read.tickets == (1, 2)


def test_a_lot_nobody_ginned(book):
    with pytest.raises(NotFoundError):
        LotRepository(book.connection).get(LOT)


def test_the_same_lot_twice_is_refused(book):
    lots = LotRepository(book.connection)
    lots.add(run())
    with pytest.raises(ConflictError):
        lots.add(run())


def test_a_lot_naming_a_ticket_nobody_wrote_is_refused(book):
    with pytest.raises(ConflictError):
        LotRepository(book.connection).add(run(tickets=(1, 9)))


def test_lots_come_back_in_number_order(book):
    lots = LotRepository(book.connection)
    lots.add(run(lot=LotId(SEASON, 43)))
    lots.add(run())
    assert [r.lot.number for r in lots.for_season(SEASON)] == [42, 43]
    assert lots.next_number(SEASON) == 44


def test_a_lot_can_be_closed(book):
    lots = LotRepository(book.connection)
    lots.add(run())
    assert not lots.is_closed(LOT)
    lots.close(LOT)
    assert lots.is_closed(LOT)


def test_closing_a_lot_nobody_ginned(book):
    lots = LotRepository(book.connection)
    with pytest.raises(NotFoundError):
        lots.close(LOT)
    with pytest.raises(NotFoundError):
        lots.is_closed(LOT)


def test_a_bale_saves_against_its_lot(book):
    LotRepository(book.connection).add(run())
    bales = BaleRepository(book.connection)
    bales.add(bale(1))
    assert bales.get(bale(1).bale_id) == bale(1)
    assert [b.number for b in bales.for_lot(LOT)] == [1]


def test_a_bale_for_a_lot_nobody_ginned_is_refused(book):
    with pytest.raises(ConflictError):
        BaleRepository(book.connection).add(bale(1))


def test_the_same_bale_twice_is_refused(book):
    LotRepository(book.connection).add(run())
    bales = BaleRepository(book.connection)
    bales.add(bale(1))
    with pytest.raises(ConflictError):
        bales.add(bale(1))


def test_a_bale_nobody_pressed(book):
    with pytest.raises(NotFoundError):
        BaleRepository(book.connection).get(BaleId.build(SEASON, GIN, 9))


def test_the_season_lint_adds_the_bales_up(book):
    LotRepository(book.connection).add(run())
    bales = BaleRepository(book.connection)
    bales.add(bale(1))
    bales.add(bale(2, gross=Weight(548)))
    assert bales.lint(SEASON) == Weight(515 + 525)


def test_the_press_counter_rebuilds_off_the_book(book):
    LotRepository(book.connection).add(run())
    bales = BaleRepository(book.connection)
    bales.add(bale(7))
    press = bales.press(SEASON, GIN)
    assert press.next_number == 8
    assert len(press) == 1
