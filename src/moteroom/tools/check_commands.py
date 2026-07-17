"""Write the command list down out of the command tree.

Everything this package does, somebody reaches through a command, and the list
of them is the closest thing to a table of contents it has. Keeping that list
by hand means it is wrong the week after somebody adds a command, so it is
generated from the tree and checked against it.

Run the module to check it. Run it with ``--write`` to bring it up to date.
"""

from __future__ import annotations

import sys

import click

from moteroom.cli.main import main
from moteroom.tools.gate import REPO_ROOT, Finding, run_gate

COMMANDS = REPO_ROOT / "docs" / "COMMANDS.md"
HEADING = "# Commands"


def summary(command: click.Command) -> str:
    """The first line of what a command says about itself."""
    text = (command.help or command.short_help or "").strip()
    return text.splitlines()[0] if text else ""


def leaves() -> list[tuple[str, str]]:
    """Every command that does something, by the words that reach it."""
    found: list[tuple[str, str]] = []

    def walk(command: click.Command, path: str) -> None:
        if isinstance(command, click.Group):
            for name, child in sorted(command.commands.items()):
                walk(child, f"{path} {name}".strip())
            return
        found.append((path, summary(command)))

    walk(main, "")
    return sorted(found)


def groups() -> list[tuple[str, str]]:
    """The groups the tree hangs off, in the order they are worked."""
    found = []
    for name, command in sorted(main.commands.items()):
        if isinstance(command, click.Group):
            found.append((name, summary(command)))
    return found


def render() -> str:
    """The list as it should read."""
    lines = [
        HEADING,
        "",
        "Generated from the command tree. Run",
        "`python -m moteroom.tools.check_commands --write` after adding one.",
        "",
        "## Groups",
        "",
        "| group | what it covers |",
        "| --- | --- |",
    ]
    lines.extend(f"| `{name}` | {what} |" for name, what in groups())
    lines.extend(["", "## Commands", "", "| command | what it does |", "| --- | --- |"])
    for path, what in leaves():
        lines.append(f"| `moteroom {path}` | {what} |")
    return "\n".join(lines) + "\n"


def run() -> tuple[list[Finding], int]:
    """Compare the written list against the tree."""
    made = leaves()
    if not COMMANDS.exists():
        return [Finding("COMMANDS.md", "has not been generated yet")], len(made)
    if COMMANDS.read_text(encoding="utf-8") != render():
        return [Finding("COMMANDS.md", "is out of date, run with --write")], len(made)
    findings = [
        Finding(f"moteroom {path}", "is a command that says nothing")
        for path, what in made
        if not what
    ]
    return findings, len(made)


def write() -> None:
    """Bring the list up to date."""
    COMMANDS.parent.mkdir(parents=True, exist_ok=True)
    COMMANDS.write_text(render(), encoding="utf-8")


def main_gate() -> int:
    """Run the gate, or write the list when asked to."""
    if "--write" in sys.argv[1:]:
        write()
        print(f"wrote {COMMANDS}")
        return 0
    return run_gate("check_commands", run)


if __name__ == "__main__":
    raise SystemExit(main_gate())
