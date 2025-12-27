import json

from moteroom.tools.check_coverage import FLOORS, measure, package_of


def report(**files: tuple[int, int]) -> dict[str, object]:
    return {
        "files": {
            path: {"summary": {"num_statements": statements, "missing_lines": missing}}
            for path, (statements, missing) in files.items()
        }
    }


def test_a_package_is_read_off_the_path():
    assert package_of("src/moteroom/core/weight.py") == "core"
    assert package_of("src/moteroom/__init__.py") == ""
    assert package_of("somewhere/else.py") == ""


def test_the_floors_cover_every_package():
    assert "core" in FLOORS
    assert FLOORS["core"] > FLOORS["cli"]


def test_measuring_adds_the_files_up():
    tallied = measure(
        report(
            **{
                "src/moteroom/core/weight.py": (100, 1),
                "src/moteroom/core/money.py": (100, 3),
            }
        )
    )
    assert tallied["core"] == (200, 4)


def test_a_file_outside_the_packages_is_ignored():
    assert measure(report(**{"tests/test_thing.py": (10, 10)})) == {}


def test_a_report_with_no_files_measures_nothing():
    assert measure({}) == {}


def test_a_missing_report_is_a_finding(monkeypatch, tmp_path):
    import moteroom.tools.check_coverage as module

    monkeypatch.setattr(module, "REPORT", tmp_path / "none.json")
    findings, checked = module.run()
    assert checked == 0
    assert "nothing was measured" in str(findings[0])


def test_a_package_under_its_floor_is_named(monkeypatch, tmp_path):
    import moteroom.tools.check_coverage as module

    made = tmp_path / "coverage.json"
    files = {f"src/moteroom/{package}/thing.py": (100, 0) for package in FLOORS}
    files["src/moteroom/core/thin.py"] = (100, 50)
    made.write_text(json.dumps(report(**files)), encoding="utf-8")
    monkeypatch.setattr(module, "REPORT", made)
    findings, _ = module.run()
    assert len(findings) == 1
    assert "core: is at 75.00%" in str(findings[0])


def test_every_package_at_its_floor_passes(monkeypatch, tmp_path):
    import moteroom.tools.check_coverage as module

    made = tmp_path / "coverage.json"
    files = {f"src/moteroom/{package}/thing.py": (100, 0) for package in FLOORS}
    made.write_text(json.dumps(report(**files)), encoding="utf-8")
    monkeypatch.setattr(module, "REPORT", made)
    findings, checked = module.run()
    assert findings == []
    assert checked == len(FLOORS)


def test_a_package_nobody_measured_is_named(monkeypatch, tmp_path):
    import moteroom.tools.check_coverage as module

    made = tmp_path / "coverage.json"
    made.write_text(json.dumps(report(**{"src/moteroom/core/thing.py": (10, 0)})), "utf-8")
    monkeypatch.setattr(module, "REPORT", made)
    findings, _ = module.run()
    assert any("not measured" in str(finding) for finding in findings)
