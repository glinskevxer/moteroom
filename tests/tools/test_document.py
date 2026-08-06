from pathlib import Path

import pytest

from moteroom.tools.document import WRITE, Generated


def made(path: Path, text: str = "hello\n") -> Generated:
    return Generated(name="check_thing", path=path, render=lambda: text, counted=lambda: 3)


def test_a_missing_document_is_caught(tmp_path: Path) -> None:
    findings, checked = made(tmp_path / "THING.md").check()
    assert checked == 3
    assert "has not been generated" in str(findings[0])


def test_a_stale_document_is_caught(tmp_path: Path) -> None:
    path = tmp_path / "THING.md"
    path.write_text("something else\n", encoding="utf-8")
    findings, _ = made(path).check()
    assert "out of date" in str(findings[0])
    assert WRITE in str(findings[0])


def test_writing_makes_the_folder_and_the_file(tmp_path: Path) -> None:
    document = made(tmp_path / "docs" / "THING.md")
    written = document.write()
    assert written.read_text(encoding="utf-8") == "hello\n"
    assert document.check()[0] == []


def test_the_main_writes_when_it_is_told_to(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = made(tmp_path / "THING.md")
    assert document.main([WRITE]) == 0
    assert "wrote" in capsys.readouterr().out
    assert document.path.exists()


def test_the_main_checks_when_it_is_not(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = made(tmp_path / "THING.md")
    assert document.main([]) == 1
    assert "check_thing" in capsys.readouterr().out
    document.write()
    assert document.main([]) == 0


def test_a_document_compares_by_value(tmp_path: Path) -> None:
    path = tmp_path / "THING.md"
    assert made(path).path == made(path).path
