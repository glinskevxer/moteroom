from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import LotId, ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.receiving.ticket import ModuleTicket
from moteroom.settlement.allocation import allocate, divide

LOT = LotId(Season(2025), 42)


def ticket(number: int, producer: str = "BLYTHE", **overrides: Any) -> ModuleTicket:
    fields: dict[str, Any] = {
        "number": number,
        "module": ModuleId(f"HW-{number:06d}"),
        "producer": producer,
        "farm": "3312",
        "weighed_on": date(2025, 10, 14),
        "gross": Weight(38_400),
        "tare": Weight(17_200),
        "moisture": Decimal("7.5"),
    }
    fields.update(overrides)
    return ModuleTicket(**fields)


def run(**overrides: Any) -> GinRun:
    fields: dict[str, Any] = {
        "lot": LOT,
        "ginned_on": date(2025, 10, 16),
        "tickets": (1, 2),
        "seed_cotton": Weight(42_400),
        "lint": Weight(14_900),
        "seed": Weight(23_600),
        "motes": Weight(2_600),
    }
    fields.update(overrides)
    return GinRun(**fields)


def test_dividing_gives_the_odd_pound_to_the_biggest_share():
    parts = divide(Weight(101), {"A": Weight(2), "B": Weight(1)})
    assert parts["A"] == Weight(68)
    assert parts["B"] == Weight(33)
    assert parts["A"].pounds + parts["B"].pounds == 101


def test_dividing_on_nothing_is_refused():
    with pytest.raises(ValidationError):
        divide(Weight(100), {"A": Weight.zero()})


def test_a_producer_with_no_basis_gets_nothing():
    parts = divide(Weight(100), {"A": Weight(10), "B": Weight.zero()})
    assert parts["B"].is_zero


def test_one_producer_takes_the_whole_lot():
    split = allocate(run(), [ticket(1), ticket(2)])
    assert split.lint_for("BLYTHE") == Weight(14_900)
    assert split.total_seed == Weight(23_600)
    assert split.producers == ["BLYTHE"]


def test_two_producers_split_on_dry_weight():
    split = allocate(run(), [ticket(1), ticket(2, producer="MERRITT")])
    assert split.lint["BLYTHE"] == Weight(7_450)
    assert split.lint["MERRITT"] == Weight(7_450)
    assert split.total_lint == Weight(14_900)


def test_a_wet_module_earns_less_than_a_dry_one():
    split = allocate(
        run(), [ticket(1, moisture=Decimal("14.0")), ticket(2, producer="MERRITT")]
    )
    assert split.lint["BLYTHE"] < split.lint["MERRITT"]
    assert split.total_lint == Weight(14_900)


def test_the_basis_is_the_dry_weight_not_the_scale_weight():
    split = allocate(run(), [ticket(1, moisture=Decimal("12.0")), ticket(2)])
    assert split.total_basis < Weight(42_400)


def test_the_split_prints_how_many_ways_it_went():
    split = allocate(run(), [ticket(1), ticket(2, producer="MERRITT")])
    assert str(split) == "lot 2025-0042 split 2 ways"


def test_asking_for_a_producer_who_put_nothing_in():
    split = allocate(run(), [ticket(1), ticket(2)])
    with pytest.raises(ValidationError):
        split.lint_for("MERRITT")


def test_the_tickets_have_to_be_the_lot_s_own():
    with pytest.raises(ValidationError):
        allocate(run(), [ticket(1)])
    with pytest.raises(ValidationError):
        allocate(run(), [ticket(1), ticket(3)])


def test_the_same_ticket_twice_is_refused():
    with pytest.raises(ValidationError):
        allocate(run(tickets=(1,)), [ticket(1), ticket(1)])


def test_three_producers_still_add_back_to_the_lot():
    split = allocate(
        run(tickets=(1, 2, 3), seed_cotton=Weight(63_600), lint=Weight(22_301)),
        [ticket(1), ticket(2, producer="MERRITT"), ticket(3, producer="COLE")],
    )
    assert split.total_lint == Weight(22_301)
    assert len(split.producers) == 3
