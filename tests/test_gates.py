"""Every gate, run from the test suite as well as from CI.

The gates are the build's opinion of the repository, and they are run in CI as
separate steps so a failure names itself. They are run here too, for the
person working locally who runs pytest and nothing else: a layer violation
found on the machine it was written on costs a minute, and the same one found
in CI costs a push.

The list is discovered rather than written, so a gate added without being
wired in is caught by its own absence.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from moteroom.tools.gate import PACKAGE_ROOT, Finding

WRITERS = {"check_glossary", "check_architecture", "check_commands"}
NEEDS_A_REPORT = {"check_coverage"}


def gate_modules() -> list[str]:
    """Every gate module in the tools package."""
    folder = PACKAGE_ROOT / "tools"
    names = sorted(path.stem for path in folder.glob("check_*.py"))
    names.append("release_check")
    return names


def run_gate(name: str) -> tuple[list[Finding], int]:
    module = importlib.import_module(f"moteroom.tools.{name}")
    findings, checked = module.run()
    return list(findings), int(checked)


def test_there_are_gates_to_run():
    names = gate_modules()
    assert len(names) >= 12
    assert "check_layers" in names
    assert "release_check" in names


@pytest.mark.parametrize("name", gate_modules())
def test_every_gate_passes(name: str) -> None:
    if name in NEEDS_A_REPORT:
        return
    findings, checked = run_gate(name)
    assert findings == [], f"{name}:\n" + "\n".join(str(one) for one in findings)
    assert checked > 0


@pytest.mark.parametrize("name", gate_modules())
def test_every_gate_has_a_main_that_reports(name: str) -> None:
    module = importlib.import_module(f"moteroom.tools.{name}")
    entry = getattr(module, "main", None) or getattr(module, "main_gate", None)
    assert callable(entry), f"{name} has no main"


@pytest.mark.parametrize("name", sorted(WRITERS))
def test_every_generated_document_is_where_it_says_it_is(name: str) -> None:
    module = importlib.import_module(f"moteroom.tools.{name}")
    document = module.DOCUMENT
    assert document.path.exists()
    assert document.path.parent.name == "docs"
    assert document.path.read_text(encoding="utf-8") == document.render()


def test_the_workflow_runs_every_gate_that_exists():
    from moteroom.tools.check_workflow import WORKFLOW

    text = WORKFLOW.read_text(encoding="utf-8")
    for name in gate_modules():
        assert f"moteroom.tools.{name}" in text, f"the workflow does not run {name}"


def test_the_gates_are_all_under_the_tools_package():
    for name in gate_modules():
        assert (PACKAGE_ROOT / "tools" / f"{name}.py").exists()


def test_nothing_outside_tools_is_named_like_a_gate():
    stray = [
        path
        for path in PACKAGE_ROOT.rglob("check_*.py")
        if path.parent != PACKAGE_ROOT / "tools"
    ]
    assert stray == []


def test_the_docs_folder_holds_only_generated_documents():
    docs = Path(PACKAGE_ROOT).parent.parent / "docs"
    written = {
        importlib.import_module(f"moteroom.tools.{name}").DOCUMENT.path.name for name in WRITERS
    }
    assert {path.name for path in docs.glob("*.md")} == written
