"""What a report is.

A report is data, not text. It carries its title, its columns, its rows and
whatever notes belong under it, and something else turns that into characters.
That split is what lets the same report print on a terminal, go into a csv and
be asserted against in a test without three copies of the arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from moteroom.core.errors import ValidationError


@dataclass(frozen=True)
class Report:
    """One report: a title, a table and some notes."""

    title: str
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    right: tuple[int, ...] = field(default=())
    notes: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValidationError("title", "is blank")
        if not self.headers:
            raise ValidationError("headers", "a report has to have columns")
        for row in self.rows:
            if len(row) != len(self.headers):
                raise ValidationError("rows", f"a row has {len(row)} of {len(self.headers)}")
        for index in self.right:
            if not 0 <= index < len(self.headers):
                raise ValidationError("right", f"column {index} is not in this report")

    @property
    def is_empty(self) -> bool:
        return not self.rows

    @property
    def width(self) -> int:
        return len(self.headers)

    def column(self, name: str) -> list[str]:
        """One column by name, which is what a test usually wants."""
        if name not in self.headers:
            raise ValidationError("column", f"{name!r} is not in this report")
        index = self.headers.index(name)
        return [row[index] for row in self.rows]

    def to_csv(self) -> str:
        """The same table as comma separated values, headers included."""
        lines = [",".join(_quote(cell) for cell in self.headers)]
        lines.extend(",".join(_quote(cell) for cell in row) for row in self.rows)
        return "\n".join(lines)


def _quote(cell: str) -> str:
    if any(character in cell for character in ',"\n'):
        escaped = cell.replace('"', '""')
        return f'"{escaped}"'
    return cell
