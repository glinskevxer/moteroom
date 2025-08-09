"""Settings commands: reading and writing the plant's own values."""

from __future__ import annotations

from datetime import date

import click

from moteroom.cli.context import Session
from moteroom.cli.output import render_table
from moteroom.storage.settings import KNOWN, SettingsRepository


@click.group()
def setting() -> None:
    """Values that belong to the plant rather than to a season."""


@setting.command("set")
@click.argument("name")
@click.argument("value")
@click.pass_obj
def set_setting(session: Session, name: str, value: str) -> None:
    """Write one setting."""
    book = session.book()
    with book.transaction() as conn:
        cleaned = SettingsRepository(conn).set(name.strip().lower(), value, date.today())
    click.echo(f"{name.strip().lower()} is {cleaned}")


@setting.command("get")
@click.argument("name")
@click.pass_obj
def get_setting(session: Session, name: str) -> None:
    """Read one setting."""
    book = session.require_book()
    click.echo(SettingsRepository(book.connection).get(name.strip().lower()))


@setting.command("list")
@click.pass_obj
def list_settings(session: Session) -> None:
    """Every setting, and what is still missing."""
    book = session.require_book()
    held = SettingsRepository(book.connection)
    values = dict(held.all())
    rows = [[name, values.get(name, "-")] for name in sorted(KNOWN)]
    click.echo(render_table(["setting", "value"], rows))
    missing = held.missing()
    if missing:
        click.echo()
        click.echo(f"not set yet: {', '.join(missing)}")
