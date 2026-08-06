"""Generate the glossary out of the code, and check it has not drifted.

A cotton gin has its own words and half of them mean something else in an
ordinary sentence. Turnout, staple, leaf, mote, basis. The glossary exists so
somebody new can read the rest of it, and it is generated from the classes
that define those words rather than written separately, because a hand written
glossary is wrong within a season.

Run the module to check it. Run it with ``--write`` to bring it up to date.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from moteroom.tools.document import Generated
from moteroom.tools.gate import PACKAGE_ROOT, REPO_ROOT, Finding, module_name

GLOSSARY = REPO_ROOT / "docs" / "GLOSSARY.md"
PACKAGES = (
    "core",
    "receiving",
    "ginning",
    "press",
    "classing",
    "loan",
    "warehouse",
    "settlement",
)
HEADING = "# Glossary"


def entries() -> list[tuple[str, str, str]]:
    """Every public class in the domain, with the first line of its docstring."""
    found: list[tuple[str, str, str]] = []
    for package in PACKAGES:
        for path in sorted((PACKAGE_ROOT / package).glob("*.py")):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
                    continue
                doc = ast.get_docstring(node) or ""
                first = doc.strip().splitlines()[0] if doc.strip() else ""
                found.append((node.name, module_name(path).removeprefix("moteroom."), first))
    return found


def render() -> str:
    """The glossary as it should read."""
    lines = [
        HEADING,
        "",
        "Generated from the classes that define these words. Run",
        "`python -m moteroom.tools.check_glossary --write` after changing one.",
        "",
        "| term | where | what it is |",
        "| --- | --- | --- |",
    ]
    for name, where, what in sorted(entries()):
        lines.append(f"| `{name}` | `{where}` | {what} |")
    return "\n".join(lines) + "\n"


DOCUMENT = Generated(
    name="check_glossary",
    path=GLOSSARY,
    render=render,
    counted=lambda: len(entries()),
)


def run() -> tuple[list[Finding], int]:
    """Compare the written glossary against the code."""
    return DOCUMENT.check()


def write() -> Path:
    """Bring the glossary up to date."""
    return DOCUMENT.write()


def main() -> int:
    """Run the gate, or write the glossary when asked to."""
    return DOCUMENT.main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
