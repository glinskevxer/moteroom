"""Scale house commands."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import click

from moteroom.cli.context import Session
from moteroom.cli.options import as_of_option, on_option, read_date
from moteroom.cli.output import render_pairs, render_table
from moteroom.core.csvio import field, read_rows, write_rows
from moteroom.core.errors import MoteroomError, ValidationError
from moteroom.core.ids import ModuleId
from moteroom.core.weight import Weight
from moteroom.receiving.scale import Certificate, ScaleBook
from moteroom.receiving.ticket import ModuleTicket, clean_moisture
from moteroom.receiving.yard import ModuleYard
from moteroom.storage.lots import LotRepository
from moteroom.storage.tickets import TicketRepository


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
@on_option("Weigh date")
@click.pass_obj
def weigh(
    session: Session,
    module: str,
    producer: str,
    farm: str,
    gross: str,
    tare: str,
    moisture: str,
    on_text: str | None,
) -> None:
    """Write a scale ticket for one module."""
    book = session.book()
    day = read_date(on_text, session.season.start)
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
        session.record("weigh", str(written.module), f"ticket {number} {written.net}")
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
        session.record(
            "correct", str(wrong.module), f"ticket {replacement.number} voids {number}"
        )
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
@as_of_option("Yard date")
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


@ticket.command("scale")
@click.argument("scale")
@click.argument("expires")
@click.option("--tester", default="STATE WEIGHTS", show_default=True, help="Who tested it.")
@click.option("--error", default="0.0", show_default=True, help="Measured error in percent.")
@as_of_option("Test date")
@click.pass_obj
def certify(
    session: Session, scale: str, expires: str, tester: str, error: str, as_of: str | None
) -> None:
    """Check a scale certificate and what it does to a weight."""
    tested = read_date(as_of, session.season.start)
    held = Certificate(
        scale=scale.strip().upper(),
        tested_on=tested,
        expires_on=read_date(expires, session.season.end),
        tester=tester.strip().upper(),
        error=Decimal(error),
    )
    book = ScaleBook()
    book.certify(held)
    click.echo(
        render_pairs(
            [
                ("scale", held.scale),
                ("tested", held.tested_on.isoformat()),
                ("expires", held.expires_on.isoformat()),
                ("tester", held.tester),
                ("error", f"{held.error}%"),
                ("days left", str(held.days_left(tested))),
                ("expiring", "yes" if held.expiring(tested) else "no"),
                ("21,200 lb reads", str(book.correction(held.scale, tested, Weight(21_200)))),
            ]
        )
    )


TICKET_COLUMNS = ("module", "producer", "farm", "gross", "tare", "moisture", "weighed")


@ticket.command("import")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_obj
def import_tickets(session: Session, path: Path) -> None:
    """Load scale tickets out of the weighbridge export."""
    book = session.book()
    rows = read_rows(path.read_text(encoding="utf-8"), list(TICKET_COLUMNS))
    written = 0
    skipped: list[str] = []
    with book.transaction() as conn:
        tickets = TicketRepository(conn)
        held = tickets.book(session.season)
        for row in rows:
            module = field(row, "module")
            try:
                one = ModuleTicket(
                    number=tickets.next_number(session.season),
                    module=ModuleId.parse(module),
                    producer=field(row, "producer").upper(),
                    farm=field(row, "farm"),
                    weighed_on=read_date(field(row, "weighed"), session.season.start),
                    gross=Weight.parse(field(row, "gross")),
                    tare=Weight.parse(field(row, "tare")),
                    moisture=clean_moisture(field(row, "moisture")),
                )
                held.add(one)
                tickets.add(one)
            except MoteroomError as exc:
                skipped.append(f"{module}: {exc}")
                continue
            written += 1
        session.record("import", str(path.name), f"{written} of {len(rows)} tickets")
    click.echo(f"loaded {written} of {len(rows)} tickets")
    for line in skipped:
        click.echo(f"  skipped {line}")


@ticket.command("export")
@click.option("--out", "out_path", default=None, help="Write the file here instead of stdout.")
@click.pass_obj
def export_tickets(session: Session, out_path: str | None) -> None:
    """Write this season's live tickets back out as a csv."""
    held = session.open_repos().tickets.book(session.season)
    rows = [
        [
            str(one.module),
            one.producer,
            one.farm,
            str(one.gross.pounds),
            str(one.tare.pounds),
            str(one.moisture),
            one.weighed_on.isoformat(),
        ]
        for one in held.live()
    ]
    text = write_rows(list(TICKET_COLUMNS), rows)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
        click.echo(f"{len(rows)} tickets written to {out_path}")
        return
    click.echo(text, nl=False)
