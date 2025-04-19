from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.core.weight import Weight
from moteroom.settlement.charges import ChargeSchedule, bill


def schedule(**overrides: Any) -> ChargeSchedule:
    fields: dict[str, Any] = {
        "ginning_per_cwt": Money.parse("4.25"),
        "bagging_and_ties": Money.parse("11.50"),
        "module_handling": Money.parse("18.00"),
        "drying_per_cwt": Money.parse("0.65"),
        "minimum_per_bale": Money.parse("60.00"),
    }
    fields.update(overrides)
    return ChargeSchedule(**fields)


@pytest.mark.parametrize(
    "field",
    [
        "ginning_per_cwt",
        "bagging_and_ties",
        "module_handling",
        "drying_per_cwt",
        "minimum_per_bale",
    ],
)
def test_a_negative_rate_is_refused(field):
    with pytest.raises(ValidationError):
        schedule(**{field: Money.parse("-0.01")})


def test_ginning_is_charged_on_the_hundredweight():
    billed = bill(schedule(), Weight(63_600), bales=44, modules=3)
    assert billed.ginning == Money.parse("2703.00")


def test_bagging_and_module_handling_are_charged_by_the_count():
    billed = bill(schedule(), Weight(63_600), bales=44, modules=3)
    assert billed.bagging_and_ties == Money.parse("506.00")
    assert billed.module_handling == Money.parse("54.00")


def test_drying_is_only_charged_on_what_was_dried():
    dry = bill(schedule(), Weight(63_600), bales=44, modules=3)
    wet = bill(schedule(), Weight(63_600), bales=44, modules=3, dried=Weight(20_000))
    assert dry.drying.is_zero
    assert wet.drying == Money.parse("130.00")


def test_more_dried_than_came_in_is_refused():
    with pytest.raises(ValidationError):
        bill(schedule(), Weight(1_000), bales=2, modules=1, dried=Weight(1_001))


def test_the_total_adds_the_lines_up():
    billed = bill(schedule(), Weight(63_600), bales=44, modules=3)
    assert billed.total == Money.parse("3263.00")
    assert [name for name, _ in billed.lines()][-1] == "total"
    assert str(billed) == "gin charges $3,263.00"


def test_a_light_load_is_lifted_to_the_minimum():
    billed = bill(
        schedule(minimum_per_bale=Money.parse("150.00")),
        Weight(1_600),
        bales=1,
        modules=1,
    )
    assert billed.minimum_uplift == Money.parse("52.50")
    assert billed.total == Money.parse("150.00")


def test_a_full_load_is_not_lifted():
    billed = bill(schedule(), Weight(63_600), bales=44, modules=3)
    assert billed.minimum_uplift.is_zero


def test_a_negative_count_is_refused():
    with pytest.raises(ValidationError):
        bill(schedule(), Weight(1_000), bales=-1, modules=1)
    with pytest.raises(ValidationError):
        bill(schedule(), Weight(1_000), bales=1, modules=-1)


def test_seed_cotton_that_made_no_bales_is_refused():
    with pytest.raises(ValidationError):
        bill(schedule(), Weight(1_000), bales=0, modules=1)


def test_nothing_ginned_charges_nothing():
    billed = bill(schedule(), Weight.zero(), bales=0, modules=0)
    assert billed.total.is_zero
