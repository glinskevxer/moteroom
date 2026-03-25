"""Check the package still layers the way it was built to.

The direction of every import is the design. Core knows nothing about anything.
The domain packages know core and each other. Storage knows the domain, and the
domain does not know storage. Reporting reads the domain and prints. Services
sit above storage and reporting both, because assembling a report out of the
book is exactly what a service is for. The command line is allowed to know
everything, because that is its job.

An import that runs the wrong way does not break a test. It quietly makes the
domain impossible to use without a database, which is the thing this package
was laid out to avoid.
"""

from __future__ import annotations

import ast

from moteroom.tools.gate import Finding, module_name, report, source_files

CORE = {"core"}
DOMAIN = {"receiving", "ginning", "press", "classing", "loan", "warehouse", "settlement"}

ALLOWED: dict[str, set[str]] = {
    "core": CORE,
    "receiving": CORE | DOMAIN,
    "ginning": CORE | DOMAIN,
    "press": CORE | DOMAIN,
    "classing": CORE | DOMAIN,
    "loan": CORE | DOMAIN,
    "warehouse": CORE | DOMAIN,
    "settlement": CORE | DOMAIN,
    "storage": CORE | DOMAIN | {"storage"},
    "reporting": CORE | DOMAIN | {"reporting"},
    "service": CORE | DOMAIN | {"storage", "reporting", "service"},
    "cli": CORE | DOMAIN | {"storage", "reporting", "service", "cli"},
    "tools": CORE | DOMAIN | {"storage", "reporting", "service", "cli", "tools"},
}

EXCEPTIONS: set[tuple[str, str]] = set()


def _package_of(dotted: str) -> str:
    parts = dotted.split(".")
    return parts[1] if len(parts) > 1 and parts[0] == "moteroom" else ""


def _imports(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append(node.module)
    return [name for name in found if name.startswith("moteroom")]


def run() -> tuple[list[Finding], int]:
    """Read every import in the package and check which way it runs."""
    findings: list[Finding] = []
    files = source_files()
    for path in files:
        name = module_name(path)
        package = _package_of(name)
        if package not in ALLOWED:
            continue
        short = name.removeprefix("moteroom.")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for imported in _imports(tree):
            target = _package_of(imported)
            if not target or target == package:
                continue
            if target in ALLOWED[package]:
                continue
            if (short, target) in EXCEPTIONS:
                continue
            findings.append(Finding(short, f"imports {target}, which is the wrong way round"))
    return findings, len(files)


def main() -> int:
    """Run the gate and give back a shell exit status."""
    findings, checked = run()
    return report("check_layers", findings, checked)


if __name__ == "__main__":
    raise SystemExit(main())
