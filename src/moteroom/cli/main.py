"""The command tree.

Commands are grouped the way the work is: cotton comes in, it is ginned, it is
pressed, it is classed, it goes to a warehouse, and somebody gets paid. Every
command takes the book and the season off the root group rather than asking
for them again.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import click

from moteroom import __version__
from moteroom.cli.classing import card
from moteroom.cli.context import DEFAULT_BOOK, Session
from moteroom.cli.contracts import contract
from moteroom.cli.ginning import lot
from moteroom.cli.loans import loan
from moteroom.cli.options import read_date
from moteroom.cli.press import bale
from moteroom.cli.producers import producer
from moteroom.cli.receiving import ticket
from moteroom.cli.reports import report
from moteroom.cli.settings import setting
from moteroom.cli.settling import settle
from moteroom.cli.trail import audit
from moteroom.cli.warehousing import order, receipt
from moteroom.core.errors import MoteroomError
from moteroom.service import closing, doctor, export
from moteroom.storage.backup import backup, verify
from moteroom.storage.maintenance import compact, measure, table_sizes
from moteroom.storage.migrations import LATEST


@click.group()
@click.option(
    "--book",
    envvar="MOTEROOM_BOOK",
    default=DEFAULT_BOOK,
    show_default=True,
    type=click.Path(path_type=Path),
    help="The sqlite book to work against.",
)
@click.option(
    "--season",
    envvar="MOTEROOM_SEASON",
    default=None,
    help="Crop year, such as 2025 or 2025/26. Defaults to the one open today.",
)
@click.version_option(__version__, prog_name="moteroom")
@click.pass_context
def main(ctx: click.Context, book: Path, season: str | None) -> None:
    """Lot accounting for a cotton gin."""
    ctx.obj = Session.build(book, season, date.today())
    ctx.call_on_close(ctx.obj.close)


@main.command()
@click.option("--full", is_flag=True, help="Add the settings and the seasons.")
@click.pass_obj
def about(session: Session, full: bool) -> None:
    """Say which book this is and what is in it."""
    click.echo(f"moteroom {__version__}")
    click.echo(f"book     {session.book_path}")
    click.echo(f"season   {session.season}")
    if not session.exists():
        click.echo("state    no book yet, it will be made on first write")
        return
    opened = session.book()
    click.echo(f"schema   {opened.version} of {LATEST}")
    size = measure(opened, session.book_path)
    click.echo(f"size     {size.reads()}")
    if not full:
        for table in opened.tables():
            click.echo(f"  {table:<16} {opened.count(table)}")
        return
    repos = session.open_repos()
    click.echo()
    click.echo("settings")
    for name, value in repos.settings.all():
        click.echo(f"  {name:<16} {value}")
    for name in repos.settings.missing():
        click.echo(f"  {name:<16} not set")
    click.echo()
    click.echo("seasons")
    for held in repos.seasons.all():
        marker = "*" if held.season == session.season else " "
        click.echo(f" {marker} {held}")
    if not repos.seasons.years():
        click.echo("   nothing in this book yet")
    click.echo()
    click.echo("this season")
    tickets = repos.tickets.book(session.season)
    click.echo(f"  producers        {len(tickets.producers())}")
    click.echo(f"  modules          {len(tickets)}")
    click.echo(f"  seed cotton      {tickets.net()}")
    click.echo(f"  lots             {len(repos.lots.for_season(session.season))}")
    click.echo(f"  bales            {len(repos.bales.for_season(session.season))}")
    click.echo(f"  cards            {len(repos.cards.for_season(session.season))}")
    click.echo(f"  in store         {len(repos.receipts.outstanding())}")
    click.echo(f"  settled          {len(repos.statements.for_season(session.season))}")


@main.command()
@click.pass_obj
def init(session: Session) -> None:
    """Make the book if it is not there and bring it up to date."""
    existed = session.exists()
    opened = session.book()
    state = "opened" if existed else "created"
    click.echo(f"{state} {session.book_path} at schema {opened.version}")


main.add_command(producer)
main.add_command(ticket)
main.add_command(lot)
main.add_command(setting)
main.add_command(bale)
main.add_command(card)
main.add_command(receipt)
main.add_command(order)
main.add_command(settle)
main.add_command(report)
main.add_command(loan)
main.add_command(contract)
main.add_command(audit)


@main.command("backup")
@click.argument("target", type=click.Path(path_type=Path))
@click.pass_obj
def take_backup(session: Session, target: Path) -> None:
    """Copy the book somewhere safe, through sqlite rather than the filesystem."""
    book = session.require_book()
    made = backup(book, target)
    click.echo(f"copied {session.book_path} to {made}")


@main.command("verify")
@click.argument("target", type=click.Path(path_type=Path), required=False)
@click.pass_obj
def verify_book(session: Session, target: Path | None) -> None:
    """Ask sqlite whether a book is intact."""
    verdict = verify(target or session.book_path)
    click.echo(str(verdict))
    if not verdict.is_sound:
        raise SystemExit(1)


@main.command("analyse")
@click.pass_obj
def analyse_book(session: Session) -> None:
    """Let sqlite look at the tables so its planner stops guessing."""
    book = session.require_book()
    book.analyse()
    click.echo(f"analysed {session.book_path}")
    for table, rows in table_sizes(book).items():
        if rows:
            click.echo(f"  {table:<16} {rows}")


@main.command("compact")
@click.pass_obj
def compact_book(session: Session) -> None:
    """Hand back the pages a season's deletions left behind."""
    book = session.require_book()
    before, after = compact(book, session.book_path)
    click.echo(f"before  {before}")
    click.echo(f"after   {after}")
    click.echo(f"saved   {before.bytes - after.bytes} bytes")


