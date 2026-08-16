"""Check the things that only matter when somebody installs this.

Three questions nobody asks until a release is wrong. Does the package say the
same version in both places it says it? Does the changelog mention that
version? And would the wheel carry the files that make the package work at all,
which here means the typing marker and the command entry point.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from moteroom import __version__
from moteroom.tools.gate import PACKAGE_ROOT, REPO_ROOT, Finding, run_gate

PYPROJECT = REPO_ROOT / "pyproject.toml"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
ENTRY_POINT = "moteroom.cli.main:main"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
PACKAGED = ("py.typed", "__init__.py", "cli/main.py")


def _pyproject() -> dict[str, object]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def run() -> tuple[list[Finding], int]:
    """Read the packaging metadata and compare it against the package."""
    findings: list[Finding] = []
    if not PYPROJECT.exists():
        return [Finding("pyproject.toml", "is not there")], 0
    data = _pyproject()
    project = data.get("project")
    if not isinstance(project, dict):
        return [Finding("pyproject.toml", "has no project table")], 1

    declared = str(project.get("version", ""))
    if not VERSION_PATTERN.match(declared):
        findings.append(Finding("version", f"{declared!r} is not three numbers"))
    if declared != __version__:
        findings.append(
            Finding("version", f"pyproject says {declared} and the package says {__version__}")
        )

    scripts = project.get("scripts")
    if not isinstance(scripts, dict) or scripts.get("moteroom") != ENTRY_POINT:
        findings.append(Finding("scripts", f"the moteroom command should be {ENTRY_POINT}"))

    if not (PACKAGE_ROOT / "py.typed").exists():
        findings.append(Finding("py.typed", "is missing, so installs lose their types"))

    if not CHANGELOG.exists():
        findings.append(Finding("CHANGELOG.md", "is not there"))
    elif f"## {declared}" not in CHANGELOG.read_text(encoding="utf-8"):
        findings.append(Finding("CHANGELOG.md", f"has no entry for {declared}"))

    dependencies = project.get("dependencies")
    if isinstance(dependencies, list):
        for requirement in dependencies:
            if "==" not in str(requirement):
                findings.append(Finding(str(requirement), "is not pinned exactly"))

    extras = project.get("optional-dependencies")
    if not isinstance(extras, dict) or "dev" not in extras:
        findings.append(Finding("optional-dependencies", "has no dev extra to install from"))
    elif isinstance(extras["dev"], list):
        for requirement in extras["dev"]:
            if "==" not in str(requirement):
                findings.append(Finding(str(requirement), "is not pinned exactly"))

    if str(project.get("requires-python", "")) < ">=3.12":
        findings.append(Finding("requires-python", "does not say which pythons this runs on"))

    for name in PACKAGED:
        if not (PACKAGE_ROOT / name).exists():
            findings.append(Finding(name, "is expected in the wheel and is not there"))

    if declared != "0.0.0" and _first_entry(CHANGELOG) != declared:
        findings.append(Finding("CHANGELOG.md", f"does not open with {declared}"))
    return findings, len(PACKAGED) + 5


def _first_entry(path: Path) -> str:
    """The version the changelog opens with, which should be this one."""
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            return line.removeprefix("## ").strip()
    return ""


def main() -> int:
    """Run the gate and give back a shell exit status."""
    return run_gate("release_check", run)


if __name__ == "__main__":
    raise SystemExit(main())
