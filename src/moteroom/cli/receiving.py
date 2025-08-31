"""Scale house commands."""

from __future__ import annotations

from datetime import date, datetime

import click

from moteroom.cli.context import Session
from moteroom.cli.output import render_pairs, render_table
from moteroom.core.errors import ValidationError
from moteroom.core.ids import ModuleId
from moteroom.core.weight import Weight
from moteroom.receiving.ticket import ModuleTicket, clean_moisture
from moteroom.receiving.yard import ModuleYard
from moteroom.storage.lots import LotRepository
from moteroom.storage.tickets import TicketRepository


def read_date(text: str | None, fallback: date) -> date:
    """Read a date off the command line, defaulting to the day given."""
    if not text:
        return fallback
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError("date", f"{text!r} is not a date") from exc


@click.group()
def ticket() -> None:
    """Weighing modules in at the scale."""


@ticket.command("weigh")
@click.argument("module")
@click.argument("producer")
@click.argument("farm")
@click.argument("gross")
@click.argument("tare")
@click.option("--moisture", default="7.5", show_default=True, help="Probe reading.")
@click.option("--on", "weighed_on", default=None, help="Weigh date, YYYY-MM-DD.")
@click.pass_obj
def weigh(
    session: Session,
    module: str,
    producer: str,
    farm: str,
    gross: str,
    tare: str,
    moisture: str,
    weighed_on: str | None,
) -> None:
    """Write a scale ticket for one module."""
    book = session.book()
    day = read_date(weighed_on, session.season.start)
    if not session.season.contains(day):
        raise ValidationError("on", f"{day} is outside {session.season}")
    with book.transaction() as conn:
        tickets = TicketRepository(conn)
        held = tickets.book(session.season)
        number = tickets.next_number(session.season)
        written = ModuleTicket(
            number=number,
            module=ModuleId.parse(module),
            producer=producer.strip().upper(),
            farm=farm.strip(),
            weighed_on=day,
            gross=Weight.parse(gross),
            tare=Weight.parse(tare),
            moisture=clean_moisture(moisture),
        )
        held.add(written)
        tickets.add(written)
    click.echo(f"ticket {number} {written.module} {written.net}")


@ticket.command("correct")
@click.argument("number", type=int)
@click.argument("gross")
@click.argument("tare")
@click.pass_obj
def correct(session: Session, number: int, gross: str, tare: str) -> None:
    """Void a ticket by writing the corrected one."""
    book = session.require_book()
    with book.transaction() as conn:
        tickets = TicketRepository(conn)
        wrong = tickets.get(session.season, number)
        replacement = ModuleTicket(
            number=tickets.next_number(session.season),
            module=wrong.module,
            producer=wrong.producer,
            farm=wrong.farm,
            weighed_on=wrong.weighed_on,
            gross=Weight.parse(gross),
            tare=Weight.parse(tare),
            moisture=wrong.moisture,
            voids=number,
        )
        tickets.book(session.season).add(replacement)
        tickets.add(replacement)
    click.echo(f"ticket {replacement.number} voids {number}")


@ticket.command("list")
@click.option("--producer", default=None, help="Only this grower's tickets.")
@click.pass_obj
def list_tickets(session: Session, producer: str | None) -> None:
    """Every live ticket this season."""
    book = session.require_book()
    held = TicketRepository(book.connection).book(session.season)
    rows = [
        [
            str(one.number),
            str(one.module),
            one.producer,
            one.farm,
            one.weighed_on.isoformat(),
            str(one.net.pounds),
        ]
        for one in held.live()
        if producer is None or one.producer == producer.strip().upper()
    ]
    click.echo(
        render_table(
            ["ticket", "module", "producer", "farm", "weighed", "net"], rows, right=(0, 5)
        )
    )


@ticket.command("show")
@click.argument("number", type=int)
@click.pass_obj
def show_ticket(session: Session, number: int) -> None:
    """One ticket, with what it weighed and whether it still counts."""
    book = session.require_book()
    tickets = TicketRepository(book.connection)
    one = tickets.get(session.season, number)
    held = tickets.book(session.season)
    click.echo(
        render_pairs(
            [
                ("ticket", str(one.number)),
                ("module", str(one.module)),
                ("producer", one.producer),
                ("farm", one.farm),
                ("weighed", one.weighed_on.isoformat()),
                ("gross", str(one.gross)),
                ("tare", str(one.tare)),
                ("net", str(one.net)),
                ("moisture", f"{one.moisture}%"),
                ("dry net", str(one.dry_weight())),
                ("state", "voided" if held.is_voided(number) else "live"),
            ]
        )
    )


@ticket.command("yard")
@click.option("--as-of", "as_of", default=None, help="Yard date, YYYY-MM-DD.")
@click.pass_obj
def yard(session: Session, as_of: str | None) -> None:
    """What is still in the yard, worst first."""
    book = session.require_book()
    when = read_date(as_of, date.today())
    tickets = TicketRepository(book.connection)
    held = tickets.book(session.season)
    ginned = LotRepository(book.connection).assigned_tickets(session.season)
    standing = ModuleYard()
    for one in held.live():
        standing.receive(one)
        if one.number in ginned:
            standing.gin(one.number)
    rows = [
        [
            str(line.ticket.number),
            str(line.ticket.module),
            line.ticket.producer,
            str(line.ticket.net.pounds),
            f"{line.ticket.moisture}",
            str(line.days),
            line.reason,
        ]
        for line in standing.running_order(when)
    ]
    click.echo(
        render_table(
            ["ticket", "module", "producer", "net", "moisture", "days", "why"],
            rows,
            right=(0, 3, 4, 5),
        )
    )
    urgent = standing.urgent(when)
    if urgent:
        click.echo()
        click.echo(f"{len(urgent)} modules are past their hold")
