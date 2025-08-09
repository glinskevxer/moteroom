from moteroom.tools.check_docstrings import main, run


def test_the_package_passes_its_own_docstring_gate():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 50


def test_the_gate_exits_clean():
    assert main() == 0


def test_a_module_with_no_docstring_is_caught(tmp_path, monkeypatch):
    import moteroom.tools.check_docstrings as module

    bad = tmp_path / "bad.py"
    bad.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "bad")
    findings, checked = module.run()
    assert checked == 1
    assert "module has no docstring" in str(findings[0])


def test_a_public_class_with_no_docstring_is_caught(tmp_path, monkeypatch):
    import moteroom.tools.check_docstrings as module

    bad = tmp_path / "bad.py"
    bad.write_text('"""A module that says something."""\n\n\nclass Thing:\n    pass\n', "utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "bad")
    findings, _ = module.run()
    assert "class has no docstring" in str(findings[0])


def test_a_private_class_is_left_alone(tmp_path, monkeypatch):
    import moteroom.tools.check_docstrings as module

    bad = tmp_path / "bad.py"
    bad.write_text(
        '"""A module that says something."""\n\n\nclass _Thing:\n    pass\n', "utf-8"
    )
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "bad")
    findings, _ = module.run()
    assert findings == []


def test_a_docstring_that_says_nothing_is_caught(tmp_path, monkeypatch):
    import moteroom.tools.check_docstrings as module

    bad = tmp_path / "bad.py"
    bad.write_text('"""Thing."""\n\n\ndef go() -> None:\n    """Go."""\n', encoding="utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "bad")
    findings, _ = module.run()
    assert len(findings) == 2
    assert "says nothing" in str(findings[0])


def test_a_method_is_not_covered(tmp_path, monkeypatch):
    import moteroom.tools.check_docstrings as module

    bad = tmp_path / "bad.py"
    bad.write_text(
        '"""A module that says something."""\n\n\n'
        'class Thing:\n    """A thing worth having."""\n\n    def go(self) -> None:\n'
        "        pass\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "bad")
    findings, _ = module.run()
    assert findings == []
