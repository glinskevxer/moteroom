from pathlib import Path

import pytest

from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from tests.cli.conftest import Run

GIN = GinCode("41207")
SEASON = Season(2025)


def tag(number: int) -> str:
    return str(BaleId.build(SEASON, GIN, number))


def line(bale: str, tail: str = "        ") -> str:
    return f"{bale}20251022MEMPHIS 04336294812313042{tail}"


def transfer(*body: str) -> str:
    head = f"HDRMEMPHIS 20251022{len(body):06d}"
    return "\n".join([head, *body, f"TRL{len(body):06d}"])


@pytest.fixture()
def classed(run: Run, tmp_path: Path) -> Run:
    run("setting", "set", "gin_code", "41207")
    run("setting", "set", "base_loan_rate", "52.00")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    for gross in ("538", "548"):
        run("bale", "press", "1", gross, "--on", "2025-10-16")
    path = tmp_path / "transfer.txt"
    path.write_text(transfer(line(tag(1))), encoding="utf-8")
    run("card", "load", str(path))
    return run


def test_a_bale_prices_line_by_line(classed):
    made = classed("loan", "value", tag(1))
    assert made.exit_code == 0
    assert "base" in made.output
    assert "515 lb at" in made.output


def test_a_bale_with_no_card_cannot_be_priced(classed):
    assert classed("loan", "value", tag(2)).exit_code != 0


def test_a_bale_nobody_pressed(classed):
    assert classed("loan", "value", str(BaleId.build(SEASON, GIN, 9))).exit_code != 0


def test_the_pool_prices_what_is_classed(classed):
    made = classed("loan", "pool")
    assert "bales         1" in made.output
    assert "average rate" in made.output


def test_the_pool_uses_the_posted_rate_when_there_is_one(classed):
    classed("settle", "rates")
    assert classed("loan", "pool").exit_code == 0


def test_redeeming_above_the_loan_charges_interest(classed):
    made = classed("loan", "redeem", tag(1), "--price", "58.00", "--days", "90")
    assert "at the loan rate" in made.output
    assert "interest" in made.output


def test_redeeming_below_the_loan_leaves_a_gain(classed):
    made = classed("loan", "redeem", tag(1), "--price", "46.00", "--days", "90")
    assert "at the world price" in made.output
    assert "market gain" in made.output


def test_a_price_that_will_not_read(classed):
    assert classed("loan", "redeem", tag(1), "--price", "cheap").exit_code != 0


def test_an_interest_rate_that_will_not_read(classed):
    assert (
        classed("loan", "redeem", tag(1), "--price", "46.00", "--interest", "lots").exit_code
        != 0
    )
