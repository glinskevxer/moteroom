from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from moteroom.cli.main import main

Run = Callable[..., Result]


@pytest.fixture()
def book(tmp_path: Path) -> str:
    return str(tmp_path / "season.sqlite3")


@pytest.fixture()
def run(book: str) -> Run:
    runner = CliRunner()

    def invoke(*args: str, season: str = "2025") -> Result:
        return runner.invoke(main, ["--book", book, "--season", season, *args])

    return invoke
