from moteroom.tools.check_tests import EXEMPT, RENAMED, expected_test, main, modules, run


def test_every_module_has_tests_of_its_own():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 50


def test_the_gate_exits_clean():
    assert main() == 0


def test_a_package_marker_is_exempt():
    assert "moteroom.core" in EXEMPT
    assert "moteroom.core.weight" not in EXEMPT


def test_the_modules_are_the_ones_that_carry_code():
    names = modules()
    assert "moteroom.core.weight" in names
    assert "moteroom" not in names


def test_a_test_file_is_named_after_its_module():
    assert expected_test("moteroom.core.weight").name == "test_weight.py"
    assert expected_test("moteroom.core.weight").parent.name == "core"


def test_a_module_whose_tests_live_elsewhere_is_written_down():
    assert "moteroom.service.settlement" in RENAMED
    assert expected_test("moteroom.service.settlement").name == "test_settlement.py"


def test_a_module_with_no_tests_would_be_caught(monkeypatch):
    import moteroom.tools.check_tests as module

    monkeypatch.setattr(module, "modules", lambda: ["moteroom.core.nothing"])
    findings, checked = module.run()
    assert checked == 1
    assert "has no tests" in str(findings[0])
