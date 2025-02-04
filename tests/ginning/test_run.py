from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import LotId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
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


def test_a_lot_knows_how_many_modules_it_ate():
    assert run().module_count == 3
    assert run().covers(2)
    assert not run().covers(9)


def test_a_lot_prints_the_way_the_board_reads():
    assert str(run()) == "lot 2025-0042 3 modules 22,300 lb lint"


def test_the_outbound_scales_account_for_most_of_it():
    assert run().accounted == Weight(61_600)
    assert run().unaccounted == Weight(2_000)


def test_a_lot_has_to_gin_something():
    with pytest.raises(ValidationError):
        run(tickets=())


def test_a_lot_cannot_gin_the_same_ticket_twice():
    with pytest.raises(ValidationError):
        run(tickets=(1, 1, 2))


def test_a_lot_cannot_name_an_unnumbered_ticket():
    with pytest.raises(ValidationError):
        run(tickets=(0, 1))


def test_a_lot_is_ginned_inside_its_own_season():
    with pytest.raises(ValidationError) as caught:
        run(ginned_on=date(2025, 7, 30))
    assert caught.value.field == "ginned_on"


def test_a_lot_weighs_something_and_makes_lint():
    with pytest.raises(ValidationError):
        run(seed_cotton=Weight.zero())
    with pytest.raises(ValidationError):
        run(lint=Weight.zero())


def test_more_out_than_in_is_a_broken_scale():
    with pytest.raises(ValidationError) as caught:
        run(seed=Weight(50_000))
    assert "scale" in caught.value.message


def test_losing_a_quarter_of_the_lot_is_refused():
    with pytest.raises(ValidationError):
        run(lint=Weight(10_000), seed=Weight(20_000), motes=Weight(1_000))


def test_a_lot_that_only_just_balances_is_allowed():
    lot = run(lint=Weight(22_300), seed=Weight(37_400), motes=Weight(3_900))
    assert lot.unaccounted == Weight(0)
