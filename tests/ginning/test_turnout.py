from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import LotId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.ginning.turnout import (
    HIGH_TURNOUT,
    LOW_TURNOUT,
    bale_equivalent,
    band,
    lint_turnout,
    mote_fraction,
    percent,
    seed_turnout,
    summarise,
)

LOT = LotId(Season(2025), 42)


def run(**overrides: Any) -> GinRun:
    fields: dict[str, Any] = {
        "lot": LOT,
        "ginned_on": date(2025, 10, 16),
        "tickets": (1, 2, 3),
        "seed_cotton": Weight(63_600),
        "lint": Weight(22_300),
        "seed": Weight(35_400),
        "motes": Weight(3_900),
    }
    fields.update(overrides)
    return GinRun(**fields)


def test_percent_reports_to_a_hundredth():
    assert percent(Weight(1), Weight(3)) == Decimal("33.33")
    assert percent(Weight(2), Weight(3)) == Decimal("66.67")


def test_percent_of_nothing_is_refused():
    with pytest.raises(ValidationError):
        percent(Weight(1), Weight.zero())


def test_the_three_turnouts_come_off_the_same_lot():
    assert lint_turnout(run()) == Decimal("35.06")
    assert seed_turnout(run()) == Decimal("55.66")
    assert mote_fraction(run()) == Decimal("6.13")


def test_lint_in_statistical_bales():
    assert bale_equivalent(Weight(480)) == Decimal("1.00")
    assert bale_equivalent(Weight(22_300)) == Decimal("46.46")
    assert bale_equivalent(Weight.zero()) == Decimal("0.00")


@pytest.mark.parametrize(
    ("turnout", "name"),
    [
        (LOW_TURNOUT - Decimal("0.01"), "low"),
        (LOW_TURNOUT, "normal"),
        (Decimal("38.00"), "normal"),
        (HIGH_TURNOUT, "normal"),
        (HIGH_TURNOUT + Decimal("0.01"), "high"),
    ],
)
def test_the_band_reads_off_the_boundaries(turnout, name):
    assert band(turnout) == name


def test_a_summary_carries_the_whole_line():
    line = summarise(run())
    assert line.lot == "2025-0042"
    assert line.modules == 3
    assert line.lint == Weight(22_300)
    assert line.bales == Decimal("46.46")
    assert line.band == "normal"


def test_the_summary_percentages_account_for_the_lot():
    line = summarise(run())
    assert Decimal("96.00") < line.accounted_percent < Decimal("97.00")


def test_a_poor_lot_reads_low():
    line = summarise(run(lint=Weight(18_000), seed=Weight(38_000), motes=Weight(4_000)))
    assert line.band == "low"


def test_a_strong_lot_reads_high():
    line = summarise(run(lint=Weight(29_000), seed=Weight(30_000), motes=Weight(3_000)))
    assert line.band == "high"
