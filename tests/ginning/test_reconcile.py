from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import LotId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.reconcile import reconcile
from moteroom.ginning.run import GinRun

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


def test_two_scales_that_agree():
    found = reconcile(run(), Weight(22_350), 44)
    assert found.difference == 50
    assert found.drift == Decimal("0.22")
    assert found.agrees


def test_two_scales_that_do_not():
    found = reconcile(run(), Weight(21_800), 43)
    assert found.difference == -500
    assert found.drift == Decimal("-2.24")
    assert not found.agrees


def test_the_tolerance_is_the_line():
    inside = reconcile(run(), Weight(22_634), 44)
    outside = reconcile(run(), Weight(22_635), 44)
    assert inside.drift == Decimal("1.50")
    assert inside.agrees
    assert outside.drift == Decimal("1.50")
    assert outside.agrees


def test_a_tighter_tolerance_fails_the_same_lot():
    found = reconcile(run(), Weight(22_500), 44, tolerance=Decimal("0.50"))
    assert not found.agrees


def test_the_average_bale_comes_out_of_the_pressed_weight():
    assert reconcile(run(), Weight(22_350), 44).average_bale == Weight(507)
    assert reconcile(run(), Weight.zero(), 0).average_bale.is_zero


def test_a_reconciliation_prints_its_verdict():
    assert (
        str(reconcile(run(), Weight(22_350), 44))
        == "lot 2025-0042 agrees by 0.22% over 44 bales"
    )


def test_no_bales_cannot_weigh_something():
    with pytest.raises(ValidationError):
        reconcile(run(), Weight(500), 0)


@pytest.mark.parametrize("bales", [-1])
def test_a_negative_bale_count_is_refused(bales):
    with pytest.raises(ValidationError):
        reconcile(run(), Weight(500), bales)


def test_a_negative_tolerance_is_refused():
    with pytest.raises(ValidationError):
        reconcile(run(), Weight(500), 1, tolerance=Decimal("-1"))
