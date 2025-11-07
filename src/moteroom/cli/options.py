"""Options every command takes, declared once.

Nine commands take a date and describe it the same way, six of them read a
clock time or a report format, and all of that was written out at each call
site. A wording that drifts between two commands is a help page that lies
about one of them, so the wording lives here with the parsing.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time
from typing import Any, TypeVar

import click

from moteroom.core.errors import ValidationError

Command = TypeVar("Command", bound=Callable[..., Any])

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"


def read_date(text: str | None, fallback: date) -> date:
    """Read a date off the command line, defaulting to the day given."""
    if not text:
        return fallback
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except ValueError as exc:
        raise ValidationError("date", f"{text!r} is not a date") from exc


def read_time(text: str) -> time:
    """Read a clock time such as 07:00 off the command line."""
    try:
        return datetime.strptime(text.strip(), TIME_FORMAT).time()
    except ValueError as exc:
        raise ValidationError("time", f"{text!r} is not a time") from exc


def date_option(flag: str, target: str, what: str) -> Callable[[Command], Command]:
    """A date option, worded the same way wherever it appears."""
    return click.option(
        flag, target, default=None, help=f"{what}, {DATE_FORMAT.replace('%', '')}."
    )


def on_option(what: str) -> Callable[[Command], Command]:
    """The ``--on`` option, which most commands carry."""
    return date_option("--on", "on_text", what)


def as_of_option(what: str) -> Callable[[Command], Command]:
    """The ``--as-of`` option, for anything read as at a date."""
    return date_option("--as-of", "as_of", what)


def csv_option(command: Command) -> Command:
    """The ``--csv`` flag every report carries."""
    return click.option("--csv", "csv_out", is_flag=True, help="Comma separated instead.")(
        command
    )
