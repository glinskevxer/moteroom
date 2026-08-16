import ast

from moteroom.tools.check_wiring import (
    ENTRY_POINTS,
    _command_groups,
    _graph,
    _imports,
    _reached,
    _registered,
    main,
    run,
)


def test_everything_in_the_package_is_reached():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 50


def test_the_gate_exits_clean():
    assert main() == 0


def test_the_entry_points_are_the_package_and_the_command_tree():
    assert {"moteroom", "moteroom.__main__", "moteroom.cli.main"} == ENTRY_POINTS


def test_the_graph_covers_every_module():
    graph = _graph()
    assert "moteroom.core.weight" in graph
    assert "moteroom.storage.book" in graph["moteroom.cli.context"]


def test_reaching_walks_the_graph():
    graph: dict[str, set[str]] = {
        "moteroom": {"moteroom.a"},
        "moteroom.a": {"moteroom.b"},
        "moteroom.b": set(),
    }
    assert _reached(graph) == {"moteroom", "moteroom.a", "moteroom.b"}


def test_an_island_is_not_reached():
    graph: dict[str, set[str]] = {"moteroom": set(), "moteroom.island": set()}
    assert "moteroom.island" not in _reached(graph)


def test_imports_are_found_both_ways_and_by_name():
    tree = ast.parse("from moteroom.loan import schedule\nimport moteroom.core.weight\n")
    found = _imports(tree)
    assert "moteroom.loan.schedule" in found
    assert "moteroom.core.weight" in found


def test_every_command_group_is_on_the_tree():
    assert _command_groups() <= _registered()
    assert "producer" in _command_groups()
    assert "report" in _registered()
