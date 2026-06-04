"""Check that the things somebody reads first are written down.

The rule is deliberately narrow: every module and every public class carries a
docstring, and so does every public function defined at module level. Methods
and properties are not covered, because a rule that needs an exception on every
third accessor is not a rule, it is an opinion with a script attached.
"""

from __future__ import annotations

import ast

from moteroom.tools.gate import Finding, module_name, run_gate, source_files

MIN_WORDS = 2


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _has_docstring(node: ast.AST) -> bool:
    if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    return bool(ast.get_docstring(node))


def _too_short(node: ast.Module | ast.ClassDef | ast.FunctionDef) -> bool:
    text = ast.get_docstring(node) or ""
    return len(text.split()) < MIN_WORDS


def run() -> tuple[list[Finding], int]:
    """Walk every module and look at what carries a docstring."""
    findings: list[Finding] = []
    files = source_files()
    for path in files:
        where = module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not _has_docstring(tree):
            findings.append(Finding(where, "the module has no docstring"))
        elif _too_short(tree):
            findings.append(Finding(where, "the module docstring says nothing"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and _is_public(node.name):
                if not _has_docstring(node):
                    findings.append(
                        Finding(f"{where}.{node.name}", "the class has no docstring")
                    )
                elif _too_short(node):
                    findings.append(
                        Finding(f"{where}.{node.name}", "the class docstring says nothing")
                    )
            if isinstance(node, ast.FunctionDef) and _is_public(node.name):
                if not _has_docstring(node):
                    findings.append(
                        Finding(f"{where}.{node.name}", "the function has no docstring")
                    )
                elif _too_short(node):
                    findings.append(
                        Finding(f"{where}.{node.name}", "the function docstring says nothing")
                    )
    return findings, len(files)


def main() -> int:
    """Run the gate and give back a shell exit status."""
    return run_gate("check_docstrings", run)


if __name__ == "__main__":
    raise SystemExit(main())
