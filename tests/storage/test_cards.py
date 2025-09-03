from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.press.bale import Bale
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.storage.book import Book
from moteroom.storage.cards import CardRepository
from moteroom.storage.lots import BaleRepository, LotRepository
from moteroom.storage.producers import ProducerRepository
from moteroom.storage.tickets import TicketRepository

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 42)


def card(number: int, **overrides: Any) -> ClassingRecord:
    fields: dict[str, Any] = {
        "bale_id": BaleId.build(SEASON, GIN, number),
        "classed_on": date(2025, 10, 22),
        "office": "MEMPHIS",
        "micronaire": Micronaire(Decimal("4.3")),
        "staple": Staple(36),
        "strength": Strength(Decimal("29.4")),
        "uniformity": Uniformity(Decimal("81.2")),
        "color": ColorGrade(31),
        "leaf": LeafGrade(3),
        "trash": Trash(Decimal("0.42")),
    }
    fields.update(overrides)
    return ClassingRecord(**fields)


@pytest.fixture()
def cards():
    with Book.open() as book:
        ProducerRepository(book.connection).add(Producer("BLYTHE", "Blythe Farms"))
        tickets = TicketRepository(book.connection)
        tickets.add(
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
        LotRepository(book.connection).add(
            GinRun(
                lot=LOT,
                ginned_on=date(2025, 10, 16),
                tickets=(1,),
                seed_cotton=Weight(21_200),
                lint=Weight(7_400),
                seed=Weight(11_800),
                motes=Weight(1_300),
            )
        )
        bales = BaleRepository(book.connection)
        for number in (1, 2):
            bales.add(
                Bale(
                    bale_id=BaleId.build(SEASON, GIN, number),
                    lot=LOT,
                    pressed_on=date(2025, 10, 16),
                    gross=Weight(538),
                    tare=Weight(23),
                    moisture=Decimal("6.4"),
                )
            )
        yield CardRepository(book.connection)


def test_a_card_saves_and_reads_back_whole(cards):
    cards.add(card(1, extraneous=(Extraneous.parse("B2"),)))
    read = cards.get(BaleId.build(SEASON, GIN, 1))
    assert read == card(1, extraneous=(Extraneous.parse("B2"),))
    assert read.codes == ("B2",)


def test_a_card_nobody_filed(cards):
    with pytest.raises(NotFoundError):
        cards.get(BaleId.build(SEASON, GIN, 1))
    assert not cards.has(BaleId.build(SEASON, GIN, 1))


def test_a_card_for_a_bale_nobody_pressed_is_refused(cards):
    with pytest.raises(ConflictError):
        cards.add(card(9))


def test_the_same_bale_twice_is_refused(cards):
    cards.add(card(1))
    with pytest.raises(ConflictError):
        cards.add(card(1))


def test_a_corrected_card_takes_its_findings_with_it(cards):
    cards.add(card(1, extraneous=(Extraneous.parse("B2"),)))
    cards.replace(card(1, leaf=LeafGrade(5)))
    read = cards.get(BaleId.build(SEASON, GIN, 1))
    assert read.codes == ()
    assert read.leaf.grade == 5


def test_correcting_a_card_nobody_filed(cards):
    with pytest.raises(NotFoundError):
        cards.replace(card(1))


def test_a_season_loads_back_into_a_classing_book(cards):
    cards.add(card(1))
    cards.add(card(2))
    loaded = cards.book(SEASON)
    assert len(loaded) == 2


def test_the_unclassed_bales_are_the_ones_with_no_card(cards):
    cards.add(card(1))
    waiting = cards.unclassed(SEASON)
    assert [b.bale_number for b in waiting] == [2]


def test_a_card_and_its_findings_go_in_together(cards):
    with pytest.raises(ConflictError):
        cards.add(card(9, extraneous=(Extraneous.parse("B2"),)))
    assert cards.for_season(SEASON) == []


def test_a_refused_card_names_the_bale(cards):
    cards.add(card(1))
    with pytest.raises(ConflictError) as caught:
        cards.add(card(1))
    assert caught.value.key == str(BaleId.build(SEASON, GIN, 1))
