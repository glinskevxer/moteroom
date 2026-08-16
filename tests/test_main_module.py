"""Running the package as a module rather than as an installed command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from moteroom import __version__
from moteroom.__main__ import REFUSED, run


def test_the_module_prints_the_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["--version"]) == 0
    assert __version__ in capsys.readouterr().out


def test_the_module_runs_a_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    book = str(tmp_path / "season.sqlite3")
    assert run(["--book", book, "init"]) == 0
    assert "created" in capsys.readouterr().out


def test_one_of_our_errors_comes_back_as_a_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = str(tmp_path / "season.sqlite3")
    run(["--book", book, "init"])
    status = run(["--book", book, "--season", "2025", "producer", "add", "1", "Blythe"])
    assert status == REFUSED
    assert "error: producer" in capsys.readouterr().err


def test_a_command_nobody_has_comes_back_as_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(["cotton"]) != 0


def test_a_command_that_exits_carries_its_status(tmp_path: Path) -> None:
    book = str(tmp_path / "season.sqlite3")
    run(["--book", book, "init"])
    assert run(["--book", book, "--season", "2025", "close"]) == 0


def test_a_missing_book_comes_back_as_a_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = run(
        ["--book", str(tmp_path / "none.sqlite3"), "--season", "2025", "ticket", "list"]
    )
    assert status == REFUSED
    assert "does not exist yet" in capsys.readouterr().err


def test_python_dash_m_reaches_the_same_tree(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "moteroom", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert __version__ in result.stdout


def test_python_dash_m_carries_a_failing_status(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "moteroom", "--book", str(tmp_path / "none.sqlite3"), "verify"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
