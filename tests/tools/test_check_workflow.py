from moteroom.tools.check_workflow import (
    PYTHON_VERSIONS,
    REQUIRED_STEPS,
    WORKFLOW,
    _named_gates,
    gate_modules,
    main,
    run,
)


def test_the_workflow_is_where_it_says_it_is():
    assert WORKFLOW.exists()
    assert WORKFLOW.name == "ci.yml"


def test_the_workflow_runs_every_gate():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked >= 4


def test_the_gate_exits_clean():
    assert main() == 0


def test_the_gates_are_found_off_the_tools_folder():
    modules = gate_modules()
    assert "check_migrations" in modules
    assert "check_workflow" not in modules


def test_the_workflow_names_the_gates_it_runs():
    named = _named_gates(WORKFLOW.read_text(encoding="utf-8"))
    assert set(named) == set(gate_modules())


def test_both_python_versions_are_tested():
    text = WORKFLOW.read_text(encoding="utf-8")
    for version in PYTHON_VERSIONS:
        assert f'"{version}"' in text


def test_the_required_steps_are_in_the_workflow():
    text = WORKFLOW.read_text(encoding="utf-8")
    for step in REQUIRED_STEPS:
        assert step in text


def test_a_missing_workflow_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_workflow as module

    monkeypatch.setattr(module, "WORKFLOW", tmp_path / "none.yml")
    findings, checked = module.run()
    assert checked == 0
    assert "there is no workflow" in str(findings[0])


def test_a_gate_the_workflow_forgets_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_workflow as module

    thin = tmp_path / "ci.yml"
    thin.write_text("ruff check\nruff format --check\nmypy\npytest\n", encoding="utf-8")
    monkeypatch.setattr(module, "WORKFLOW", thin)
    findings, _ = module.run()
    assert any("does not run" in str(finding) for finding in findings)


def test_a_gate_that_does_not_exist_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_workflow as module

    text = (
        WORKFLOW.read_text(encoding="utf-8")
        + "\n      - run: python -m moteroom.tools.check_ghost\n"
    )
    made = tmp_path / "ci.yml"
    made.write_text(text, encoding="utf-8")
    monkeypatch.setattr(module, "WORKFLOW", made)
    findings, _ = module.run()
    assert any("does not exist" in str(finding) for finding in findings)
