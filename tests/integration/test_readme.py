"""Replay the worked example in the readme.

A readme that has drifted from the code is worse than no readme, because
somebody will type what it says. So the example is not prose: it is a
transcript, and this replays every command in it and compares what came back
against what the readme claims came back.
"""

from __future__ import annotations

import shlex
from pathlib import Path

from click.testing import CliRunner

from moteroom.cli.main import main

README = Path(__file__).resolve().parents[2] / "README.md"
PROMPT = "$ moteroom "
INDENT = "    "


def blocks() -> list[tuple[list[str], list[str]]]:
    """Every command in the readme with the output it claims."""
    found: list[tuple[list[str], list[str]]] = []
    lines = README.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith(INDENT + PROMPT):
            command = shlex.split(line[len(INDENT) + len(PROMPT) :])
            index += 1
            expected: list[str] = []
            while index < len(lines):
                held = lines[index]
                if held.startswith(INDENT + PROMPT):
                    break
                if not held.strip():
                    expected.append("")
                    index += 1
                    continue
                if not held.startswith(INDENT):
                    break
                expected.append(held[len(INDENT) :])
                index += 1
            while expected and not expected[-1].strip():
                expected.pop()
            found.append((command, expected))
            continue
        index += 1
    return found


def test_the_readme_has_a_worked_example():
    found = blocks()
    assert len(found) >= 7
    assert found[0][0] == ["init"]


def test_every_command_in_the_readme_prints_what_it_says(tmp_path: Path) -> None:
    runner = CliRunner()
    book = tmp_path / "season.sqlite3"
    for command, expected in blocks():
        result = runner.invoke(main, ["--book", str(book), "--season", "2025", *command])
        assert result.exit_code == 0, f"{command} failed: {result.output}"
        printed = result.output.rstrip("\n").splitlines()
        if command == ["init"]:
            assert printed[0].endswith("at schema 9")
            continue
        assert printed == expected, f"{command} printed\n" + "\n".join(printed)


def test_the_readme_names_the_layout_that_exists():
    text = README.read_text(encoding="utf-8")
    root = README.parent / "src" / "moteroom"
    for package in sorted(path.name for path in root.iterdir() if path.is_dir()):
        if package == "__pycache__":
            continue
        assert f"src/moteroom/{package}/" in text, f"{package} is not in the readme"


def test_the_readme_names_the_checks_ci_runs():
    text = README.read_text(encoding="utf-8")
    for step in ("ruff check", "mypy", "pytest", "check_migrations"):
        assert step in text
