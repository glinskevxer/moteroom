"""The commands the office runs rather than the ones the plant runs.

Nobody weighs a module through these. They are the ones somebody uses on the
book itself: look it over, say whether the season can close, copy it, check the
copy, write it out, hand the pages back. They are the commands that matter
least until the day they matter most, so they are walked end to end here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from tests.conftest import Run

GIN = GinCode("41207")
SEASON = Season(2025)
BALES = 14


def tag(number: int) -> str:
    return str(BaleId.build(SEASON, GIN, number))


@pytest.fixture()
def office(run: Run, tmp_path: Path) -> Run:
    for name, value in (
        ("gin_code", "41207"),
        ("classing_office", "MEMPHIS"),
        ("warehouse", "MW14"),
        ("base_loan_rate", "52.00"),
    ):
        run("setting", "set", name, value)
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run(
        "lot",
        "gin",
        "1",
        "--lint",
        "7210",
        "--seed",
        "11800",
        "--motes",
        "1300",
        "--on",
        "2025-10-16",
    )
    for _ in range(BALES):
        run("bale", "press", "1", "538", "--on", "2025-10-16")
    cards = [
        f"{tag(number)}20251022MEMPHIS 04336294812313042        "
        for number in range(1, BALES + 1)
    ]
    path = tmp_path / "cards.txt"
    path.write_text(
        "\n".join([f"HDRMEMPHIS 20251022{BALES:06d}", *cards, f"TRL{BALES:06d}", ""]),
        encoding="utf-8",
    )
    run("card", "load", str(path))
    run("settle", "rates")
    return run


def test_the_doctor_finds_the_bale_still_at_the_gin(office: Run) -> None:
    looked = office("doctor", "--as-of", "2025-12-01")
    assert looked.exit_code == 0
    assert "fine    schema" in looked.output
    assert "the book is missing" in looked.output


def test_the_season_will_not_close_until_the_bale_is_placed(office: Run) -> None:
    first = office("close")
    assert first.exit_code != 0
    assert "bales placed" in first.output
    for number in range(1, BALES + 1):
        office(
            "receipt",
            "issue",
            tag(number),
            f"MW{number:08d}",
            "--holder",
            "BLYTHE",
            "--on",
            "2025-10-20",
        )
    office("settle", "run", "BLYTHE", "--on", "2026-02-03")
    second = office("close")
    assert second.exit_code == 0
    assert "can close" in second.output


def test_the_book_copies_and_the_copy_verifies(office: Run, tmp_path: Path) -> None:
    copy = tmp_path / "copy.sqlite3"
    made = office("backup", str(copy))
    assert made.exit_code == 0
    assert copy.exists()
    checked = office("verify", str(copy))
    assert checked.exit_code == 0
    assert "is sound" in checked.output


def test_the_season_writes_itself_out(office: Run, tmp_path: Path) -> None:
    office("settle", "run", "BLYTHE", "--on", "2026-02-03")
    out = tmp_path / "export"
    made = office("export", str(out), "--as-of", "2026-02-03")
    assert made.exit_code == 0
    folder = out / "moteroom-2025"
    assert (folder / "season.txt").exists()
    assert (folder / "statement-blythe.csv").exists()
    assert "seed cotton  21,200 lb" in (folder / "season.txt").read_text()


def test_the_book_says_how_big_it_is_and_compacts(office: Run) -> None:
    assert "pages free" in office("size").output
    made = office("compact")
    assert made.exit_code == 0
    assert "saved" in made.output
    assert "is sound" in office("verify").output


def test_the_seasons_command_shows_the_one_that_was_worked(office: Run) -> None:
    listed = office("seasons")
    assert "* 2025/26" in listed.output
    assert f"1 tickets, 1 lots, {BALES} bales" in listed.output


def test_the_trail_carries_the_whole_day(office: Run) -> None:
    counted = office("audit", "actions")
    for action in ("weigh", "gin", "press"):
        assert action in counted.output


def test_the_doctor_reads_fine_once_everything_is_done(office: Run) -> None:
    for number in range(1, BALES + 1):
        office(
            "receipt",
            "issue",
            tag(number),
            f"MW{number:08d}",
            "--holder",
            "BLYTHE",
            "--on",
            "2025-10-20",
        )
    office("settle", "run", "BLYTHE", "--on", "2026-02-03")
    looked = office("doctor", "--as-of", "2025-12-01")
    assert "the book is fine" in looked.output
    assert looked.exit_code == 0
