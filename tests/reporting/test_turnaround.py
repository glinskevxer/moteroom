from datetime import date
from decimal import Decimal

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode, LotId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.press.bale import Bale
from moteroom.reporting.turnaround import (
    average,
    gap,
    slowest,
    turnaround,
    waiting,
    week_of,
)

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 1)


def bale(number: int, pressed: date = date(2025, 10, 16)) -> Bale:
    return Bale(
        bale_id=BaleId.build(SEASON, GIN, number),
        lot=LOT,
        pressed_on=pressed,
        gross=Weight(538),
        tare=Weight(23),
        moisture=Decimal("6.4"),
    )


def card(number: int, classed: date = date(2025, 10, 22)) -> ClassingRecord:
    return ClassingRecord(
        bale_id=BaleId.build(SEASON, GIN, number),
        classed_on=classed,
        office="MEMPHIS",
        micronaire=Micronaire(Decimal("4.0")),
        staple=Staple(36),
        strength=Strength(Decimal("28.0")),
        uniformity=Uniformity(Decimal("81.0")),
        color=ColorGrade(41),
        leaf=LeafGrade(3),
        trash=Trash(Decimal("0.42")),
    )


def test_the_gap_is_press_to_card():
    assert gap(bale(1), card(1)) == 6


def test_a_card_for_another_bale_or_before_the_press():
    with pytest.raises(ValidationError):
        gap(bale(1), card(2))
    with pytest.raises(ValidationError):
        gap(bale(1), card(1, classed=date(2025, 10, 1)))


def test_a_week_is_the_monday_it_starts_on():
    assert week_of(date(2025, 10, 16)) == date(2025, 10, 13)
    assert week_of(date(2025, 10, 13)) == date(2025, 10, 13)


def test_the_average_is_to_a_hundredth_of_a_day():
    assert average([6, 7]) == Decimal("6.50")
    assert average([1, 2, 2]) == Decimal("1.67")
    assert average([]) == Decimal("0.00")


def test_the_page_groups_by_the_week_the_bale_was_pressed():
    made = turnaround(
        [
            (bale(1), card(1)),
            (bale(2, pressed=date(2025, 10, 23)), card(2, classed=date(2025, 11, 6))),
        ]
    )
    assert made.column("week") == ["2025-10-13", "2025-10-20"]
    assert made.column("average") == ["6.00", "14.00"]


def test_a_slow_week_reads_slow():
    made = turnaround([(bale(1), card(1, classed=date(2025, 11, 6)))])
    assert made.column("reading") == ["slow"]


def test_a_prompt_week_reads_prompt():
    made = turnaround([(bale(1), card(1))])
    assert made.column("reading") == ["prompt"]
    assert "6.00 days on average" in made.notes[0]


def test_an_empty_page_says_no_cards_back():
    made = turnaround([])
    assert made.is_empty
    assert made.notes == ("no cards back yet",)


def test_the_slowest_bales_come_back_worst_first():
    pairs = [(bale(1), card(1)), (bale(2), card(2, classed=date(2025, 11, 6)))]
    worst = slowest(pairs)
    assert worst[0] == (str(bale(2).bale_id), 21)
    assert worst[1] == (str(bale(1).bale_id), 6)
    assert slowest(pairs, 1) == [worst[0]]


def test_asking_for_no_slowest_at_all():
    with pytest.raises(ValidationError):
        slowest([(bale(1), card(1))], 0)


def test_the_bales_still_waiting_come_back_longest_first():
    bales = [bale(1), bale(2, pressed=date(2025, 10, 1))]
    found = waiting(bales, {str(bale(1).bale_id)}, date(2025, 11, 1))
    assert [one[1] for one in found] == [31]
    assert waiting(bales, set(), date(2025, 9, 1)) == []
