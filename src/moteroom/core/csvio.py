"""Reading and writing the csv files the office actually exchanges.

Scale tickets arrive as a spreadsheet export from the weighbridge software, and
half the columns are in a different order every season because somebody dragged
one. So a file is read by header name rather than by position, headers are
matched case insensitively with the spaces taken out, and a missing column is
named rather than producing a row of nothing.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence

from moteroom.core.errors import ValidationError


def normalise(name: str) -> str:
    """A header as it will be matched: lower case, no spaces or underscores."""
    return name.strip().lower().replace(" ", "").replace("_", "")


def read_rows(text: str, required: Sequence[str]) -> list[dict[str, str]]:
    """Read a csv by header name, refusing a file missing a column."""
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        raise ValidationError("csv", "the file is empty") from None
    columns = [normalise(name) for name in header]
    if len(set(columns)) != len(columns):
        raise ValidationError("csv", "two columns have the same name")
    missing = [name for name in required if normalise(name) not in columns]
    if missing:
        raise ValidationError("csv", f"is missing {', '.join(missing)}")
    rows: list[dict[str, str]] = []
    for number, values in enumerate(reader, start=2):
        if not any(value.strip() for value in values):
            continue
        if len(values) != len(columns):
            raise ValidationError("csv", f"row {number} has {len(values)} of {len(columns)}")
        rows.append(dict(zip(columns, (value.strip() for value in values), strict=True)))
    return rows


def field(row: dict[str, str], name: str) -> str:
    """One column out of a row, by the name the caller knows it as."""
    key = normalise(name)
    if key not in row:
        raise ValidationError("csv", f"has no column {name}")
    return row[key]


def write_rows(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    """Write a csv the same way every report does."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        if len(row) != len(headers):
            raise ValidationError("csv", "a row does not match the headers")
        writer.writerow(row)
    return out.getvalue()
