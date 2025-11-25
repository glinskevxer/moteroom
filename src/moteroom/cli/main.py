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
from moteroom.cli.press import bale
from moteroom.cli.producers import producer
from moteroom.cli.receiving import ticket
from moteroom.cli.reports import report
from moteroom.cli.settings import setting
from moteroom.cli.settling import settle
from moteroom.cli.trail import audit
from moteroom.cli.warehousing import order, receipt
from moteroom.core.errors import MoteroomError
from moteroom.service import closing
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
@click.pass_obj
def about(session: Session) -> None:
    """Say which book this is and what is in it."""
    click.echo(f"moteroom {__version__}")
    click.echo(f"book     {session.book_path}")
    click.echo(f"season   {session.season}")
    if not session.exists():
        click.echo("state    no book yet, it will be made on first write")
        return
    opened = session.book()
    click.echo(f"schema   {opened.version} of {LATEST}")
    for table in opened.tables():
        click.echo(f"  {table:<16} {opened.count(table)}")


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
