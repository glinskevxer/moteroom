from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.reporting.season import Facts, against, summary


def facts(**overrides: Any) -> Facts:
    fields: dict[str, Any] = {
        "season": Season(2025),
        "producers": 4,
        "modules": 120,
        "seed_cotton": Weight(2_544_000),
        "lint": Weight(894_000),
        "seed": Weight(1_416_000),
        "motes": Weight(156_000),
        "bales": 1_740,
        "classed": 1_700,
        "white": 1_300,
        "loan_value": Money.parse("465000.00"),
        "settled": 4,
    }
    fields.update(overrides)
    return Facts(**fields)


def test_the_page_carries_the_numbers_a_gin_is_judged_on():
    made = summary(facts())
    named = dict(zip(made.column("measure"), made.column("value"), strict=True))
    assert named["turnout"] == "35.14%"
    assert named["bales"] == "1740"
    assert named["average bale"] == "513 lb"


def test_the_shares_read_off_the_counts():
    made = facts()
    assert made.white_share == Decimal("76.47")
    assert made.classed_share == Decimal("97.70")


def test_bales_a_module_and_value_a_bale():
    made = facts()
    assert made.bales_per_module == Decimal("14.50")
    assert made.value_per_bale == Money.parse("267.25")


def test_an_empty_season_divides_by_nothing_safely():
    made = facts(
        modules=0, bales=0, classed=0, white=0, seed_cotton=Weight.zero(), lint=Weight.zero()
    )
    assert made.turnout == Decimal("0.00")
    assert made.average_bale.is_zero
    assert made.bales_per_module == Decimal("0.00")
    assert made.value_per_bale.is_zero
    assert (
        dict(zip(summary(made).column("measure"), summary(made).column("value"), strict=True))[
            "modules"
        ]
        == "0"
    )


def test_two_seasons_compare_with_the_move_between_them():
    made = against(facts(), facts(season=Season(2024), modules=100, bales=1_500))
    assert made.headers == ("measure", "2024/25", "2025/26", "move")
    assert made.column("move")[0] == "+20.00%"
    assert made.column("move")[3] == "+16.00%"


def test_a_season_that_fell_reads_negative():
    made = against(facts(modules=80), facts(season=Season(2024), modules=100))
    assert made.column("move")[0] == "-20.00%"


def test_a_season_after_nothing_has_no_move():
    made = against(facts(), facts(season=Season(2024), modules=0))
    assert made.column("move")[0] == "-"


def test_a_season_does_not_compare_against_itself():
    with pytest.raises(ValueError, match="itself"):
        against(facts(), facts())
