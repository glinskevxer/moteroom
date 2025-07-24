from datetime import date
from decimal import Decimal
from typing import Any

from moteroom.core.ids import BaleId, GinCode, LotId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.press.bale import Bale
from moteroom.reporting.daily import daily_sheet, running_turnout

GIN = GinCode("41207")
SEASON = Season(2025)
DAY = date(2025, 10, 16)


def run(number: int, **overrides: Any) -> GinRun:
    fields: dict[str, Any] = {
        "lot": LotId(SEASON, number),
        "ginned_on": DAY,
        "tickets": (number * 10, number * 10 + 1),
        "seed_cotton": Weight(42_400),
        "lint": Weight(14_900),
        "seed": Weight(23_600),
        "motes": Weight(2_600),
    }
    fields.update(overrides)
    return GinRun(**fields)


def bale(number: int, lot: int = 1) -> Bale:
    return Bale(
        bale_id=BaleId.build(SEASON, GIN, number),
        lot=LotId(SEASON, lot),
        pressed_on=DAY,
        gross=Weight(538),
        tare=Weight(23),
        moisture=Decimal("6.4"),
    )


def test_the_sheet_has_a_line_per_lot():
    sheet = daily_sheet(DAY, [run(1), run(2)], [bale(1), bale(2), bale(3, lot=2)])
    assert sheet.column("lot") == ["2025-0001", "2025-0002"]
    assert sheet.column("bales") == ["2", "1"]


def test_the_sheet_only_shows_the_day_asked_for():
    sheet = daily_sheet(DAY, [run(1), run(2, ginned_on=date(2025, 10, 17))], [])
    assert sheet.column("lot") == ["2025-0001"]


def test_a_day_with_nothing_says_so():
    sheet = daily_sheet(DAY, [], [])
    assert sheet.is_empty
    assert sheet.notes == ("nothing ginned",)


def test_the_totals_sit_under_the_table():
    sheet = daily_sheet(DAY, [run(1), run(2)], [bale(1), bale(2)])
    assert "2 lots" in sheet.notes[0]
    assert "84,800 lb in" in sheet.notes[0]
    assert "turnout 35.14%" in sheet.notes[1]


def test_the_average_bale_needs_bales():
    assert "no bales" in daily_sheet(DAY, [run(1)], []).notes[2]
    assert "14,900 lb" in daily_sheet(DAY, [run(1)], [bale(1)]).notes[2]


def test_the_turnout_column_reads_per_lot():
    sheet = daily_sheet(DAY, [run(1, lint=Weight(12_000), seed=Weight(23_600))], [])
    assert sheet.column("turnout") == ["28.30"]


def test_running_turnout_is_weighted_not_averaged():
    small = run(
        1, seed_cotton=Weight(10_000), lint=Weight(4_000), seed=Weight(5_000), motes=Weight(500)
    )
    large = run(
        2,
        seed_cotton=Weight(90_000),
        lint=Weight(27_000),
        seed=Weight(50_000),
        motes=Weight(9_000),
    )
    assert running_turnout([small, large]) == Decimal("31.00")
    assert running_turnout([]) == Decimal("0.00")
