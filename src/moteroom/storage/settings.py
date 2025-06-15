"""Plant settings.

A handful of values that belong to the plant rather than to a season: the gin
code the press stamps, the classing office the cards come from, the warehouse
the bales go to. They live in the book so a copy of the book is a complete
record, and each one is validated on the way in rather than on the way out.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date

from moteroom.core.errors import NotFoundError, ValidationError
from moteroom.core.ids import GinCode
from moteroom.core.money import CentsPerPound

GIN_CODE = "gin_code"
CLASSING_OFFICE = "classing_office"
WAREHOUSE = "warehouse"
BASE_LOAN_RATE = "base_loan_rate"


def _check_gin_code(value: str) -> str:
    return str(GinCode.parse(value))


def _check_office(value: str) -> str:
    cleaned = value.strip().upper()
    if not cleaned.isalpha() or not 3 <= len(cleaned) <= 8:
        raise ValidationError(CLASSING_OFFICE, f"{value!r} is not an office name")
    return cleaned


def _check_warehouse(value: str) -> str:
    cleaned = value.strip().upper()
    if not cleaned.isalnum() or not 4 <= len(cleaned) <= 8:
        raise ValidationError(WAREHOUSE, f"{value!r} is not a warehouse code")
    return cleaned


def _check_rate(value: str) -> str:
    return str(CentsPerPound.parse(value).cents)


KNOWN: dict[str, Callable[[str], str]] = {
    GIN_CODE: _check_gin_code,
    CLASSING_OFFICE: _check_office,
    WAREHOUSE: _check_warehouse,
    BASE_LOAN_RATE: _check_rate,
}


class SettingsRepository:
    """The settings table, with a validator per name."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def set(self, name: str, value: str, changed_on: date) -> str:
        """Write a setting, refusing a name nobody knows or a bad value."""
        if name not in KNOWN:
            raise ValidationError("setting", f"{name!r} is not a setting this plant has")
        cleaned = KNOWN[name](value)
        self.connection.execute(
            "INSERT INTO settings (name, value, changed_on) VALUES (?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET value = excluded.value, "
            "changed_on = excluded.changed_on",
            (name, cleaned, changed_on.isoformat()),
        )
        return cleaned

    def get(self, name: str) -> str:
        row = self.connection.execute(
            "SELECT value FROM settings WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise NotFoundError("setting", name)
        return str(row["value"])

    def get_or(self, name: str, fallback: str) -> str:
        try:
            return self.get(name)
        except NotFoundError:
            return fallback

    def gin_code(self) -> GinCode:
        return GinCode(self.get(GIN_CODE))

    def base_rate(self) -> CentsPerPound:
        return CentsPerPound.parse(self.get(BASE_LOAN_RATE))

    def all(self) -> list[tuple[str, str]]:
        rows = self.connection.execute("SELECT name, value FROM settings ORDER BY name")
        return [(row["name"], row["value"]) for row in rows]

    def missing(self) -> list[str]:
        """Settings the plant has not filled in yet."""
        held = {name for name, _ in self.all()}
        return sorted(set(KNOWN) - held)
