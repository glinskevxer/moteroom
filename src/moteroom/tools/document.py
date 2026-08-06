"""A document generated out of the code, and the gate that keeps it true.

Three documents are written this way now: the glossary, the architecture and
the command list. Each of them was carrying the same four things, one of which
is the argument parsing, and three copies of argument parsing is how one of
them ends up writing when it was asked to check.

So the pattern lives here. A generated document says where it goes and how to
render it, and everything else is the same for all of them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from moteroom.tools.gate import Finding, run_gate

WRITE = "--write"


@dataclass(frozen=True)
class Generated:
    """One document written out of the code."""

    name: str
    path: Path
    render: Callable[[], str]
    counted: Callable[[], int]

    def check(self) -> tuple[list[Finding], int]:
        """Whether what is written matches what the code says."""
        if not self.path.exists():
            return [Finding(self.path.name, "has not been generated yet")], self.counted()
        if self.path.read_text(encoding="utf-8") != self.render():
            return (
                [Finding(self.path.name, f"is out of date, run with {WRITE}")],
                self.counted(),
            )
        return [], self.counted()

    def write(self) -> Path:
        """Bring the document up to date."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.render(), encoding="utf-8")
        return self.path

    def main(self, argv: list[str]) -> int:
        """Check the document, or write it when the arguments say to."""
        if WRITE in argv:
            print(f"wrote {self.write()}")
            return 0
        return run_gate(self.name, self.check)
