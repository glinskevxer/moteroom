"""Date rules swept across whole years rather than one convenient Tuesday.

Anything that reads a calendar is tested here on every day of a period rather
than on a date somebody picked, because a rule that is wrong on the first of
August is invisible to a test written in October.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.press.bale import Bale
from moteroom.receiving.ticket import ModuleTicket
from moteroom.receiving.yard import days_waiting, priority_of
from moteroom.warehouse.receipt import Receipt

GIN = GinCode("41207")


def days_of(start: date, count: int) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(count)]


def test_every_day_of_three_years_falls_in_exactly_one_season():
    for day in days_of(date(2024, 1, 1), 365 * 3):
        season = Season.for_date(day)
        assert season.contains(day)
        assert not season.next().contains(day)
        assert not season.previous().contains(day)


def test_the_season_boundary_moves_on_the_first_of_august_every_year():
    for year in range(2020, 2031):
        assert Season.for_date(date(year, 7, 31)) == Season(year - 1)
        assert Season.for_date(date(year, 8, 1)) == Season(year)


def test_a_season_covers_every_day_between_its_ends():
    season = Season(2024)
    day = season.start
    counted = 0
    while day <= season.end:
        assert season.contains(day)
        counted += 1
        day += timedelta(days=1)
    assert counted == 365


def test_a_leap_day_falls_in_the_season_that_was_open():
    assert Season.for_date(date(2028, 2, 29)) == Season(2027)


def test_a_ticket_can_be_written_on_any_day_of_its_season():
    for day in days_of(date(2025, 8, 1), 365):
        one = ModuleTicket(
            number=1,
            module=ModuleId("HW-000001"),
            producer="BLYTHE",
            farm="3312",
            weighed_on=day,
            gross=Weight(38_400),
            tare=Weight(17_200),
            moisture=Decimal("9.4"),
        )
        assert one.season == Season(2025)


def test_a_bale_can_be_pressed_on_any_day_of_its_lot_season():
    lot = LotId(Season(2025), 42)
    for day in days_of(date(2025, 8, 1), 365):
        Bale(
            bale_id=BaleId.build(Season(2025), GIN, 1),
            lot=lot,
            pressed_on=day,
            gross=Weight(538),
            tare=Weight(23),
            moisture=Decimal("6.4"),
        )


def test_days_in_store_never_goes_backwards_over_a_year():
    receipt = Receipt(
        number="MW00000001",
        warehouse="MW14",
        bale_id=BaleId.build(Season(2025), GIN, 1),
        received_on=date(2025, 10, 20),
        net=Weight(515),
        holder="BLYTHE",
    )
    last = 0
    for day in days_of(date(2025, 10, 20), 365):
        days = receipt.days_stored(day)
        assert days >= last
        last = days
    assert last == 365


def test_a_released_receipt_stops_counting_wherever_the_release_falls():
    for offset in range(1, 200):
        receipt = Receipt(
            number="MW00000001",
            warehouse="MW14",
            bale_id=BaleId.build(Season(2025), GIN, 1),
            received_on=date(2025, 10, 20),
            net=Weight(515),
            holder="BLYTHE",
        ).release(date(2025, 10, 20) + timedelta(days=offset), "CALCOT")
        assert receipt.days_stored(date(2026, 7, 31)) == offset + 1


@pytest.mark.parametrize("moisture", ["9.4", "12.4"])
def test_the_yard_priority_only_ever_worsens_as_days_pass(moisture):
    one = ModuleTicket(
        number=1,
        module=ModuleId("HW-000001"),
        producer="BLYTHE",
        farm="3312",
        weighed_on=date(2025, 10, 14),
        gross=Weight(38_400),
        tare=Weight(17_200),
        moisture=Decimal(moisture),
    )
    last = priority_of(one, date(2025, 10, 14))
    for day in days_of(date(2025, 10, 14), 120):
        now = priority_of(one, day)
        assert now <= last
        assert days_waiting(one, day) >= 1
        last = now


def test_the_season_label_is_two_digits_across_a_century_roll():
    assert Season(2099).label == "2099/00"
    assert Season(2000).label == "2000/01"
    assert Season(2009).label == "2009/10"
