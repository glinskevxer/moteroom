"""Lot commands.

Ginning a lot is the one place where the seed cotton weight is not typed in.
It is the sum of the tickets the lot names, because a lot whose weight
disagrees with its own tickets is a lot nobody can settle off.
"""

from __future__ import annotations

import click

from moteroom.cli.context import Session
from moteroom.cli.output import render_pairs, render_table
from moteroom.cli.receiving import read_date
from moteroom.core.errors import ConflictError, ValidationError
from moteroom.core.ids import LotId
from moteroom.core.weight import Weight, total
from moteroom.ginning.reconcile import reconcile
from moteroom.ginning.run import GinRun
from moteroom.ginning.turnout import summarise
from moteroom.storage.lots import BaleRepository, LotRepository
from moteroom.storage.tickets import TicketRepository


def read_tickets(text: str) -> tuple[int, ...]:
    """Read a ticket list such as ``1,2,3`` off the command line."""
    numbers: list[int] = []
    for part in text.split(","):
        cleaned = part.strip()
        if not cleaned.isdigit():
            raise ValidationError("tickets", f"{part.strip()!r} is not a ticket number")
        numbers.append(int(cleaned))
    if not numbers:
        raise ValidationError("tickets", "a lot has to gin something")
    return tuple(numbers)


@click.group()
def lot() -> None:
    """Running lots through the plant."""


@lot.command("gin")
@click.argument("tickets")
@click.option("--lint", required=True, help="Lint pounds off the lot.")
@click.option("--seed", required=True, help="Seed pounds off the lot.")
@click.option("--motes", default="0", show_default=True, help="Mote room pounds.")
@click.option("--on", "ginned_on", default=None, help="Gin date, YYYY-MM-DD.")
@click.pass_obj
def gin(
    session: Session,
    tickets: str,
    lint: str,
    seed: str,
    motes: str,
    ginned_on: str | None,
) -> None:
    """Gin a set of tickets as one lot."""
    book = session.require_book()
    numbers = read_tickets(tickets)
    with book.transaction() as conn:
        ticket_repo = TicketRepository(conn)
        lots = LotRepository(conn)
        held = ticket_repo.book(session.season)
        already = lots.assigned_tickets(session.season)
        weights: list[Weight] = []
        for number in numbers:
            one = ticket_repo.get(session.season, number)
            if held.is_voided(number):
                raise ConflictError("ticket", str(number), "was voided")
            if number in already:
                raise ConflictError("ticket", str(number), "is already in a lot")
            weights.append(one.net)
        run = GinRun(
            lot=LotId(session.season, lots.next_number(session.season)),
            ginned_on=read_date(ginned_on, session.season.start),
            tickets=numbers,
            seed_cotton=total(weights),
            lint=Weight.parse(lint),
            seed=Weight.parse(seed),
            motes=Weight.parse(motes),
        )
        lots.add(run)
    click.echo(f"lot {run.lot} ginned {run.seed_cotton} into {run.lint} of lint")


@lot.command("list")
@click.pass_obj
def list_lots(session: Session) -> None:
    """Every lot this season with its turnout."""
    book = session.require_book()
    lots = LotRepository(book.connection)
    rows = []
    for run in lots.for_season(session.season):
        line = summarise(run)
        rows.append(
            [
                str(run.lot),
                run.ginned_on.isoformat(),
                str(line.modules),
                str(run.seed_cotton.pounds),
                str(run.lint.pounds),
                f"{line.lint_turnout}",
                line.band,
            ]
        )
    click.echo(
        render_table(
            ["lot", "ginned", "modules", "seed cotton", "lint", "turnout", "band"],
            rows,
            right=(2, 3, 4, 5),
        )
    )


@lot.command("show")
@click.argument("number", type=int)
@click.pass_obj
def show_lot(session: Session, number: int) -> None:
    """One lot, with its turnout and how the press compared."""
    book = session.require_book()
    lots = LotRepository(book.connection)
    run = lots.get(LotId(session.season, number))
    line = summarise(run)
    bales = BaleRepository(book.connection).for_lot(run.lot)
    pressed = total([bale.net for bale in bales])
    check = reconcile(run, pressed, len(bales))
    click.echo(
        render_pairs(
            [
                ("lot", str(run.lot)),
                ("ginned", run.ginned_on.isoformat()),
                ("tickets", ",".join(str(t) for t in run.tickets)),
                ("seed cotton", str(run.seed_cotton)),
                ("lint", str(run.lint)),
                ("seed", str(run.seed)),
                ("motes", str(run.motes)),
                ("turnout", f"{line.lint_turnout}% {line.band}"),
                ("bales", str(len(bales))),
                ("pressed", str(pressed)),
                ("drift", f"{check.drift}%" if bales else "no bales yet"),
                ("closed", "yes" if lots.is_closed(run.lot) else "no"),
            ]
        )
    )


@lot.command("close")
@click.argument("number", type=int)
@click.pass_obj
def close_lot(session: Session, number: int) -> None:
    """Say a lot is off the press."""
    book = session.require_book()
    target = LotId(session.season, number)
    with book.transaction() as conn:
        lots = LotRepository(conn)
        if lots.is_closed(target):
            raise ConflictError("lot", str(target), "is already closed")
        lots.close(target)
    click.echo(f"lot {target} closed")
