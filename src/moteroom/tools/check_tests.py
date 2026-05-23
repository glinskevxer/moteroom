"""Check every module has tests of its own.

Coverage says how many lines ran. It does not say which module was never
thought about, because a module can be fully covered by the tests of the module
above it and still have nobody asking whether it is right.

So this asks a different question: does every module have a test module named
after it. That is a weaker claim than coverage and it catches a different
thing, which is why both are run.
"""

from __future__ import annotations

from pathlib import Path

from moteroom.tools.gate import PACKAGE_ROOT, REPO_ROOT, Finding, module_name, report

TESTS = REPO_ROOT / "tests"
EXEMPT = {
    "moteroom",
    "moteroom.core",
    "moteroom.receiving",
    "moteroom.ginning",
    "moteroom.press",
    "moteroom.classing",
    "moteroom.loan",
    "moteroom.warehouse",
    "moteroom.settlement",
    "moteroom.storage",
    "moteroom.service",
    "moteroom.reporting",
    "moteroom.cli",
    "moteroom.tools",
}
RENAMED = {
    "moteroom.service.settlement": "tests/service/test_settlement.py",
    "moteroom.reporting.settlement": "tests/reporting/test_settlement_report.py",
    "moteroom.reporting.season": "tests/reporting/test_season_report.py",
    "moteroom.cli.trail": "tests/cli/test_trail.py",
    "moteroom.reporting.freight": "tests/reporting/test_freight_report.py",
}


def expected_test(name: str) -> Path:
    """Where the tests for a module should live."""
    if name in RENAMED:
        return REPO_ROOT / RENAMED[name]
    parts = name.removeprefix("moteroom.").split(".")
    return TESTS.joinpath(*parts[:-1], f"test_{parts[-1]}.py")


def modules() -> list[str]:
    """Every module that is expected to carry tests."""
    found = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        name = module_name(path)
        if name in EXEMPT:
            continue
        found.append(name)
    return found


def run() -> tuple[list[Finding], int]:
    """Look for a test module against every module in the package."""
    findings: list[Finding] = []
    names = modules()
    for name in names:
        wanted = expected_test(name)
        if not wanted.exists():
            findings.append(
                Finding(
                    name.removeprefix("moteroom."),
                    f"has no tests at {wanted.relative_to(REPO_ROOT)}",
                )
            )
    return findings, len(names)


def main() -> int:
    """Run the gate and give back a shell exit status."""
    findings, checked = run()
    return report("check_tests", findings, checked)


if __name__ == "__main__":
    raise SystemExit(main())
