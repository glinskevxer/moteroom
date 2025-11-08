from datetime import date
from decimal import Decimal

import pytest

from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId
from moteroom.core.money import CentsPerPound
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.press.bale import Bale
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.service import inventory
from moteroom.settlement.contract import Contract
from moteroom.storage.book import Book
from moteroom.storage.contracts import ContractRepository
from moteroom.storage.lots import BaleRepository, LotRepository
from moteroom.storage.producers import ProducerRepository
from moteroom.storage.tickets import TicketRepository
from moteroom.storage.warehouse import ReceiptRepository
from moteroom.warehouse.receipt import Receipt

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 42)


def tag(number: int) -> BaleId:
    return BaleId.build(SEASON, GIN, number)


@pytest.fixture()
def book():
    with Book.open() as opened:
        ProducerRepository(opened.connection).add(Producer("BLYTHE", "Blythe Farms"))
        TicketRepository(opened.connection).add(
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
        LotRepository(opened.connection).add(
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
        bales = BaleRepository(opened.connection)
        for number in (1, 2, 3):
            bales.add(
                Bale(
                    bale_id=tag(number),
                    lot=LOT,
                    pressed_on=date(2025, 10, 16),
                    gross=Weight(538),
                    tare=Weight(23),
                    moisture=Decimal("6.4"),
                )
            )
        yield opened


def receipt(book: Book, number: int) -> Receipt:
    made = Receipt(
        number=f"MW{number:08d}",
        warehouse="MW14",
        bale_id=tag(number),
        received_on=date(2025, 10, 20),
        net=Weight(515),
        holder="BLYTHE",
    )
    ReceiptRepository(book.connection).issue(made)
    return made


def test_a_bale_with_no_receipt_is_still_at_the_gin(book):
    taken = inventory.take(book, SEASON)
    assert taken.counts()[inventory.AT_THE_GIN] == 3
    assert taken.bales == 3
    assert taken.net == Weight(1_545)
    assert taken.balances


def test_a_receipted_bale_is_in_store(book):
    receipt(book, 1)
    taken = inventory.take(book, SEASON)
    assert taken.counts()[inventory.IN_STORE] == 1
    assert taken.weight_at(inventory.IN_STORE) == Weight(515)
    assert "receipt MW00000001" in taken.where(inventory.IN_STORE)[0].detail


def test_a_released_receipt_reads_as_shipped(book):
    receipt(book, 1)
    ReceiptRepository(book.connection).release("MW00000001", date(2026, 1, 12), "CALCOT")
    taken = inventory.take(book, SEASON)
    assert taken.counts()[inventory.SHIPPED] == 1


def test_a_delivered_bale_reads_as_delivered(book):
    contracts = ContractRepository(book.connection)
    contracts.add(
        Contract(
            number="C000141",
            buyer="CALCOT",
            signed_on=date(2025, 8, 2),
            bales=1,
            delivery_from=date(2025, 11, 1),
            delivery_to=date(2026, 1, 31),
            price=CentsPerPound.of("68.50"),
        ),
        SEASON,
    )
    contracts.deliver("C000141", tag(1), date(2025, 12, 1), CentsPerPound.of("68.50"))
    taken = inventory.take(book, SEASON)
    assert taken.counts()[inventory.DELIVERED] == 1
    assert "against C000141" in taken.where(inventory.DELIVERED)[0].detail
    assert taken.balances


def test_a_delivered_bale_with_a_live_receipt_does_not_balance(book):
    receipt(book, 1)
    contracts = ContractRepository(book.connection)
    contracts.add(
        Contract(
            number="C000141",
            buyer="CALCOT",
            signed_on=date(2025, 8, 2),
            bales=1,
            delivery_from=date(2025, 11, 1),
            delivery_to=date(2026, 1, 31),
            price=CentsPerPound.of("68.50"),
        ),
        SEASON,
    )
    contracts.deliver("C000141", tag(1), date(2025, 12, 1), CentsPerPound.of("68.50"))
    taken = inventory.take(book, SEASON)
    assert not taken.balances
    assert "outstanding" in taken.orphans[0][1]


def test_an_inventory_prints_where_things_are(book):
    receipt(book, 1)
    assert str(inventory.take(book, SEASON)) == "2 at the gin, 1 in store"


def test_an_empty_season_says_nothing_was_pressed(book):
    assert str(inventory.take(book, Season(2026))) == "nothing pressed"
