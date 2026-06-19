"""Reading a column back into the type it went in as.

Sqlite has five types and this package has twenty. Every repository was
writing the same three conversions by hand, and the one that matters is the
nullable date: `date.fromisoformat(row["x"])` on a null throws, so every one
of them carried its own conditional and one of them was going to be missed.

They are all here, they all name the column in the error, and the nullable one
is a different function so it cannot be reached by accident.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation

from moteroom.core.errors import ValidationError
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.weight import Weight


def text(row: sqlite3.Row, column: str) -> str:
    """A column as text, refusing a null."""
    value = row[column]
    if value is None:
        raise ValidationError(column, "is null and the record needs it")
    return str(value)


def number(row: sqlite3.Row, column: str) -> int:
    """A column as a whole number."""
    return int(text(row, column))


def money(row: sqlite3.Row, column: str) -> Money:
    """A column as money, which is stored as its exact decimal text."""
    try:
        return Money(Decimal(text(row, column)))
    except InvalidOperation as exc:
        raise ValidationError(column, f"{row[column]!r} is not money") from exc


def rate(row: sqlite3.Row, column: str) -> CentsPerPound:
    """A column as a cents per pound rate."""
    try:
        return CentsPerPound(Decimal(text(row, column)))
    except InvalidOperation as exc:
        raise ValidationError(column, f"{row[column]!r} is not a rate") from exc


def weight(row: sqlite3.Row, column: str) -> Weight:
    """A column as a weight in pounds."""
    return Weight(number(row, column))


def day(row: sqlite3.Row, column: str) -> date:
    """A column as a date, refusing a null."""
    try:
        return date.fromisoformat(text(row, column))
    except ValueError as exc:
        raise ValidationError(column, f"{row[column]!r} is not a date") from exc


def maybe_day(row: sqlite3.Row, column: str) -> date | None:
    """A column as a date that is allowed to be missing."""
    return None if row[column] is None else day(row, column)


def maybe_money(row: sqlite3.Row, column: str) -> Money | None:
    """A column as money that is allowed to be missing."""
    return None if row[column] is None else money(row, column)


def maybe_rate(row: sqlite3.Row, column: str) -> CentsPerPound | None:
    """A column as a rate that is allowed to be missing."""
    return None if row[column] is None else rate(row, column)


def flag(row: sqlite3.Row, column: str) -> bool:
    """A column as a yes or no, which sqlite keeps as a number."""
    return bool(number(row, column))
