"""Write the architecture down out of the rules that enforce it.

A diagram in a document is a claim. The layer rules in the gate are the thing
that is actually true, so the document is generated from them and checked
against them, and a layer that changes shows up in the document on the same
commit rather than three months later.

Run the module to check it. Run it with ``--write`` to bring it up to date.
"""

from __future__ import annotations

import sys

from moteroom.tools.check_layers import ALLOWED
from moteroom.tools.gate import PACKAGE_ROOT, REPO_ROOT, Finding, run_gate

ARCHITECTURE = REPO_ROOT / "docs" / "ARCHITECTURE.md"
HEADING = "# Architecture"

WHAT = {
    "core": "units, money, identifiers, the crop year",
    "receiving": "tickets, parties, the yard, the scales, the freight",
    "ginning": "lots, turnout, plant time, drying, byproducts",
    "press": "bales, the counter, moisture restoration, bagging and ties",
    "classing": "instrument readings, colour, the office transfer, sampling",
    "loan": "the premium and discount schedule, pool value, redemption",
    "warehouse": "receipts, storage, shipping, transfers, insurance",
    "settlement": "charges, seed, allocation, contracts, equity, cheques",
    "storage": "the sqlite book, its migrations and the repositories over it",
    "reporting": "reports, as data rather than as text",
    "service": "the work that needs the book and the domain at once",
    "cli": "the command tree",
    "tools": "the gates the build runs against itself",
}


def modules(package: str) -> int:
    """How many modules a package carries."""
    folder = PACKAGE_ROOT / package
    return len([path for path in folder.glob("*.py") if path.name != "__init__.py"])


def render() -> str:
    """The document as it should read."""
    lines = [
        HEADING,
        "",
        "Generated from the layer rules the build enforces. Run",
        "`python -m moteroom.tools.check_architecture --write` after changing them.",
        "",
        "| package | modules | may import | what is in it |",
        "| --- | --- | --- | --- |",
    ]
    for package in sorted(ALLOWED):
        allowed = sorted(one for one in ALLOWED[package] if one != package)
        reach = ", ".join(f"`{one}`" for one in allowed) if allowed else "nothing"
        lines.append(f"| `{package}` | {modules(package)} | {reach} | {WHAT[package]} |")
    lines.extend(
        [
            "",
            "Reading the table: a package may import itself and the packages named,",
            "and nothing else in this codebase. `core` sits at the bottom and knows",
            "nothing about anything. `cli` sits at the top and is allowed to know the",
            "rest, because that is its job.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> tuple[list[Finding], int]:
    """Compare the written document against the rules."""
    if not ARCHITECTURE.exists():
        return [Finding("ARCHITECTURE.md", "has not been generated yet")], len(ALLOWED)
    if ARCHITECTURE.read_text(encoding="utf-8") != render():
        return [Finding("ARCHITECTURE.md", "is out of date, run with --write")], len(ALLOWED)
    missing = sorted(set(ALLOWED) - set(WHAT))
    return (
        [Finding(name, "is a package the document does not describe") for name in missing],
        len(ALLOWED),
    )


def write() -> None:
    """Bring the document up to date."""
    ARCHITECTURE.parent.mkdir(parents=True, exist_ok=True)
    ARCHITECTURE.write_text(render(), encoding="utf-8")


def main() -> int:
    """Run the gate, or write the document when asked to."""
    if "--write" in sys.argv[1:]:
        write()
        print(f"wrote {ARCHITECTURE}")
        return 0
    return run_gate("check_architecture", run)


if __name__ == "__main__":
    raise SystemExit(main())
