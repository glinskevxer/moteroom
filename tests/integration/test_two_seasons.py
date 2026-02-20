"""Two seasons in the one book.

A gin does not start a new file every August. The same book carries last year
and this one, and everything that is keyed by season has to keep them apart:
ticket numbers start again, bale numbers start again, rates are posted per
season, and a report asked for one season must not pick up the other.

This is the test that catches a query somebody wrote without a season in it.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from moteroom.cli.main import main
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season

GIN = GinCode("41207")


def tag(season: int, number: int) -> str:
    return str(BaleId.build(Season(season), GIN, number))


def card_line(bale: str, classed: str) -> str:
    return f"{bale}{classed}MEMPHIS 04336294812313042        "


def transfer(*body: str) -> str:
    head = f"HDRMEMPHIS 20251022{len(body):06d}"
    return "\n".join([head, *body, f"TRL{len(body):06d}"])


@pytest.fixture()
def both(tmp_path: Path) -> Callable[..., Result]:
    book = str(tmp_path / "gin.sqlite3")
    runner = CliRunner()

    def run(*args: str, season: str) -> Result:
        return runner.invoke(main, ["--book", book, "--season", season, *args])

    run("setting", "set", "gin_code", "41207", season="2024")
    run("producer", "add", "BLYTHE", "Blythe Farms", season="2024")
    for season, weighed, ginned in (
        ("2024", "2024-10-14", "2024-10-16"),
        ("2025", "2025-10-14", "2025-10-16"),
    ):
        run(
            "ticket",
            "weigh",
            f"HW-{season}01",
            "BLYTHE",
            "3312",
            "38400",
            "17200",
            "--on",
            weighed,
            season=season,
        )
        run(
            "lot",
            "gin",
            "1",
            "--lint",
            "7400",
            "--seed",
            "11800",
            "--motes",
            "1300",
            "--on",
            ginned,
            season=season,
        )
        run("bale", "press", "1", "538", "--on", ginned, season=season)
        run("settle", "rates", season=season)
    return run


def test_ticket_numbers_start_again_each_season(both: Callable[..., Result]) -> None:
    assert "HW-202401" in both("ticket", "show", "1", season="2024").output
    assert "HW-202501" in both("ticket", "show", "1", season="2025").output
    assert both("ticket", "show", "2", season="2025").exit_code != 0


def test_the_two_seasons_carry_their_own_modules(both: Callable[..., Result]) -> None:
    assert "HW-202401" in both("ticket", "list", season="2024").output
    assert "HW-202401" not in both("ticket", "list", season="2025").output


def test_lot_numbers_start_again_and_are_kept_apart(both: Callable[..., Result]) -> None:
    assert "2024-0001" in both("lot", "list", season="2024").output
    assert "2024-0001" not in both("lot", "list", season="2025").output
    assert "2025-0001" in both("lot", "list", season="2025").output


def test_bale_tags_carry_their_own_season_digit(both: Callable[..., Result]) -> None:
    assert tag(2024, 1) in both("bale", "list", season="2024").output
    assert tag(2025, 1) in both("bale", "list", season="2025").output
    assert tag(2024, 1) not in both("bale", "list", season="2025").output


def test_a_bale_from_the_wrong_season_is_not_found(both: Callable[..., Result]) -> None:
    assert both("bale", "show", tag(2024, 1), season="2025").exit_code == 0
    assert both("bale", "show", tag(2024, 9), season="2024").exit_code != 0


def test_rates_are_posted_once_per_season(both: Callable[..., Result]) -> None:
    assert both("settle", "rates", season="2024").exit_code != 0
    assert "4.25" in both("settle", "rates", "--show", season="2024").output
    assert both("settle", "rates", "--show", season="2026").exit_code != 0


def test_the_reports_only_see_the_season_they_are_asked_for(
    both: Callable[..., Result],
) -> None:
    assert "2024-0001" in both("report", "daily", "--on", "2024-10-16", season="2024").output
    empty = both("report", "daily", "--on", "2024-10-16", season="2025")
    assert "nothing ginned" in empty.output


def test_the_season_page_counts_one_season_at_a_time(both: Callable[..., Result]) -> None:
    for season in ("2024", "2025"):
        page = both("report", "season", season=season)
        assert "1 bales off 1 modules" in page.output


def test_a_settlement_in_one_season_leaves_the_other_open(
    both: Callable[..., Result], tmp_path: Path
) -> None:
    for season, classed in (("2024", "20241022"), ("2025", "20251022")):
        path = tmp_path / f"cards{season}.txt"
        path.write_text(transfer(card_line(tag(int(season), 1), classed)), encoding="utf-8")
        both("card", "load", str(path), season=season)
    both("settle", "run", "BLYTHE", "--on", "2025-02-03", season="2024")
    assert "BLYTHE" in both("report", "settlements", season="2024").output
    assert "nothing settled yet" in both("report", "settlements", season="2025").output
    assert "0 of 1" in both("report", "outstanding", season="2024").output
    assert "1 of 1" in both("report", "outstanding", season="2025").output


def test_closing_one_season_says_nothing_about_the_other(both: Callable[..., Result]) -> None:
    first = both("close", season="2024")
    second = both("close", season="2025")
    assert "2024/25" in first.output
    assert "2025/26" in second.output
    assert "2025" not in first.output.split("2024/25")[0]


def test_the_audit_trail_is_kept_per_season(both: Callable[..., Result]) -> None:
    assert "weigh" in both("audit", "list", season="2024").output
    counted = both("audit", "actions", season="2025")
    assert "weigh" in counted.output
    assert "3 entries" in counted.output
