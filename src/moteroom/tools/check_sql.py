"""Check the SQL all lives in one place.

The storage package exists so that nothing else has to know there is a
database. A query written anywhere else is not a small shortcut: it is a second
place that knows the column names, and it will be the one nobody updates when a
migration renames one.

So two rules. Only storage imports sqlite3, and only storage writes SQL.
"""

from __future__ import annotations

import ast

from moteroom.tools.gate import Finding, module_name, report, source_files

ALLOWED_PACKAGE = "storage"
KEYWORDS = ("SELECT ", "INSERT INTO", "UPDATE ", "DELETE FROM", "CREATE TABLE", "PRAGMA ")


def _package(name: str) -> str:
    parts = name.split(".")
    return parts[1] if len(parts) > 2 else ""


def _strings(tree: ast.Module) -> list[str]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            for piece in node.values:
                if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                    found.append(piece.value)
    return found


def _imports_sqlite(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.startswith("sqlite3") for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("sqlite3"):
            return True
    return False


def run() -> tuple[list[Finding], int]:
    """Look for SQL and for sqlite outside the storage package."""
    findings: list[Finding] = []
    files = source_files()
    for path in files:
        name = module_name(path)
        package = _package(name)
        if package == ALLOWED_PACKAGE or name.startswith("moteroom.tools."):
            continue
        where = name.removeprefix("moteroom.")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _imports_sqlite(tree):
            findings.append(Finding(where, "imports sqlite3 outside storage"))
        for text in _strings(tree):
            for keyword in KEYWORDS:
                if keyword in text.upper():
                    findings.append(Finding(where, f"writes SQL: {text.strip()[:40]!r}"))
                    break
    return findings, len(files)


def main() -> int:
    """Run the gate and give back a shell exit status."""
    findings, checked = run()
    return report("check_sql", findings, checked)


if __name__ == "__main__":
    raise SystemExit(main())
