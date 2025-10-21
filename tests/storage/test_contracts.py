from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId
from moteroom.core.money import CentsPerPound
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.press.bale import Bale
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.settlement.contract import Contract
from moteroom.storage.book import Book
from moteroom.storage.contracts import ContractRepository
from moteroom.storage.lots import BaleRepository, LotRepository
from moteroom.storage.producers import ProducerRepository
from moteroom.storage.tickets import TicketRepository

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 42)


def contract(**overrides: Any) -> Contract:
    fields: dict[str, Any] = {
        "number": "C000141",
        "buyer": "CALCOT",
        "signed_on": date(2025, 8, 2),
        "bales": 3,
        "delivery_from": date(2025, 11, 1),
        "delivery_to": date(2026, 1, 31),
        "price": CentsPerPound.of("68.50"),
    }
    fields.update(overrides)
    return Contract(**fields)


@pytest.fixture()
def contracts():
    with Book.open() as book:
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
        yield ContractRepository(book.connection)


def test_a_contract_saves_and_reads_back(contracts):
    contracts.add(contract(), SEASON)
    assert contracts.get("C000141") == contract()
    assert [one.number for one in contracts.for_season(SEASON)] == ["C000141"]


def test_a_basis_contract_survives_the_round_trip(contracts):
    made = contract(price=None, basis=CentsPerPound.of("-3.25"))
    contracts.add(made, SEASON)
    assert contracts.get("C000141") == made


def test_the_same_contract_twice_is_refused(contracts):
    contracts.add(contract(), SEASON)
    with pytest.raises(ConflictError):
        contracts.add(contract(), SEASON)


def test_a_contract_nobody_wrote(contracts):
    with pytest.raises(NotFoundError):
        contracts.get("C000141")


def test_a_delivery_reads_back_with_its_rate(contracts):
    contracts.add(contract(), SEASON)
    tag = BaleId.build(SEASON, GIN, 1)
    contracts.deliver("C000141", tag, date(2025, 12, 1), CentsPerPound.of("68.50"))
    delivered = contracts.deliveries("C000141")
    assert delivered[0][0] == tag
    assert delivered[0][2] == CentsPerPound.of("68.50")


def test_a_bale_only_goes_against_one_contract(contracts):
    contracts.add(contract(), SEASON)
    contracts.add(contract(number="C000142"), SEASON)
    tag = BaleId.build(SEASON, GIN, 1)
    contracts.deliver("C000141", tag, date(2025, 12, 1), CentsPerPound.of("68.50"))
    with pytest.raises(ConflictError):
        contracts.deliver("C000142", tag, date(2025, 12, 1), CentsPerPound.of("68.50"))


def test_delivering_against_a_contract_nobody_wrote(contracts):
    with pytest.raises(NotFoundError):
        contracts.deliver(
            "C000141",
            BaleId.build(SEASON, GIN, 1),
            date(2025, 12, 1),
            CentsPerPound.of("68.50"),
        )


def test_delivering_a_bale_nobody_pressed(contracts):
    contracts.add(contract(), SEASON)
    with pytest.raises(ConflictError):
        contracts.deliver(
            "C000141",
            BaleId.build(SEASON, GIN, 9),
            date(2025, 12, 1),
            CentsPerPound.of("68.50"),
        )


def test_the_fill_counts_the_deliveries(contracts):
    contracts.add(contract(), SEASON)
    assert contracts.fill("C000141").remaining == 3
    contracts.deliver(
        "C000141", BaleId.build(SEASON, GIN, 1), date(2025, 12, 1), CentsPerPound.of("68.50")
    )
    assert contracts.fill("C000141").delivered == 1


def test_a_bale_knows_which_contract_took_it(contracts):
    contracts.add(contract(), SEASON)
    tag = BaleId.build(SEASON, GIN, 1)
    assert contracts.contract_for(tag) is None
    contracts.deliver("C000141", tag, date(2025, 12, 1), CentsPerPound.of("68.50"))
    assert contracts.contract_for(tag) == "C000141"
