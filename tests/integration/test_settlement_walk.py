"""A settlement with everything on it.

The statement is the one page that pulls from every part of the season, so
this walks a producer all the way through with each piece added in turn and
checks the net moves the way it should: freight down, byproducts up, advances
down, and the whole thing adding back to the lines it printed.
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal
from pathlib import Path

import pytest

from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from tests.conftest import Run

GIN = GinCode("41207")
SEASON = Season(2025)


def tag(number: int) -> str:
    return str(BaleId.build(SEASON, GIN, number))


def transfer(count: int) -> str:
    body = [
        f"{tag(number)}20251022MEMPHIS 04336294812313042        "
        for number in range(1, count + 1)
    ]
    return "\n".join([f"HDRMEMPHIS 20251022{count:06d}", *body, f"TRL{count:06d}"])


def _money(text: str) -> Decimal:
    """Read one of the amounts a statement prints."""
    cleaned = text.replace("$", "").replace(",", "")
    return Decimal(cleaned)


def net_of(run: Run) -> Decimal:
    made = run("settle", "preview", "BLYTHE")
    for line in made.output.splitlines():
        if line.startswith("net "):
            return Decimal(line.split("$")[-1].replace(",", "").replace("-", "")) * (
                -1 if "-$" in line else 1
            )
    raise AssertionError(f"no net in\n{made.output}")


@pytest.fixture()
def walked(run: Run, tmp_path: Path) -> Run:
    run("setting", "set", "gin_code", "41207")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    for number in (1, 2):
        run(
            "ticket",
            "weigh",
            f"HW-00418{number}",
            "BLYTHE",
            "3312",
            "38400",
            "17200",
            "--moisture",
            "7.5",
            "--on",
            "2025-10-14",
        )
    run(
        "lot",
        "gin",
        "1,2",
        "--lint",
        "14900",
        "--seed",
        "23600",
        "--motes",
        "2600",
        "--on",
        "2025-10-16",
    )
    for _ in range(4):
        run("bale", "press", "1", "538", "--on", "2025-10-16")
    path = tmp_path / "cards.txt"
    path.write_text(transfer(4), encoding="utf-8")
    run("card", "load", str(path))
    run("settle", "rates")
    return run


def test_the_starting_settlement_has_no_freight_or_byproducts(walked: Run) -> None:
    shown = walked("settle", "preview", "BLYTHE")
    assert "freight        $0.00" in shown.output
    assert "byproducts     $0.00" in shown.output


def test_freight_takes_the_net_down(walked: Run) -> None:
    before = net_of(walked)
    walked("ticket", "freight", "TRUXTON", "1,2", "18", "--on", "2025-10-14")
    after = net_of(walked)
    assert after < before


def test_byproducts_put_the_net_back_up(walked: Run) -> None:
    before = net_of(walked)
    walked("lot", "byproduct", "motes", "24000", "180.00", "--on", "2025-11-04")
    after = net_of(walked)
    assert after > before


def test_a_disposal_takes_the_net_down(walked: Run) -> None:
    before = net_of(walked)
    walked("lot", "byproduct", "trash", "24000", "22.50", "--disposal", "--on", "2025-11-04")
    assert net_of(walked) < before


def test_an_advance_takes_the_net_down_too(walked: Run) -> None:
    before = net_of(walked)
    walked("settle", "advance", "BLYTHE", "A-114", "1000.00", "--on", "2025-11-03")
    assert net_of(walked) == before - Decimal("1000.00")


def test_everything_together_still_adds_up(walked: Run) -> None:
    walked("ticket", "freight", "TRUXTON", "1,2", "18", "--on", "2025-10-14")
    walked("lot", "byproduct", "motes", "24000", "180.00", "--on", "2025-11-04")
    walked("settle", "advance", "BLYTHE", "A-114", "1000.00", "--on", "2025-11-03")
    walked("settle", "run", "BLYTHE", "--on", "2026-02-03")
    page = walked("report", "statement", "BLYTHE", "--csv")
    rows = list(csv.reader(io.StringIO(page.output)))[1:]
    amounts = [_money(row[1]) for row in rows if row]
    assert sum(amounts[:-1]) == amounts[-1]


def test_the_settled_page_keeps_the_freight_and_byproducts(walked: Run) -> None:
    walked("ticket", "freight", "TRUXTON", "1,2", "18", "--on", "2025-10-14")
    walked("lot", "byproduct", "motes", "24000", "180.00", "--on", "2025-11-04")
    walked("settle", "run", "BLYTHE", "--on", "2026-02-03")
    page = walked("report", "statement", "BLYTHE")
    assert "freight" in page.output
    assert "byproducts" in page.output
    assert "$0.00" not in page.output.split("freight")[1].splitlines()[0]


def test_the_settlement_is_written_once_and_does_not_move(walked: Run) -> None:
    walked("settle", "run", "BLYTHE", "--on", "2026-02-03")
    first = walked("report", "statement", "BLYTHE").output
    walked("lot", "byproduct", "motes", "24000", "180.00", "--on", "2025-11-04")
    assert walked("report", "statement", "BLYTHE").output == first
