"""Ask every command in the tree for its help.

A command whose help raises is a command nobody can find out how to use, and
the failure only shows up when somebody types it. The tree is walked rather
than listed, so a command added without help is caught here as well as by the
gate that reads the source.
"""

from __future__ import annotations

import click
import pytest
from click.testing import CliRunner

from moteroom.cli.main import main


def paths() -> list[tuple[str, ...]]:
    """Every command in the tree, by the words that reach it."""
    found: list[tuple[str, ...]] = []

    def walk(command: click.Command, path: tuple[str, ...]) -> None:
        found.append(path)
        if isinstance(command, click.Group):
            for name, child in sorted(command.commands.items()):
                walk(child, (*path, name))

    walk(main, ())
    return found


def test_the_tree_has_the_commands_it_should():
    walked = paths()
    assert () in walked
    assert ("ticket", "weigh") in walked
    assert len(walked) > 40


@pytest.mark.parametrize("path", paths())
def test_every_command_answers_for_its_help(path: tuple[str, ...]) -> None:
    result = CliRunner().invoke(main, [*path, "--help"])
    assert result.exit_code == 0, f"{' '.join(path)} failed: {result.output}"
    assert "Usage:" in result.output


@pytest.mark.parametrize("path", paths())
def test_every_command_says_something_about_itself(path: tuple[str, ...]) -> None:
    result = CliRunner().invoke(main, [*path, "--help"])
    body = result.output.split("Options:")[0]
    assert len(body.split()) > 4, f"{' '.join(path)} says nothing"


@pytest.mark.parametrize("path", paths())
def test_every_option_the_command_takes_is_in_its_help(path: tuple[str, ...]) -> None:
    command: click.Command = main
    for name in path:
        assert isinstance(command, click.Group)
        command = command.commands[name]
    result = CliRunner().invoke(main, [*path, "--help"])
    for parameter in command.params:
        if isinstance(parameter, click.Option):
            assert parameter.opts[0] in result.output, (
                f"{' '.join(path)} hides {parameter.opts}"
            )


@pytest.mark.parametrize("path", paths())
def test_the_options_block_carries_words_and_not_only_names(path: tuple[str, ...]) -> None:
    result = CliRunner().invoke(main, [*path, "--help"])
    if "Options:" not in result.output:
        return
    block = result.output.split("Options:")[1]
    assert len(block.split()) > 3


def test_a_command_nobody_has_is_refused():
    result = CliRunner().invoke(main, ["cotton"])
    assert result.exit_code != 0


def test_the_root_lists_its_groups():
    result = CliRunner().invoke(main, ["--help"])
    for group in ("ticket", "lot", "bale", "card", "receipt", "settle", "report"):
        assert group in result.output
