import pytest

from moteroom import __version__
from moteroom.tools.release_check import CHANGELOG, PYPROJECT, main, run


def test_the_package_is_ready_to_ship():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked == 4


def test_the_gate_exits_clean():
    assert main() == 0


def test_the_version_is_in_both_places():
    assert f'version = "{__version__}"' in PYPROJECT.read_text(encoding="utf-8")


def test_the_changelog_mentions_the_version():
    assert f"## {__version__}" in CHANGELOG.read_text(encoding="utf-8")


def test_a_version_that_disagrees_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.release_check as module

    made = tmp_path / "pyproject.toml"
    made.write_text(
        '[project]\nname = "moteroom"\nversion = "9.9.9"\n'
        'dependencies = ["click==8.1.8"]\n'
        '[project.scripts]\nmoteroom = "moteroom.cli.main:main"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "PYPROJECT", made)
    findings, _ = module.run()
    assert any("the package says" in str(finding) for finding in findings)


def test_an_unpinned_dependency_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.release_check as module

    made = tmp_path / "pyproject.toml"
    made.write_text(
        f'[project]\nname = "moteroom"\nversion = "{__version__}"\n'
        'dependencies = ["click>=8"]\n'
        '[project.scripts]\nmoteroom = "moteroom.cli.main:main"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "PYPROJECT", made)
    findings, _ = module.run()
    assert any("not pinned" in str(finding) for finding in findings)


def test_a_missing_entry_point_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.release_check as module

    made = tmp_path / "pyproject.toml"
    made.write_text(
        f'[project]\nname = "moteroom"\nversion = "{__version__}"\n'
        'dependencies = ["click==8.1.8"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "PYPROJECT", made)
    findings, _ = module.run()
    assert any("moteroom command" in str(finding) for finding in findings)


def test_a_missing_changelog_entry_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.release_check as module

    made = tmp_path / "CHANGELOG.md"
    made.write_text("# Changelog\n\n## 0.0.1\n", encoding="utf-8")
    monkeypatch.setattr(module, "CHANGELOG", made)
    findings, _ = module.run()
    assert any("no entry" in str(finding) for finding in findings)


def test_a_missing_pyproject_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.release_check as module

    monkeypatch.setattr(module, "PYPROJECT", tmp_path / "none.toml")
    findings, checked = module.run()
    assert checked == 0
    assert "is not there" in str(findings[0])


@pytest.mark.parametrize("path", [PYPROJECT, CHANGELOG])
def test_the_packaging_files_are_where_the_gate_looks(path):
    assert path.exists()
