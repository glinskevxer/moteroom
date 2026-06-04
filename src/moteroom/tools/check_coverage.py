"""Hold each package to its own coverage floor.

One number over the whole package hides the thing worth knowing. The money
arithmetic and the storage layer are where a gap costs somebody real money, so
they carry a higher floor than the command line, which is mostly wiring and is
covered through the commands anyway.

The gate reads coverage's own json report. It is not run without one: a gate
that quietly passes when the measurement is missing is worse than no gate, so
a missing report is a finding.
"""

from __future__ import annotations

import json
from pathlib import Path

from moteroom.tools.gate import REPO_ROOT, Finding, run_gate

REPORT = REPO_ROOT / "coverage.json"

FLOORS: dict[str, float] = {
    "core": 99.0,
    "receiving": 98.0,
    "ginning": 98.0,
    "press": 98.0,
    "classing": 98.0,
    "loan": 98.0,
    "warehouse": 98.0,
    "settlement": 98.0,
    "storage": 96.0,
    "service": 95.0,
    "reporting": 96.0,
    "cli": 92.0,
    "tools": 85.0,
}


def package_of(path: str) -> str:
    """Which package a measured file belongs to."""
    parts = Path(path).parts
    if "moteroom" not in parts:
        return ""
    index = parts.index("moteroom")
    rest = parts[index + 1 :]
    return rest[0] if len(rest) > 1 else ""


def measure(data: dict[str, object]) -> dict[str, tuple[int, int]]:
    """Statements and misses per package, out of coverage's own numbers."""
    files = data.get("files")
    if not isinstance(files, dict):
        return {}
    tallied: dict[str, tuple[int, int]] = {}
    for path, entry in files.items():
        package = package_of(str(path))
        if package not in FLOORS:
            continue
        summary = entry.get("summary", {}) if isinstance(entry, dict) else {}
        statements = int(summary.get("num_statements", 0))
        missing = int(summary.get("missing_lines", 0))
        held = tallied.get(package, (0, 0))
        tallied[package] = (held[0] + statements, held[1] + missing)
    return tallied


def run() -> tuple[list[Finding], int]:
    """Compare each package against its floor."""
    if not REPORT.exists():
        return [Finding("coverage.json", "is not there, so nothing was measured")], 0
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    tallied = measure(data)
    findings: list[Finding] = []
    for package, floor in sorted(FLOORS.items()):
        if package not in tallied:
            findings.append(Finding(package, "was not measured at all"))
            continue
        statements, missing = tallied[package]
        covered = 100.0 if statements == 0 else (statements - missing) * 100.0 / statements
        if covered + 0.005 < floor:
            findings.append(
                Finding(package, f"is at {covered:.2f}% and its floor is {floor:.2f}%")
            )
    return findings, len(FLOORS)


def main() -> int:
    """Run the gate and give back a shell exit status."""
    return run_gate("check_coverage", run)


if __name__ == "__main__":
    raise SystemExit(main())
