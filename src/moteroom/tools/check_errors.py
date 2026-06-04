"""Check the errors all read the same way.

Every error this package raises ends up in front of somebody at a scale house
who is holding a truck up. They are all written the same way on purpose: the
field or the record first, then a lower case phrase saying what is wrong with
it, and no full stop, because the caller prints them inside its own sentence.

The rule is deliberately shallow. It reads the literal text of the message and
nothing else, so it cannot object to anything a person would defend.
"""

from __future__ import annotations

import ast

from moteroom.tools.gate import Finding, module_name, run_gate, source_files

# Which argument carries the phrase a person reads. NotFoundError has none: it
# takes a kind and a key and writes its own sentence.
MESSAGE_AT = {
    "ValidationError": 1,
    "ConflictError": 2,
    "MoteroomError": 0,
    "IneligibleError": 1,
    "MigrationError": 0,
}
ALLOWED_FIRST = "abcdefghijklmnopqrstuvwxyz{"


def _message(call: ast.Call, position: int) -> str | None:
    """The literal text of the message argument, if it is readable at all."""
    if len(call.args) <= position:
        return None
    node = call.args[position]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for piece in node.values:
            if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                parts.append(piece.value)
            else:
                parts.append("{}")
        return "".join(parts)
    return None


def run() -> tuple[list[Finding], int]:
    """Read every raise in the package and look at how it reads."""
    findings: list[Finding] = []
    files = source_files()
    for path in files:
        where = module_name(path).removeprefix("moteroom.")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            call = node.exc
            name = call.func.id if isinstance(call.func, ast.Name) else ""
            if name not in MESSAGE_AT:
                continue
            message = _message(call, MESSAGE_AT[name])
            if message is None:
                findings.append(
                    Finding(f"{where}:{node.lineno}", "raises a message nobody wrote")
                )
                continue
            if not message.strip():
                findings.append(Finding(f"{where}:{node.lineno}", "raises an empty message"))
                continue
            if message[0] not in ALLOWED_FIRST:
                findings.append(
                    Finding(f"{where}:{node.lineno}", f"{message!r} does not start lower case")
                )
            if message.rstrip().endswith("."):
                findings.append(
                    Finding(f"{where}:{node.lineno}", f"{message!r} ends with a full stop")
                )
    return findings, len(files)


def main() -> int:
    """Run the gate and give back a shell exit status."""
    return run_gate("check_errors", run)


if __name__ == "__main__":
    raise SystemExit(main())
