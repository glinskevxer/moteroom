"""Every report, on an empty book and on a full one.

Reports are the part of this package that gets run in front of somebody, and
the failure that matters is the one on the empty book in August when nothing
has been ginned yet. So every report command is walked rather than listed: a
report added without a test still gets run here.
"""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner, Result

from moteroom.cli.main import main
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season

GIN = GinCode("41207")
SEASON = Season(2025)


def report_commands() -> list[str]:
    """Every command under the report group, by name."""
    group = main.commands["report"]
    assert isinstance(group, click.Group)
    return sorted(group.commands)


def run_on(book: str, *args: str) -> Result:
    return CliRunner().invoke(main, ["--book", book, "--season", "2025", *args])


@pytest.fixture()
def empty(tmp_path: Path) -> str:
    book = str(tmp_path / "empty.sqlite3")
    run_on(book, "init")
    return book


@pytest.fixture()
def full(tmp_path: Path) -> str:
    book = str(tmp_path / "full.sqlite3")
    run_on(book, "setting", "set", "gin_code", "41207")
    run_on(book, "setting", "set", "warehouse", "MW14")
    run_on(book, "producer", "add", "BLYTHE", "Blythe Farms")
    run_on(
        book,
        "ticket",
        "weigh",
        "HW-004181",
        "BLYTHE",
        "3312",
        "38400",
        "17200",
        "--on",
        "2025-10-14",
    )
    run_on(
        book,
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
        "2025-10-16",
    )
    run_on(book, "bale", "press", "1", "538", "--on", "2025-10-16")
    path = Path(tmp_path / "cards.txt")
    tag = str(BaleId.build(SEASON, GIN, 1))
    card = f"{tag}20251022MEMPHIS 04336294812313042        "
    path.write_text(
        "\n".join(["HDRMEMPHIS 20251022000001", card, "TRL000001", ""]),
        encoding="utf-8",
    )
    run_on(book, "card", "load", str(path))
    run_on(
        book, "receipt", "issue", tag, "MW00000001", "--holder", "BLYTHE", "--on", "2025-10-20"
    )
    run_on(book, "settle", "rates")
    run_on(book, "settle", "run", "BLYTHE", "--on", "2026-02-03")
    return book


ARGUMENTS = {"statement": ["BLYTHE"]}


def test_there_are_reports_to_walk():
    assert len(report_commands()) >= 10
    assert "daily" in report_commands()


@pytest.mark.parametrize("name", report_commands())
def test_every_report_runs_on_an_empty_book(empty: str, name: str) -> None:
    if name in ARGUMENTS:
        return
    result = run_on(empty, "report", name)
    assert result.exit_code == 0, f"{name} failed: {result.output}"
    assert result.output.strip()


@pytest.mark.parametrize("name", report_commands())
def test_every_report_runs_as_csv_on_an_empty_book(empty: str, name: str) -> None:
    if name in ARGUMENTS:
        return
    result = run_on(empty, "report", name, "--csv")
    assert result.exit_code == 0, f"{name} failed: {result.output}"
    header = result.output.splitlines()[0]
    assert header.strip()
    assert "=" not in header


@pytest.mark.parametrize("name", report_commands())
def test_every_report_runs_on_a_worked_book(full: str, name: str) -> None:
    result = run_on(full, "report", name, *ARGUMENTS.get(name, []))
    assert result.exit_code == 0, f"{name} failed: {result.output}"
    assert result.output.strip()


@pytest.mark.parametrize("name", report_commands())
def test_every_report_prints_a_title_or_a_table(full: str, name: str) -> None:
    result = run_on(full, "report", name, *ARGUMENTS.get(name, []))
    lines = result.output.splitlines()
    assert lines
    assert set(lines[1]) <= {"="} if len(lines) > 1 else True


@pytest.mark.parametrize("name", report_commands())
def test_no_report_writes_to_the_book(full: str, name: str) -> None:
    before = run_on(full, "audit", "actions").output
    run_on(full, "report", name, *ARGUMENTS.get(name, []))
    assert run_on(full, "audit", "actions").output == before
