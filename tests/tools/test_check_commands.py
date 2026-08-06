from pathlib import Path
from types import ModuleType

import click

from moteroom.tools.check_commands import (
    COMMANDS,
    HEADING,
    groups,
    leaves,
    main_gate,
    render,
    run,
    summary,
)
from moteroom.tools.document import Generated


def test_the_list_is_up_to_date():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 40


def test_the_gate_exits_clean():
    assert main_gate() == 0


def test_the_leaves_are_the_commands_that_do_something():
    paths = [path for path, _ in leaves()]
    assert "ticket weigh" in paths
    assert "ticket" not in paths
    assert paths == sorted(paths)


def test_every_leaf_says_what_it_does():
    for path, what in leaves():
        assert what.strip(), f"{path} says nothing"


def test_the_groups_are_the_ones_on_the_tree():
    names = [name for name, _ in groups()]
    assert "ticket" in names
    assert "report" in names
    assert "init" not in names


def test_a_summary_is_the_first_line_of_the_help():
    @click.command()
    def thing() -> None:
        """Do a thing worth doing.

        And here is more about it.
        """

    assert summary(thing) == "Do a thing worth doing."


def test_a_command_with_no_help_summarises_as_nothing():
    @click.command()
    def bare() -> None:
        pass

    assert summary(bare) == ""


def test_the_document_reads_as_two_tables():
    lines = render().splitlines()
    assert lines[0] == HEADING
    assert "## Groups" in lines
    assert "## Commands" in lines


def test_the_written_document_matches_what_renders():
    assert COMMANDS.read_text(encoding="utf-8") == render()


def elsewhere(module: ModuleType, path: Path) -> Generated:
    """The same document written somewhere a test can look at it."""
    return Generated(
        name=module.DOCUMENT.name,
        path=path,
        render=module.DOCUMENT.render,
        counted=module.DOCUMENT.counted,
    )


def test_a_stale_document_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_commands as module

    stale = tmp_path / "COMMANDS.md"
    stale.write_text("# Commands\n", encoding="utf-8")
    monkeypatch.setattr(module, "DOCUMENT", elsewhere(module, stale))
    findings, _ = module.run()
    assert "out of date" in str(findings[0])


def test_a_missing_document_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_commands as module

    monkeypatch.setattr(module, "DOCUMENT", elsewhere(module, tmp_path / "none.md"))
    findings, _ = module.run()
    assert "has not been generated" in str(findings[0])


def test_writing_brings_it_back(monkeypatch, tmp_path):
    import moteroom.tools.check_commands as module

    made = tmp_path / "docs" / "COMMANDS.md"
    monkeypatch.setattr(module, "DOCUMENT", elsewhere(module, made))
    module.write()
    assert made.read_text(encoding="utf-8") == render()
    assert module.run()[0] == []
