"""Audit commands: what has been done to this book."""

from __future__ import annotations

import click

from moteroom.cli.context import Session
from moteroom.cli.output import render_table
from moteroom.storage.audit import AuditRepository


@click.group()
def audit() -> None:
    """The trail of everything that wrote to the book."""


@audit.command("list")
@click.option("--limit", type=int, default=20, show_default=True, help="How many lines.")
@click.pass_obj
def list_entries(session: Session, limit: int) -> None:
    """The most recent things done, newest first."""
    book = session.require_book()
    entries = AuditRepository(book.connection).entries(session.season, limit)
    rows = [
        [
            entry.at.isoformat(sep=" ", timespec="minutes"),
            entry.action,
            entry.subject,
            entry.detail,
        ]
        for entry in entries
    ]
    click.echo(render_table(["when", "action", "subject", "detail"], rows))


@audit.command("subject")
@click.argument("subject")
@click.pass_obj
def show_subject(session: Session, subject: str) -> None:
    """Everything ever done to one ticket, lot or bale."""
    book = session.require_book()
    entries = AuditRepository(book.connection).for_subject(subject.strip().upper())
    rows = [
        [entry.at.isoformat(sep=" ", timespec="minutes"), entry.action, entry.detail]
        for entry in entries
    ]
    click.echo(render_table(["when", "action", "detail"], rows))


@audit.command("actions")
@click.pass_obj
def count_actions(session: Session) -> None:
    """How often each action has been run this season."""
    book = session.require_book()
    trail = AuditRepository(book.connection)
    rows = [[action, str(count)] for action, count in trail.actions(session.season).items()]
    click.echo(render_table(["action", "times"], rows, right=(1,)))
    click.echo()
    click.echo(f"{trail.count(session.season)} entries")
