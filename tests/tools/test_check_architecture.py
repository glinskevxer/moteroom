from pathlib import Path
from types import ModuleType

from moteroom.tools.check_architecture import (
    ARCHITECTURE,
    HEADING,
    WHAT,
    main,
    modules,
    render,
    run,
)
from moteroom.tools.check_layers import ALLOWED
from moteroom.tools.document import Generated


def test_the_document_is_up_to_date():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked == len(ALLOWED)


def test_the_gate_exits_clean():
    assert main() == 0


def test_every_package_is_described():
    assert set(WHAT) == set(ALLOWED)


def test_the_module_counts_are_real():
    assert modules("core") > 3
    assert modules("cli") > 5


def test_the_document_reads_as_a_table():
    lines = render().splitlines()
    assert lines[0] == HEADING
    rows = [line for line in lines if line.startswith("| `")]
    assert len(rows) == len(ALLOWED)


def test_core_is_written_down_as_knowing_nothing():
    line = next(line for line in render().splitlines() if line.startswith("| `core`"))
    assert "nothing" in line


def test_the_written_document_matches_what_renders():
    assert ARCHITECTURE.read_text(encoding="utf-8") == render()


def elsewhere(module: ModuleType, path: Path) -> Generated:
    """The same document written somewhere a test can look at it."""
    return Generated(
        name=module.DOCUMENT.name,
        path=path,
        render=module.DOCUMENT.render,
        counted=module.DOCUMENT.counted,
    )


def test_a_missing_document_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_architecture as module

    monkeypatch.setattr(module, "DOCUMENT", elsewhere(module, tmp_path / "none.md"))
    findings, _ = module.run()
    assert "has not been generated" in str(findings[0])


def test_a_stale_document_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_architecture as module

    stale = tmp_path / "ARCHITECTURE.md"
    stale.write_text("# Architecture\n", encoding="utf-8")
    monkeypatch.setattr(module, "DOCUMENT", elsewhere(module, stale))
    findings, _ = module.run()
    assert "out of date" in str(findings[0])


def test_writing_brings_it_back(monkeypatch, tmp_path):
    import moteroom.tools.check_architecture as module

    made = tmp_path / "docs" / "ARCHITECTURE.md"
    monkeypatch.setattr(module, "DOCUMENT", elsewhere(module, made))
    module.write()
    assert made.read_text(encoding="utf-8") == render()
    assert module.run()[0] == []