@main.command("size")
@click.pass_obj
def show_size(session: Session) -> None:
    """How big the book is and which tables it went into."""
    book = session.require_book()
    size = measure(book, session.book_path)
    click.echo(str(size))
    if size.worth_compacting:
        click.echo("worth compacting")
    click.echo()
    for table, rows in table_sizes(book).items():
        if rows:
            click.echo(f"  {table:<16} {rows}")


@main.command("export")
@click.argument("into", type=click.Path(path_type=Path))
@click.option("--as-of", "as_of", default=None, help="Export date, Y-m-d.")
@click.pass_obj
def export_season(session: Session, into: Path, as_of: str | None) -> None:
    """Write the whole season out as files."""
    book = session.require_book()
    when = read_date(as_of, date.today())
    made = export.write(book, session.season, into, when)
    click.echo(str(made))
    for name in made.files:
        click.echo(f"  {name}")


@main.command("doctor")
@click.option("--as-of", "as_of", default=None, help="Date to look as at, Y-m-d.")
@click.pass_obj
def look_over(session: Session, as_of: str | None) -> None:
    """Look over the book and say whether anything is wrong."""
    book = session.require_book()
    when = read_date(as_of, date.today())
    notes = doctor.look(book, session.season, session.book_path, when)
    for note in notes:
        click.echo(str(note))
    click.echo()
    click.echo(f"the book is {doctor.worst(notes)}")
    if not doctor.is_sound(notes):
        raise SystemExit(1)


@main.command("seasons")
@click.pass_obj
def list_seasons(session: Session) -> None:
    """Every season this book holds and how much of each."""
    repos = session.open_repos()
    for held in repos.seasons.all():
        marker = "*" if held.season == session.season else " "
        click.echo(f"{marker} {held}")
    if not repos.seasons.years():
        click.echo("nothing in this book yet")


@main.command("close")
@click.pass_obj
def close(session: Session) -> None:
    """Say whether the season is finished with, and what is left if not."""
    book = session.require_book()
    made = closing.check(book, session.season)
    for check in made.checks:
        click.echo(str(check))
    click.echo()
    click.echo(str(made))
    if not made.can_close:
        raise SystemExit(1)


def run() -> int:
    """Entry point that turns our own errors into a message rather than a trace."""
    try:
        main.main(standalone_mode=False)
    except MoteroomError as exc:
        click.echo(f"error: {exc}", err=True)
        return 1
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except click.Abort:
        click.echo("aborted", err=True)
        return 1
    return 0
