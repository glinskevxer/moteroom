from pathlib import Path

import pytest

from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from tests.cli.conftest import Run

GIN = GinCode("41207")
SEASON = Season(2025)


def tag(number: int) -> str:
    return str(BaleId.build(SEASON, GIN, number))


@pytest.fixture()
def classed(run: Run, tmp_path: Path) -> Run:
    run("setting", "set", "gin_code", "41207")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    run("bale", "press", "1", "538", "--on", "2025-10-16")
    path = tmp_path / "transfer.txt"
    head = "HDRMEMPHIS 20251022000001"
    path.write_text(
        f"{head}\n{tag(1)}20251022MEMPHIS 04336294812313042        \nTRL000001\n",
        encoding="utf-8",
    )
    run("card", "load", str(path))
    return run


def test_a_flat_contract_prices_a_bale(classed):
    made = classed("contract", "price", tag(1), "--price", "68.50")
    assert made.exit_code == 0
    assert "contract   68.50c" in made.output
    assert "515 lb" in made.output


def test_a_basis_contract_needs_futures(classed):
    assert classed("contract", "price", tag(1), "--basis", "-3.25").exit_code != 0
    made = classed("contract", "price", tag(1), "--basis", "-3.25", "--futures", "71.00")
    assert "67.75c" in made.output


def test_a_contract_priced_both_ways_is_refused(classed):
    assert (
        classed("contract", "price", tag(1), "--price", "68.50", "--basis", "-3.25").exit_code
        != 0
    )


def test_a_contract_priced_no_way_at_all_is_refused(classed):
    assert classed("contract", "price", tag(1)).exit_code != 0


def test_a_bale_with_no_card_cannot_be_priced(classed):
    assert classed("contract", "price", tag(2), "--price", "68.50").exit_code != 0


def test_a_fill_says_what_is_left(classed):
    assert "short 150" in classed("contract", "fill", "C000141", "400", "100", "150").output
    assert "filled" in classed("contract", "fill", "C000141", "400", "400").output


def test_a_contract_number_that_will_not_read(classed):
    assert classed("contract", "fill", "141", "400").exit_code != 0


def test_a_contract_writes_and_lists(classed):
    written = classed(
        "contract",
        "write",
        "c000141",
        "calcot",
        "400",
        "--price",
        "68.50",
        "--signed",
        "2025-08-02",
        "--opens",
        "2025-11-01",
        "--closes",
        "2026-01-31",
    )
    assert written.exit_code == 0
    listed = classed("contract", "list")
    assert "C000141" in listed.output
    assert "CALCOT" in listed.output


def test_the_same_contract_twice_is_refused(classed):
    args = [
        "contract",
        "write",
        "C000141",
        "CALCOT",
        "400",
        "--price",
        "68.50",
        "--signed",
        "2025-08-02",
        "--opens",
        "2025-11-01",
        "--closes",
        "2026-01-31",
    ]
    classed(*args)
    assert classed(*args).exit_code != 0


def test_a_delivery_prices_the_bale_and_fills_the_contract(classed):
    classed(
        "contract",
        "write",
        "C000141",
        "CALCOT",
        "2",
        "--price",
        "68.50",
        "--signed",
        "2025-08-02",
        "--opens",
        "2025-11-01",
        "--closes",
        "2026-01-31",
    )
    made = classed("contract", "deliver", "C000141", tag(1), "--on", "2025-12-01")
    assert made.exit_code == 0
    assert "68.95c" in made.output
    listed = classed("contract", "list")
    assert listed.output.count("C000141") == 1


def test_a_delivery_outside_the_window_is_refused(classed):
    classed(
        "contract",
        "write",
        "C000141",
        "CALCOT",
        "2",
        "--price",
        "68.50",
        "--signed",
        "2025-08-02",
        "--opens",
        "2025-11-01",
        "--closes",
        "2025-11-30",
    )
    assert (
        classed("contract", "deliver", "C000141", tag(1), "--on", "2025-12-01").exit_code != 0
    )


def test_a_bale_cannot_be_delivered_twice(classed):
    for number in ("C000141", "C000142"):
        classed(
            "contract",
            "write",
            number,
            "CALCOT",
            "2",
            "--price",
            "68.50",
            "--signed",
            "2025-08-02",
            "--opens",
            "2025-11-01",
            "--closes",
            "2026-01-31",
        )
    classed("contract", "deliver", "C000141", tag(1), "--on", "2025-12-01")
    assert (
        classed("contract", "deliver", "C000142", tag(1), "--on", "2025-12-01").exit_code != 0
    )


def test_an_empty_contract_list_says_nothing(classed):
    assert "(nothing)" in classed("contract", "list").output
