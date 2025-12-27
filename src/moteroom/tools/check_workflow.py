"""Check the workflow runs what this repository checks.

A gate that exists and is not wired into the build is worse than no gate,
because everybody believes it is running. So the workflow file is read and
compared against the gates that are actually in the tools package, both ways
round: nothing missing, and nothing named that is not there.
"""

from __future__ import annotations

from pathlib import Path

from moteroom.tools.gate import REPO_ROOT, Finding, report

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYTHON_VERSIONS = ("3.12", "3.13")
REQUIRED_STEPS = ("ruff check", "ruff format --check", "mypy", "pytest", "--cov=moteroom")


def gate_modules() -> list[str]:
    """Every check module in the tools package."""
    here = Path(__file__).resolve().parent
    return sorted(path.stem for path in here.glob("check_*.py"))


def run() -> tuple[list[Finding], int]:
    """Read the workflow and compare it against what the repository has."""
    findings: list[Finding] = []
    if not WORKFLOW.exists():
        return [Finding("ci.yml", "there is no workflow")], 0
    text = WORKFLOW.read_text(encoding="utf-8")
    for module in [*gate_modules(), "release_check"]:
        if f"moteroom.tools.{module}" not in text:
            findings.append(Finding(module, "is a gate the workflow does not run"))
    for named in _named_gates(text):
        if named not in {*gate_modules(), "release_check"}:
            findings.append(Finding(named, "is run by the workflow and does not exist"))
    for step in REQUIRED_STEPS:
        if step not in text:
            findings.append(Finding(step, "is not in the workflow"))
    for version in PYTHON_VERSIONS:
        if f'"{version}"' not in text:
            findings.append(Finding(version, "is not tested by the workflow"))
    return findings, len(gate_modules())


def _named_gates(text: str) -> list[str]:
    found = []
    for line in text.splitlines():
        marker = "python -m moteroom.tools."
        if marker in line:
            found.append(line.split(marker, 1)[1].strip())
    return found


def main() -> int:
    """Run the gate and give back a shell exit status."""
    findings, checked = run()
    return report("check_workflow", findings, checked)


if __name__ == "__main__":
    raise SystemExit(main())
