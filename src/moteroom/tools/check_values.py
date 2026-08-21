"""Check the domain is still made of values.

Everything the domain holds is a value: a weight, a card, a bale. Values are
frozen, they compare by what they hold, and two of them that hold the same
thing are the same thing. That is not a style preference. It is what lets a
ticket be handed to four modules with nobody wondering which of them changed
it, and it is what makes a test that compares a record to what went in mean
anything.

So every dataclass in the domain has to be frozen, and none of them may carry
a mutable default, which is the other way a value quietly stops being one.
"""

from __future__ import annotations

import ast

from moteroom.tools.gate import Finding, module_name, run_gate, source_files

DOMAIN = (
    "core",
    "receiving",
    "ginning",
    "press",
    "classing",
    "loan",
    "warehouse",
    "settlement",
)
MUTABLE = ("list", "dict", "set", "bytearray")


def _package(name: str) -> str:
    parts = name.split(".")
    return parts[1] if len(parts) > 2 else ""


def _dataclass_call(node: ast.ClassDef) -> ast.Call | None:
    for decorator in node.decorator_list:
        if (
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name)
            and decorator.func.id == "dataclass"
        ):
            return decorator
        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
            return ast.Call(func=decorator, args=[], keywords=[])
    return None


def _is_frozen(call: ast.Call) -> bool:
    for keyword in call.keywords:
        if keyword.arg == "frozen":
            return isinstance(keyword.value, ast.Constant) and keyword.value.value is True
    return False


def _mutable_defaults(node: ast.ClassDef) -> list[str]:
    found = []
    for statement in node.body:
        if not isinstance(statement, ast.AnnAssign) or statement.value is None:
            continue
        value = statement.value
        if isinstance(value, ast.List | ast.Dict | ast.Set) or (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id in MUTABLE
        ):
            found.append(ast.unparse(statement.target))
    return found


def run() -> tuple[list[Finding], int]:
    """Read every dataclass in the domain and check it is still a value."""
    findings: list[Finding] = []
    checked = 0
    for path in source_files():
        name = module_name(path)
        if _package(name) not in DOMAIN:
            continue
        where = name.removeprefix("moteroom.")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            call = _dataclass_call(node)
            if call is None:
                continue
            checked += 1
            if not _is_frozen(call):
                findings.append(
                    Finding(f"{where}.{node.name}", "is a dataclass and not frozen")
                )
            for field in _mutable_defaults(node):
                findings.append(
                    Finding(f"{where}.{node.name}", f"{field} carries a mutable default")
                )
    return findings, checked


def main() -> int:
    """Run the gate and give back a shell exit status."""
    return run_gate("check_values", run)


if __name__ == "__main__":
    raise SystemExit(main())
