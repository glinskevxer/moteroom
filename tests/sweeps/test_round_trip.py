"""Every record saved and read back, compared against what went in.

A repository that drops a field does not fail. It reads back a record that
looks right and is missing the moisture, and the first person to notice is the
producer whose dry weight came out wrong in March. So every record type is
written and read and compared whole, field by field, rather than on the two
fields the repository's own test happened to check.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.byproduct import MOTES, Sale
from moteroom.ginning.run import GinRun
from moteroom.press.bale import Bale
from moteroom.receiving.freight import Haul, Rate
from moteroom.receiving.party import Farm, Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.settlement.cheque import Cheque
from moteroom.settlement.contract import Contract
from moteroom.settlement.statement import Advance, Statement
from moteroom.storage.book import Book
from moteroom.storage.rates import default_terms
from moteroom.storage.registry import Repositories
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.shipping import ShippingOrder

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 1)
TAG = BaleId.build(SEASON, GIN, 1)
DAY = date(2025, 10, 14)


def ticket() -> ModuleTicket:
    return ModuleTicket(
        number=1,
        module=ModuleId("HW-004181"),
        producer="BLYTHE",
        farm="3312",
        weighed_on=DAY,
        gross=Weight(38_417),
        tare=Weight(17_203),
        moisture=Decimal("9.7"),
        voids=None,
    )


def run() -> GinRun:
    return GinRun(
        lot=LOT,
        ginned_on=date(2025, 10, 16),
        tickets=(1,),
        seed_cotton=Weight(21_214),
        lint=Weight(7_403),
        seed=Weight(11_801),
        motes=Weight(1_307),
    )


def bale() -> Bale:
    return Bale(
        bale_id=TAG,
        lot=LOT,
        pressed_on=date(2025, 10, 16),
        gross=Weight(539),
        tare=Weight(23),
        moisture=Decimal("6.7"),
    )


def card() -> ClassingRecord:
    return ClassingRecord(
        bale_id=TAG,
        classed_on=date(2025, 10, 22),
        office="MEMPHIS",
        micronaire=Micronaire(Decimal("4.7")),
        staple=Staple(37),
        strength=Strength(Decimal("29.7")),
        uniformity=Uniformity(Decimal("81.7")),
        color=ColorGrade(31),
        leaf=LeafGrade(2),
        trash=Trash(Decimal("0.47")),
        extraneous=(Extraneous.parse("B2"), Extraneous.parse("G1")),
    )


def receipt() -> Receipt:
    return Receipt(
        number="MW00000001",
        warehouse="MW14",
        bale_id=TAG,
        received_on=date(2025, 10, 20),
        net=Weight(516),
        holder="BLYTHE",
        electronic=False,
    )


@pytest.fixture()
def repos():
    with Book.open() as book:
        made = Repositories(book.connection)
        made.producers.add(Producer("BLYTHE", "Blythe Farms"))
        made.tickets.add(ticket())
        made.lots.add(run())
        made.bales.add(bale())
        yield made


def test_a_producer_and_a_farm_come_back_whole(repos):
    farm = Farm("3312", "1140", "BLYTHE", Decimal("284.57"))
    repos.farms.add(farm)
    assert repos.producers.get("BLYTHE") == Producer("BLYTHE", "Blythe Farms")
    assert repos.farms.get("3312", "1140") == farm


def test_a_ticket_comes_back_whole(repos):
    assert repos.tickets.get(SEASON, 1) == ticket()


def test_a_lot_comes_back_whole(repos):
    assert repos.lots.get(LOT) == run()


def test_a_bale_comes_back_whole(repos):
    assert repos.bales.get(TAG) == bale()


def test_a_card_comes_back_whole(repos):
    repos.cards.add(card())
    assert repos.cards.get(TAG) == card()


def test_a_receipt_comes_back_whole(repos):
    repos.receipts.issue(receipt())
    assert repos.receipts.get("MW00000001") == receipt()


def test_an_order_comes_back_whole(repos):
    repos.receipts.issue(receipt())
    order = ShippingOrder(
        number="SO000141",
        warehouse="MW14",
        ordered_on=date(2026, 1, 12),
        buyer="CALCOT",
        receipts=("MW00000001",),
        ship_by=date(2026, 1, 20),
    )
    repos.orders.add(order)
    assert repos.orders.get("SO000141") == order


def test_a_contract_comes_back_whole(repos):
    contract = Contract(
        number="C000141",
        buyer="CALCOT",
        signed_on=date(2025, 8, 2),
        bales=400,
        delivery_from=date(2025, 11, 1),
        delivery_to=date(2026, 1, 31),
        basis=CentsPerPound.of("-3.27"),
    )
    repos.contracts.add(contract, SEASON)
    assert repos.contracts.get("C000141") == contract


def test_a_statement_and_its_advance_come_back_whole(repos):
    advance = Advance("A-114", Money.parse("1000.07"))
    repos.advances.add(SEASON, "BLYTHE", advance, date(2025, 11, 3))
    statement = Statement(
        producer="BLYTHE",
        season=SEASON,
        bales=44,
        lint=Weight(22_307),
        lint_proceeds=Money.parse("11648.67"),
        gin_charges=Money.parse("3263.07"),
        seed_credit=Money.parse("2500.17"),
        freight=Money.parse("250.07"),
        byproduct_credit=Money.parse("100.07"),
        advances=(advance,),
    )
    repos.statements.save(statement, date(2026, 2, 3))
    assert repos.statements.get(SEASON, "BLYTHE") == statement


def test_a_cheque_comes_back_whole(repos):
    cheque = Cheque("1001", "BLYTHE", Money.parse("10885.77"), date(2026, 2, 3))
    repos.cheques.issue(cheque, SEASON)
    assert repos.cheques.get("1001") == cheque


def test_the_rates_come_back_whole(repos):
    repos.rates.post(SEASON, default_terms(), date(2025, 8, 1))
    assert repos.rates.get(SEASON) == default_terms()


def test_a_haul_and_its_rate_come_back_whole(repos):
    rate = Rate(
        hauler="TRUXTON",
        per_module=Money.parse("42.07"),
        per_mile=Money.parse("3.17"),
        minimum=Money.parse("250.07"),
    )
    repos.freight.post(SEASON, rate)
    load = Haul("TRUXTON", DAY, (1,), 18)
    repos.freight.haul(SEASON, load)
    assert repos.freight.rate(SEASON, "TRUXTON") == rate
    assert repos.freight.hauls(SEASON) == [load]


def test_a_byproduct_sale_comes_back_whole(repos):
    sale = Sale(MOTES, date(2025, 11, 4), Weight(24_007), Money.parse("180.07"), "MILL")
    repos.byproducts.sell(SEASON, sale)
    assert repos.byproducts.sales(SEASON) == [sale]


def test_a_setting_comes_back_as_it_was_written(repos):
    assert repos.settings.set("gin_code", "41207", DAY) == "41207"
    assert repos.settings.get("gin_code") == "41207"
