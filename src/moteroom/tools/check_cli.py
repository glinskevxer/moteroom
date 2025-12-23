"""Check every command says what it is for.

The command line is the only part of this package most people ever read. A
command with no help, or an option whose help is a shrug, is a command nobody
can use without reading the source, so the tree is walked and each one is
asked.

It also catches the thing a person cannot see: two commands under different
groups that would both answer to the same words.
"""

from __future__ import annotations

import click

from moteroom.cli.main import main
from moteroom.tools.gate import Finding, report

MIN_HELP_WORDS = 2
EXEMPT_OPTIONS = {"--help", "--version"}


def _walk(command: click.Command, path: str) -> list[tuple[str, click.Command]]:
    found = [(path, command)]
    if isinstance(command, click.Group):
        for name, child in sorted(command.commands.items()):
            found.extend(_walk(child, f"{path} {name}".strip()))
    return found


def commands() -> list[tuple[str, click.Command]]:
    """Every command on the tree, by the words that reach it."""
    return _walk(main, "")


def run() -> tuple[list[Finding], int]:
    """Ask every command and option what it is for."""
    findings: list[Finding] = []
    tree = commands()
    for path, command in tree:
        where = path or "moteroom"
        help_text = (command.help or command.short_help or "").strip()
        if not help_text:
            findings.append(Finding(where, "has no help"))
        elif len(help_text.split()) < MIN_HELP_WORDS:
            findings.append(Finding(where, "has help that says nothing"))
        for parameter in command.params:
            if not isinstance(parameter, click.Option):
                continue
            if set(parameter.opts) & EXEMPT_OPTIONS:
                continue
            names = "/".join(parameter.opts)
            if not (parameter.help or "").strip():
                findings.append(Finding(f"{where} {names}", "has no help"))
    for path, command in tree:
        if not path:
            continue
        name = path.split()[-1]
        if name != name.lower() or "_" in name:
            findings.append(Finding(path, "is not spelled the way the others are"))
        if isinstance(command, click.Group) and not command.commands:
            findings.append(Finding(path, "is a group with nothing under it"))
    return findings, len(tree)


def main_gate() -> int:
    """Run the gate and give back a shell exit status."""
    findings, checked = run()
    return report("check_cli", findings, checked)


if __name__ == "__main__":
    raise SystemExit(main_gate())
