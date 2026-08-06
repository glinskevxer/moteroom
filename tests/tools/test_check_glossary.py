from pathlib import Path
from types import ModuleType

from moteroom.tools.check_glossary import GLOSSARY, HEADING, entries, main, render, run
from moteroom.tools.document import Generated


def test_the_glossary_is_up_to_date():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 40


def test_the_gate_exits_clean():
    assert main() == 0


def test_the_entries_come_off_the_domain_classes():
    names = {name for name, _, _ in entries()}
    assert "Weight" in names
    assert "ColorGrade" in names
    assert "Repositories" not in names
    assert "Session" not in names


def test_every_entry_says_what_it_is():
    for name, where, what in entries():
        assert what.strip(), f"{where}.{name} has nothing to say"


def test_the_rendered_glossary_is_a_table_in_order():
    lines = render().splitlines()
    assert lines[0] == HEADING
    terms = [line.split("|")[1].strip(" `") for line in lines if line.startswith("| `")]
    assert terms == sorted(terms)


def test_the_written_glossary_matches_what_renders():
    assert GLOSSARY.read_text(encoding="utf-8") == render()


def elsewhere(module: ModuleType, path: Path) -> Generated:
    """The same document written somewhere a test can look at it."""
    return Generated(
        name=module.DOCUMENT.name,
        path=path,
        render=module.DOCUMENT.render,
        counted=module.DOCUMENT.counted,
    )


def test_a_missing_glossary_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_glossary as module

    monkeypatch.setattr(module, "DOCUMENT", elsewhere(module, tmp_path / "none.md"))
    findings, _ = module.run()
    assert "has not been generated" in str(findings[0])


def test_a_stale_glossary_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_glossary as module

    stale = tmp_path / "GLOSSARY.md"
    stale.write_text("# Glossary\n", encoding="utf-8")
    monkeypatch.setattr(module, "DOCUMENT", elsewhere(module, stale))
    findings, _ = module.run()
    assert "out of date" in str(findings[0])


def test_writing_brings_it_back(monkeypatch, tmp_path):
    import moteroom.tools.check_glossary as module

    made = tmp_path / "docs" / "GLOSSARY.md"
    monkeypatch.setattr(module, "DOCUMENT", elsewhere(module, made))
    module.write()
    assert made.read_text(encoding="utf-8") == render()
    assert module.run()[0] == []
