"""What a gate is and how it reports.

Every gate collects findings and returns an exit status. Nothing raises on the
first problem, because a gate that stops at the first finding takes as many
runs to clear as there are problems.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACKAGE_ROOT.parent.parent


Gate = Callable[[], tuple[list["Finding"], int]]


@dataclass(frozen=True)
class Finding:
    """One thing a gate objects to, with where it is."""

    where: str
    detail: str

    def __str__(self) -> str:
        return f"{self.where}: {self.detail}"


def source_files() -> list[Path]:
    """Every module in the package, in a stable order."""
    return sorted(
        path for path in PACKAGE_ROOT.rglob("*.py") if "__pycache__" not in path.parts
    )


def module_name(path: Path) -> str:
    """The dotted name of a file inside the package."""
    relative = path.relative_to(PACKAGE_ROOT.parent).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def report(name: str, findings: Sequence[Finding], checked: int) -> int:
    """Print what a gate found and give back the exit status."""
    if findings:
        print(f"{name}: {len(findings)} problems in {checked} files")
        for finding in findings:
            print(f"  {finding}")
        return 1
    print(f"{name}: {checked} files, no problems")
    return 0


def run_gate(name: str, gate: Gate) -> int:
    """Run a gate and report it, which is what every gate module's main does.

    Ten modules were each ending in the same four lines. The four lines are not
    a decision any of them gets to make, so they are made here and each module
    says only what it checks.
    """
    if not callable(gate):
        raise TypeError("a gate has to be callable")
    findings, checked = gate()
    return report(name, findings, checked)
