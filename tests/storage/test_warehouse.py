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
from moteroom.storage.warehouse import OrderRepository, ReceiptRepository
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.shipping import ShippingOrder

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 42)


def receipt(number: int, **overrides: Any) -> Receipt:
    fields: dict[str, Any] = {
        "number": f"MW{number:08d}",
        "warehouse": "MW14",
        "bale_id": BaleId.build(SEASON, GIN, number),
        "received_on": date(2025, 10, 20),
        "net": Weight(515),
        "holder": "BLYTHE",
    }
    fields.update(overrides)
    return Receipt(**fields)


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
                    bale_id=BaleId.build(SEASON, GIN, number),
                    lot=LOT,
                    pressed_on=date(2025, 10, 16),
                    gross=Weight(538),
                    tare=Weight(23),
                    moisture=Decimal("6.4"),
                )
            )
        yield opened


def test_a_receipt_issues_and_reads_back(book):
    receipts = ReceiptRepository(book.connection)
    receipts.issue(receipt(1))
    assert receipts.get("MW00000001") == receipt(1)


def test_a_receipt_for_a_bale_nobody_pressed_is_refused(book):
    receipts = ReceiptRepository(book.connection)
    with pytest.raises(ConflictError):
        receipts.issue(receipt(9))


def test_a_second_live_receipt_on_one_bale_is_refused(book):
    receipts = ReceiptRepository(book.connection)
    receipts.issue(receipt(1))
    with pytest.raises(ConflictError):
        receipts.issue(receipt(2, bale_id=BaleId.build(SEASON, GIN, 1)))


def test_a_receipt_nobody_issued(book):
    with pytest.raises(NotFoundError):
        ReceiptRepository(book.connection).get("MW00000009")


def test_releasing_updates_the_row_in_place(book):
    receipts = ReceiptRepository(book.connection)
    receipts.issue(receipt(1))
    released = receipts.release("MW00000001", date(2025, 12, 1), "CALCOT")
    assert released.holder == "CALCOT"
    assert receipts.get("MW00000001").released_on == date(2025, 12, 1)
    assert receipts.for_bale(BaleId.build(SEASON, GIN, 1)) is None


def test_releasing_twice_is_refused(book):
    receipts = ReceiptRepository(book.connection)
    receipts.issue(receipt(1))
    receipts.release("MW00000001", date(2025, 12, 1), "CALCOT")
    with pytest.raises(ConflictError):
        receipts.release("MW00000001", date(2025, 12, 2), "CALCOT")


def test_outstanding_can_be_asked_per_house(book):
    receipts = ReceiptRepository(book.connection)
    receipts.issue(receipt(1))
    receipts.issue(receipt(2, warehouse="MW15"))
    assert [r.number for r in receipts.outstanding()] == ["MW00000001", "MW00000002"]
    assert [r.number for r in receipts.outstanding("MW15")] == ["MW00000002"]


def test_a_register_rebuilds_off_the_book(book):
    receipts = ReceiptRepository(book.connection)
    receipts.issue(receipt(1))
    receipts.issue(receipt(2))
    receipts.release("MW00000002", date(2025, 12, 1), "CALCOT")
    register = receipts.register("MW14")
    assert [r.number for r in register.outstanding()] == ["MW00000001"]


def test_an_order_saves_with_its_receipts_in_order(book):
    receipts = ReceiptRepository(book.connection)
    receipts.issue(receipt(1))
    receipts.issue(receipt(2))
    orders = OrderRepository(book.connection)
    order = ShippingOrder(
        number="SO000141",
        warehouse="MW14",
        ordered_on=date(2026, 1, 12),
        buyer="CALCOT",
        receipts=("MW00000002", "MW00000001"),
    )
    orders.add(order)
    assert orders.get("SO000141") == order
    assert [o.number for o in orders.open_orders()] == ["SO000141"]


def test_an_order_naming_a_receipt_nobody_issued_is_refused(book):
    orders = OrderRepository(book.connection)
    with pytest.raises(ConflictError):
        orders.add(
            ShippingOrder(
                number="SO000141",
                warehouse="MW14",
                ordered_on=date(2026, 1, 12),
                buyer="CALCOT",
                receipts=("MW00000009",),
            )
        )


def test_an_order_nobody_wrote(book):
    with pytest.raises(NotFoundError):
        OrderRepository(book.connection).get("SO000141")


def test_a_released_receipt_can_still_be_found_for_its_bale(book):
    receipts = ReceiptRepository(book.connection)
    receipts.issue(receipt(1))
    tag = BaleId.build(SEASON, GIN, 1)
    assert receipts.last_released(tag) is None
    receipts.release("MW00000001", date(2026, 1, 12), "CALCOT")
    found = receipts.last_released(tag)
    assert found is not None
    assert found.number == "MW00000001"


def test_a_bale_that_never_left_has_no_released_receipt(book):
    receipts = ReceiptRepository(book.connection)
    receipts.issue(receipt(1))
    assert receipts.last_released(BaleId.build(SEASON, GIN, 2)) is None
