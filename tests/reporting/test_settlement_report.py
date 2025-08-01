from typing import Any

from moteroom.core.money import Money
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.reporting.settlement import (
    settlement_summary,
    statement_report,
    total_lint,
    total_paid,
    unsettled,
)
from moteroom.settlement.statement import Advance, Statement

SEASON = Season(2025)


def statement(producer: str = "BLYTHE", **overrides: Any) -> Statement:
    fields: dict[str, Any] = {
        "producer": producer,
        "season": SEASON,
        "bales": 44,
        "lint": Weight(22_300),
        "lint_proceeds": Money.parse("11648.60"),
        "gin_charges": Money.parse("3263.00"),
        "seed_credit": Money.parse("2500.12"),
    }
    fields.update(overrides)
    return Statement(**fields)


def test_a_statement_prints_every_line():
    made = statement_report(statement())
    assert made.column("line")[0] == "lint proceeds"
    assert made.column("line")[-1] == "net"
    assert "44 bales" in made.notes[0]
    assert "due to the producer" in made.notes[1]


def test_an_advance_gets_its_own_line():
    made = statement_report(statement(advances=(Advance("A-114", Money.parse("5000.00")),)))
    assert "advance A-114" in made.column("line")


def test_a_statement_that_comes_out_owing_says_so():
    owing = statement(advances=(Advance("A-114", Money.parse("30000.00")),))
    assert "owing to the gin" in statement_report(owing).notes[1]


def test_the_summary_is_one_line_per_producer_in_order():
    made = settlement_summary([statement("MERRITT"), statement()])
    assert made.column("producer") == ["BLYTHE", "MERRITT"]
    assert made.column("bales") == ["44", "44"]


def test_the_summary_splits_what_is_paid_from_what_is_owed():
    owing = statement("MERRITT", advances=(Advance("A-1", Money.parse("30000.00")),))
    made = settlement_summary([statement(), owing])
    assert "2 producers" in made.notes[0]
    assert "1 to pay" in made.notes[1]
    assert "1 owing" in made.notes[2]


def test_an_empty_summary_says_so():
    made = settlement_summary([])
    assert made.is_empty
    assert made.notes == ("nothing settled yet",)


def test_unsettled_names_who_is_left():
    made = unsettled(["BLYTHE", "MERRITT", "COLE"], [statement()])
    assert made.column("producer") == ["COLE", "MERRITT"]
    assert "2 of 3" in made.notes[0]


def test_unsettled_is_empty_when_everybody_is_done():
    assert unsettled(["BLYTHE"], [statement()]).is_empty


def test_the_totals_only_count_the_cheques():
    owing = statement("MERRITT", advances=(Advance("A-1", Money.parse("30000.00")),))
    assert total_paid([statement(), owing]) == statement().net
    assert total_lint([statement(), owing]) == Weight(44_600)
