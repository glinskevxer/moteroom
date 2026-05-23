from datetime import date
from decimal import Decimal
from typing import Any

from moteroom.core.ids import ModuleId
from moteroom.core.money import Money
from moteroom.core.weight import Weight
from moteroom.receiving.freight import FreightLedger, Haul, Rate
from moteroom.receiving.ticket import ModuleTicket
from moteroom.reporting.freight import by_hauler, by_producer, owed_to, unhauled

DAY = date(2025, 10, 14)


def ticket(number: int, producer: str = "BLYTHE") -> ModuleTicket:
    return ModuleTicket(
        number=number,
        module=ModuleId(f"HW-{number:06d}"),
        producer=producer,
        farm="3312",
        weighed_on=DAY,
        gross=Weight(38_400),
        tare=Weight(17_200),
        moisture=Decimal("9.4"),
    )


def rate(hauler: str = "TRUXTON", **overrides: Any) -> Rate:
    fields: dict[str, Any] = {
        "hauler": hauler,
        "per_module": Money.parse("42.00"),
        "per_mile": Money.parse("3.10"),
        "minimum": Money.parse("250.00"),
    }
    fields.update(overrides)
    return Rate(**fields)


def loaded() -> FreightLedger:
    ledger = FreightLedger([rate(), rate("BOWLAND")])
    ledger.haul(Haul("TRUXTON", DAY, (1, 2), 18))
    ledger.haul(Haul("BOWLAND", DAY, (3,), 40))
    return ledger


def test_the_haulier_page_adds_by_who_drove():
    made = by_hauler(loaded())
    assert set(made.column("haulier")) == {"TRUXTON", "BOWLAND"}
    assert "2 loads" in made.notes[0]


def test_a_haulier_with_no_loads_is_left_off():
    ledger = FreightLedger([rate(), rate("BOWLAND")])
    ledger.haul(Haul("TRUXTON", DAY, (1,), 18))
    assert by_hauler(ledger).column("haulier") == ["TRUXTON"]


def test_an_empty_page_says_nothing_was_hauled():
    made = by_hauler(FreightLedger())
    assert made.is_empty
    assert made.notes == ("nothing hauled yet",)


def test_the_producer_page_adds_by_whose_modules_rode():
    tickets = [ticket(1), ticket(2), ticket(3, "MERRITT")]
    made = by_producer(loaded(), tickets)
    assert made.column("producer") == ["BLYTHE", "MERRITT"]
    assert made.column("modules") == ["2", "1"]
    assert made.column("hauled") == ["2", "1"]


def test_the_two_pages_reach_the_same_total():
    tickets = [ticket(1), ticket(2), ticket(3, "MERRITT")]
    ledger = loaded()
    from moteroom.core.money import total_money

    by_who_drove = total_money([owed_to(ledger, one) for one in ledger.haulers()])
    by_whose_cotton = ledger.for_tickets([one.number for one in tickets])
    assert by_who_drove == by_whose_cotton
    assert "charged on" in by_producer(ledger, tickets).notes[0]


def test_a_module_nobody_hauled_is_picked_out():
    tickets = [ticket(1), ticket(9)]
    assert [one.number for one in unhauled(loaded(), tickets)] == [9]
    assert unhauled(loaded(), [ticket(1)]) == []


def test_a_producer_who_hauled_their_own_is_charged_nothing():
    made = by_producer(loaded(), [ticket(9, "COLE")])
    assert made.column("freight") == ["$0.00"]
    assert made.column("hauled") == ["0"]
