from decimal import Decimal
from typing import Any

from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.reporting.producers import best_turnout, owed, spread, summary, total_seed_cotton
from moteroom.service.producer import Standing

SEASON = Season(2025)


def standing(producer: str = "BLYTHE", **overrides: Any) -> Standing:
    fields: dict[str, Any] = {
        "producer": producer,
        "season": SEASON,
        "modules": 4,
        "seed_cotton": Weight(84_800),
        "dry_seed_cotton": Weight(84_000),
        "lots": ("2025-0001",),
        "bales": 58,
        "lint": Weight(29_800),
        "plant_turnout": Decimal("35.14"),
        "settled": False,
        "net": Money.zero(),
        "advanced": Money.zero(),
        "cheques": 0,
    }
    fields.update(overrides)
    return Standing(**fields)


def test_the_page_runs_most_cotton_first():
    made = summary([standing("MERRITT", seed_cotton=Weight(21_200)), standing()])
    assert made.column("producer") == ["BLYTHE", "MERRITT"]
    assert made.column("modules") == ["4", "4"]


def test_the_page_says_who_is_settled():
    made = summary([standing(), standing("MERRITT", settled=True)])
    assert made.column("settled") == ["yes", "no"] or made.column("settled") == ["no", "yes"]
    assert "1 settled, 1 to go" in made.notes[1]


def test_the_notes_total_the_season():
    made = summary([standing(), standing("MERRITT")])
    assert "2 producers" in made.notes[0]
    assert "8 modules" in made.notes[0]
    assert "59,600 lb of lint" in made.notes[0]


def test_an_empty_page_says_nobody_has_ginned():
    made = summary([])
    assert made.is_empty
    assert made.notes == ("nobody has ginned yet",)


def test_the_turnout_spread_is_the_argument():
    made = summary([standing(), standing("MERRITT", lint=Weight(25_000))])
    assert "turnout runs" in made.notes[2]
    assert spread([]) == "nowhere"


def test_the_totals_read_off_the_standings():
    held = [standing(settled=True, net=Money.parse("100.00")), standing("MERRITT")]
    assert owed(held) == Money.parse("100.00")
    assert total_seed_cotton(held) == Weight(169_600)
    assert best_turnout(held) == Decimal("35.14")
    assert best_turnout([]) == Decimal("0.00")


def test_the_against_column_is_signed():
    made = summary([standing(lint=Weight(31_000))])
    assert made.column("against")[0].startswith("+")
