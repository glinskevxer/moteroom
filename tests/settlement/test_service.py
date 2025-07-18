from datetime import date
from decimal import Decimal

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.press.bale import Bale
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.settlement.charges import ChargeSchedule
from moteroom.settlement.seed import SeedTerms
from moteroom.settlement.service import SettlementService, Terms
from moteroom.settlement.statement import Advance
from moteroom.storage.book import Book
from moteroom.storage.cards import CardRepository
from moteroom.storage.lots import BaleRepository, LotRepository
from moteroom.storage.producers import ProducerRepository
from moteroom.storage.settlement import AdvanceRepository
from moteroom.storage.tickets import TicketRepository

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 1)

TERMS = Terms(
    charges=ChargeSchedule(
        ginning_per_cwt=Money.parse("4.25"),
        bagging_and_ties=Money.parse("11.50"),
        module_handling=Money.parse("18.00"),
    ),
    seed=SeedTerms(
        price_per_ton=Money.parse("205.00"),
        gin_shares=1,
        producer_shares=3,
    ),
    base_rate=CentsPerPound.of("52.00"),
)


@pytest.fixture()
def service():
    with Book.open() as book:
        people = ProducerRepository(book.connection)
        people.add(Producer("BLYTHE", "Blythe Farms"))
        people.add(Producer("MERRITT", "Merritt"))
        tickets = TicketRepository(book.connection)
        for number, producer in ((1, "BLYTHE"), (2, "MERRITT")):
            tickets.add(
                ModuleTicket(
                    number=number,
                    module=ModuleId(f"HW-{number:06d}"),
                    producer=producer,
                    farm="3312",
                    weighed_on=date(2025, 10, 14),
                    gross=Weight(38_400),
                    tare=Weight(17_200),
                    moisture=Decimal("7.5"),
                )
            )
        LotRepository(book.connection).add(
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
        bales = BaleRepository(book.connection)
        for number in range(1, 5):
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
        yield SettlementService(book, TERMS)


def card(number: int, color: int = 41) -> ClassingRecord:
    return ClassingRecord(
        bale_id=BaleId.build(SEASON, GIN, number),
        classed_on=date(2025, 10, 22),
        office="MEMPHIS",
        micronaire=Micronaire(Decimal("4.0")),
        staple=Staple(36),
        strength=Strength(Decimal("27.0")),
        uniformity=Uniformity(Decimal("81.0")),
        color=ColorGrade(color),
        leaf=LeafGrade(3),
        trash=Trash(Decimal("0.42")),
    )


def test_a_producer_gets_their_half_of_the_lot(service):
    shares = service.shares_for(SEASON, "BLYTHE")
    assert len(shares) == 1
    assert shares[0].lint == Weight(7_450)
    assert shares[0].bales == 2
    assert shares[0].modules == 1


def test_an_unclassed_lot_falls_back_to_the_base_rate(service):
    shares = service.shares_for(SEASON, "BLYTHE")
    assert shares[0].rate == CentsPerPound.of("52.00")
    assert not shares[0].classed
    assert service.unclassed_lots(SEASON) == ["2025-0001"]


def test_a_classed_lot_pays_what_it_classed_at(service):
    cards = CardRepository(service.book.connection)
    for number in range(1, 5):
        cards.add(card(number, color=21))
    shares = service.shares_for(SEASON, "BLYTHE")
    assert shares[0].classed
    assert shares[0].rate.cents > Decimal("52.00")
    assert service.unclassed_lots(SEASON) == []


def test_a_statement_comes_out_of_the_book(service):
    made = service.build(SEASON, "BLYTHE")
    assert made.bales == 2
    assert made.lint == Weight(7_450)
    assert made.lint_proceeds == Money.parse("3874.00")
    assert made.gin_charges > Money.zero()
    assert made.seed_credit > Money.zero()


def test_the_two_producers_split_the_lot_between_them(service):
    first = service.build(SEASON, "BLYTHE")
    second = service.build(SEASON, "MERRITT")
    assert first.bales + second.bales == 4
    assert first.lint + second.lint == Weight(14_900)


def test_advances_are_picked_up(service):
    AdvanceRepository(service.book.connection).add(
        SEASON, "BLYTHE", Advance("A-114", Money.parse("1000.00")), date(2025, 11, 3)
    )
    made = service.build(SEASON, "BLYTHE")
    assert made.advanced == Money.parse("1000.00")


def test_a_producer_with_no_cotton_cannot_be_settled(service):
    with pytest.raises(ValidationError):
        service.build(SEASON, "COLE")


def test_a_lot_whose_tickets_were_voided_is_skipped(service):
    tickets = TicketRepository(service.book.connection)
    tickets.add(
        ModuleTicket(
            number=3,
            module=ModuleId("HW-000001"),
            producer="BLYTHE",
            farm="3312",
            weighed_on=date(2025, 10, 14),
            gross=Weight(38_500),
            tare=Weight(17_200),
            moisture=Decimal("7.5"),
            voids=1,
        )
    )
    assert service.shares_for(SEASON, "BLYTHE") == []


def test_the_producers_to_settle_come_off_the_live_tickets(service):
    assert service.settled_producers(SEASON) == ["BLYTHE", "MERRITT"]
