"""Printing.

Everything this package prints is read on a terminal in a gin office by
somebody comparing it against a paper ticket, so columns line up and numbers
sit on the right. There is no colour and no box drawing: the output gets pasted
into emails and printed on a dot matrix often enough that plain text wins.
"""

from __future__ import annotations

from collections.abc import Sequence

GAP = "  "
EMPTY = "(nothing)"


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    right: Sequence[int] = (),
) -> str:
    """Lay rows out under headers, right aligning the columns named."""
    if not rows:
        return EMPTY
    widths = [len(header) for header in headers]
    for row in rows:
        if len(row) != len(headers):
            raise ValueError("a row does not match the headers")
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    lines = [_line(headers, widths, right), _rule(widths)]
    lines.extend(_line(row, widths, right) for row in rows)
    return "\n".join(lines)


def render_pairs(pairs: Sequence[tuple[str, str]]) -> str:
    """A block of name and value, which is how a single record prints."""
    if not pairs:
        return EMPTY
    width = max(len(name) for name, _ in pairs)
    return "\n".join(f"{name:<{width}}{GAP}{value}" for name, value in pairs)


def _line(cells: Sequence[str], widths: Sequence[int], right: Sequence[int]) -> str:
    parts = [
        cell.rjust(widths[index]) if index in right else cell.ljust(widths[index])
        for index, cell in enumerate(cells)
    ]
    return GAP.join(parts).rstrip()


def _rule(widths: Sequence[int]) -> str:
    return GAP.join("-" * width for width in widths)
