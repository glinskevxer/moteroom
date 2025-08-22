import ast

from moteroom.tools.check_layers import ALLOWED, EXCEPTIONS, _imports, _package_of, main, run


def test_the_package_layers_the_way_it_says_it_does():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 50


def test_the_gate_exits_clean():
    assert main() == 0


def test_core_is_allowed_to_know_nothing_else():
    assert ALLOWED["core"] == {"core"}


def test_the_domain_is_not_allowed_to_know_storage():
    assert "storage" not in ALLOWED["classing"]
    assert "storage" not in ALLOWED["settlement"]


def test_the_command_line_is_allowed_to_know_the_rest():
    assert {"storage", "reporting"} <= ALLOWED["cli"]


def test_there_are_no_exceptions_left():
    assert set() == EXCEPTIONS


def test_the_service_layer_is_the_one_allowed_to_reach_storage():
    assert "storage" in ALLOWED["service"]
    assert "service" not in ALLOWED["storage"]


def test_a_package_is_read_off_a_dotted_name():
    assert _package_of("moteroom.core.weight") == "core"
    assert _package_of("moteroom") == ""
    assert _package_of("click") == ""


def test_the_imports_of_a_module_are_found_both_ways():
    tree = ast.parse(
        "import moteroom.core.weight\nfrom moteroom.loan import schedule\nimport click\n"
    )
    assert _imports(tree) == ["moteroom.core.weight", "moteroom.loan"]


def test_a_relative_import_is_not_counted():
    tree = ast.parse("from . import weight\n")
    assert _imports(tree) == []
