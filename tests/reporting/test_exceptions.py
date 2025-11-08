from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.ids import BaleId, GinCode, ModuleId
from moteroom.core.money import CentsPerPound
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.reconcile import Reconciliation
from moteroom.receiving.ticket import ModuleTicket
from moteroom.receiving.yard import URGENT as YARD_URGENT
from moteroom.receiving.yard import Waiting
from moteroom.reporting import exceptions
from moteroom.settlement.contract import Contract, Fill

GIN = GinCode("41207")
SEASON = Season(2025)
AS_OF = date(2025, 12, 1)


def ticket() -> ModuleTicket:
    return ModuleTicket(
        number=1,
        module=ModuleId("HW-004181"),
        producer="BLYTHE",
        farm="3312",
        weighed_on=date(2025, 10, 14),
        gross=Weight(38_400),
        tare=Weight(17_200),
        moisture=Decimal("12.4"),
    )


def card(**overrides: Any) -> ClassingRecord:
    fields: dict[str, Any] = {
        "bale_id": BaleId.build(SEASON, GIN, 1),
        "classed_on": date(2025, 10, 22),
        "office": "MEMPHIS",
        "micronaire": Micronaire(Decimal("4.0")),
        "staple": Staple(36),
        "strength": Strength(Decimal("28.0")),
        "uniformity": Uniformity(Decimal("81.0")),
        "color": ColorGrade(41),
        "leaf": LeafGrade(3),
        "trash": Trash(Decimal("0.42")),
    }
    fields.update(overrides)
    return ClassingRecord(**fields)


def contract(**overrides: Any) -> Contract:
    fields: dict[str, Any] = {
        "number": "C000141",
        "buyer": "CALCOT",
        "signed_on": date(2025, 8, 2),
        "bales": 400,
        "delivery_from": date(2025, 11, 1),
        "delivery_to": date(2025, 12, 10),
        "price": CentsPerPound.of("68.50"),
    }
    fields.update(overrides)
    return Contract(**fields)


def test_a_level_nobody_has_is_refused():
    with pytest.raises(ValueError, match="level"):
        exceptions.Finding("panic", "a", "b")


def test_the_yard_reports_only_what_is_urgent():
    urgent = Waiting(ticket(), YARD_URGENT, 20)
    ordinary = Waiting(ticket(), 3, 2)
    found = exceptions.from_yard([urgent, ordinary])
    assert len(found) == 1
    assert found[0].level == exceptions.URGENT
    assert "20 days" in found[0].detail


def test_an_unclassed_bale_gets_worse_the_longer_it_waits():
    tag = BaleId.build(SEASON, GIN, 1)
    assert exceptions.from_unclassed([(tag, 20)]) == []
    assert exceptions.from_unclassed([(tag, 30)])[0].level == exceptions.WATCH
    assert exceptions.from_unclassed([(tag, 60)])[0].level == exceptions.URGENT


def test_a_lot_that_does_not_reconcile_is_reported():
    off = Reconciliation("2025-0001", Weight(14_900), Weight(14_000), 29, Decimal("1.50"))
    fine = Reconciliation("2025-0002", Weight(14_900), Weight(14_890), 29, Decimal("1.50"))
    found = exceptions.from_reconciliations([off, fine])
    assert len(found) == 1
    assert "differ by" in found[0].detail


def test_a_bale_in_store_a_long_time_is_noted():
    from moteroom.warehouse.receipt import Receipt

    receipt = Receipt(
        number="MW00000001",
        warehouse="MW14",
        bale_id=BaleId.build(SEASON, GIN, 1),
        received_on=date(2025, 6, 1),
        net=Weight(515),
        holder="BLYTHE",
    )
    assert exceptions.from_storage([receipt], AS_OF)[0].level == exceptions.NOTE
    assert exceptions.from_storage([receipt], date(2025, 6, 30)) == []


def test_a_released_receipt_is_not_in_store():
    from moteroom.warehouse.receipt import Receipt

    receipt = Receipt(
        number="MW00000001",
        warehouse="MW14",
        bale_id=BaleId.build(SEASON, GIN, 1),
        received_on=date(2025, 6, 1),
        net=Weight(515),
        holder="BLYTHE",
    ).release(date(2025, 7, 1), "CALCOT")
    assert exceptions.from_storage([receipt], AS_OF) == []


def test_a_contract_running_out_of_window_is_urgent():
    short = (contract(), Fill("C000141", 400, 100))
    found = exceptions.from_contracts([short], AS_OF)
    assert found[0].level == exceptions.URGENT
    assert "300 bales short with 9 days left" in found[0].detail


def test_a_contract_with_room_left_is_not_reported():
    roomy = (contract(delivery_to=date(2026, 1, 31)), Fill("C000141", 400, 100))
    assert exceptions.from_contracts([roomy], AS_OF) == []


def test_a_filled_or_expired_contract_is_not_reported():
    filled = (contract(), Fill("C000141", 400, 400))
    expired = (contract(delivery_to=date(2025, 11, 1)), Fill("C000141", 400, 1))
    assert exceptions.from_contracts([filled, expired], AS_OF) == []


def test_below_grade_and_gin_faults_come_off_the_cards():
    found = exceptions.from_cards(
        [card(leaf=LeafGrade(8)), card(extraneous=(Extraneous.parse("P1"),)), card()]
    )
    assert [one.level for one in found] == [exceptions.WATCH, exceptions.NOTE]
    assert "below grade" in found[0].detail


def test_unsettled_producers_are_noted_with_their_lint():
    found = exceptions.from_unsettled(["BLYTHE"], {"BLYTHE": Weight(7_450)})
    assert "7,450 lb" in found[0].detail
    assert exceptions.from_unsettled([], {}) == []


def test_the_page_sorts_worst_first():
    findings = [
        exceptions.Finding(exceptions.NOTE, "b", "later"),
        exceptions.Finding(exceptions.URGENT, "a", "now"),
        exceptions.Finding(exceptions.WATCH, "c", "soon"),
    ]
    made = exceptions.build(findings, AS_OF)
    assert made.column("level") == ["urgent", "watch", "note"]
    assert "3 findings, 1 urgent" in made.notes[0]


def test_an_empty_page_says_nothing_needs_attention():
    made = exceptions.build([], AS_OF)
    assert made.is_empty
    assert made.notes == ("nothing needs attention",)


def test_the_counts_and_the_worst_level():
    findings = [
        exceptions.Finding(exceptions.NOTE, "b", "later"),
        exceptions.Finding(exceptions.URGENT, "a", "now"),
    ]
    assert exceptions.counts(findings) == {"urgent": 1, "watch": 0, "note": 1}
    assert exceptions.worst_level(findings) == exceptions.URGENT
    assert exceptions.worst_level([]) is None


def test_the_urgency_share():
    findings = [
        exceptions.Finding(exceptions.URGENT, "a", "now"),
        exceptions.Finding(exceptions.NOTE, "b", "later"),
    ]
    assert exceptions.urgency(findings) == Decimal("50.00")
    assert exceptions.urgency([]) == Decimal("0.00")


def test_a_finding_prints_its_line():
    assert str(exceptions.Finding(exceptions.URGENT, "a", "now")) == "urgent: a now"
