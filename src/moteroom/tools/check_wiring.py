"""Check nothing in the package is written and then never called.

A module with green tests and no caller is not tested where it matters. It is
tested where it was written, which is not the same thing and is exactly how a
package grows a second way of doing something nobody uses.

Two questions. Is every module reached from an entry point? And is every group
of commands actually hung on the command tree, because a group that is not
added is a group nobody can run.
"""

from __future__ import annotations

import ast

from moteroom.tools.gate import Finding, module_name, report, source_files

ENTRY_POINTS = {"moteroom", "moteroom.cli.main"}


def _imports(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return {name for name in found if name.startswith("moteroom")}


def _graph() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for path in source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        graph[module_name(path)] = _imports(tree)
    return graph


def _reached(graph: dict[str, set[str]]) -> set[str]:
    seen: set[str] = set()
    stack = [name for name in ENTRY_POINTS if name in graph]
    stack.extend(name for name in graph if name.startswith("moteroom.tools."))
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        stack.extend(target for target in graph.get(name, set()) if target in graph)
    return seen


def _command_groups() -> set[str]:
    """Every click group defined under the cli package."""
    groups: set[str] = set()
    for path in source_files():
        name = module_name(path)
        if not name.startswith("moteroom.cli.") or name.endswith(".main"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                target = decorator.func if isinstance(decorator, ast.Call) else decorator
                if isinstance(target, ast.Attribute) and target.attr == "group":
                    groups.add(node.name)
    return groups


def _registered() -> set[str]:
    """Every group added to the command tree in cli.main."""
    added: set[str] = set()
    for path in source_files():
        if module_name(path) != "moteroom.cli.main":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_command"
                and node.args
                and isinstance(node.args[0], ast.Name)
            ):
                added.add(node.args[0].id)
    return added


def run() -> tuple[list[Finding], int]:
    """Walk the import graph from the entry points and see what it misses."""
    findings: list[Finding] = []
    graph = _graph()
    reached = _reached(graph)
    packages = {module_name(path) for path in source_files() if path.name == "__init__.py"}
    for name in sorted(graph):
        if name in reached or name in packages:
            continue
        findings.append(Finding(name.removeprefix("moteroom."), "is not reached from anywhere"))
    groups = _command_groups()
    registered = _registered()
    for missing in sorted(groups - registered):
        findings.append(Finding(missing, "is a command group nobody hung on the tree"))
    return findings, len(graph)


def main() -> int:
    """Run the gate and give back a shell exit status."""
    findings, checked = run()
    return report("check_wiring", findings, checked)


if __name__ == "__main__":
    raise SystemExit(main())
