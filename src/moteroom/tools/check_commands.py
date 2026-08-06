"""Write the command list down out of the command tree.

Everything this package does, somebody reaches through a command, and the list
of them is the closest thing to a table of contents it has. Keeping that list
by hand means it is wrong the week after somebody adds a command, so it is
generated from the tree and checked against it.

Run the module to check it. Run it with ``--write`` to bring it up to date.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from moteroom.cli.main import main
from moteroom.tools.document import Generated
from moteroom.tools.gate import REPO_ROOT, Finding

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


DOCUMENT = Generated(
    name="check_commands",
    path=COMMANDS,
    render=render,
    counted=lambda: len(leaves()),
)


def run() -> tuple[list[Finding], int]:
    """Compare the written list against the tree."""
    findings, checked = DOCUMENT.check()
    findings.extend(
        Finding(f"moteroom {path}", "is a command that says nothing")
        for path, what in leaves()
        if not what
    )
    return findings, checked


def write() -> Path:
    """Bring the list up to date."""
    return DOCUMENT.write()


def main_gate() -> int:
    """Run the gate, or write the list when asked to."""
    if "--write" in sys.argv[1:]:
        return DOCUMENT.main(sys.argv[1:])
    from moteroom.tools.gate import run_gate

    return run_gate("check_commands", run)


if __name__ == "__main__":
    raise SystemExit(main_gate())
