from pathlib import Path

import pytest

from moteroom.tools.gate import (
    PACKAGE_ROOT,
    Finding,
    module_name,
    report,
    run_gate,
    source_files,
)


def test_a_finding_prints_where_and_what():
    assert str(Finding("core/weight.py", "no docstring")) == "core/weight.py: no docstring"


def test_the_source_files_are_the_package_and_nothing_else():
    files = source_files()
    assert files
    assert all(path.suffix == ".py" for path in files)
    assert all("__pycache__" not in path.parts for path in files)
    assert files == sorted(files)


def test_a_module_name_comes_off_its_path():
    assert module_name(PACKAGE_ROOT / "core" / "weight.py") == "moteroom.core.weight"
    assert module_name(PACKAGE_ROOT / "core" / "__init__.py") == "moteroom.core"
    assert module_name(Path(PACKAGE_ROOT / "__init__.py")) == "moteroom"


def test_a_clean_gate_reports_nothing(capsys):
    assert report("gate", [], 12) == 0
    assert "no problems" in capsys.readouterr().out


def test_a_gate_with_findings_lists_them(capsys):
    assert report("gate", [Finding("a", "b")], 12) == 1
    printed = capsys.readouterr().out
    assert "1 problems" in printed
    assert "a: b" in printed


def test_running_a_gate_reports_it():
    assert run_gate("gate", lambda: ([], 3)) == 0
    assert run_gate("gate", lambda: ([Finding("a", "b")], 3)) == 1


def test_running_something_that_is_not_a_gate():
    with pytest.raises(TypeError):
        run_gate("gate", "not a gate")  # type: ignore[arg-type]
