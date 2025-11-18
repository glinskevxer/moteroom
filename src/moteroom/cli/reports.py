"""Report commands.

Every report takes the same two options, so they are declared once and applied
to each command rather than typed out six times. A report can always be asked
for as csv, because the office puts half of them in a spreadsheet anyway.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import click

from moteroom.cli.context import Session
from moteroom.cli.options import as_of_option, csv_option, read_date
from moteroom.cli.output import render_report
from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.core.weight import total
from moteroom.ginning.reconcile import reconcile
from moteroom.receiving.yard import ModuleYard
from moteroom.reporting import daily, exceptions, position, quality
from moteroom.reporting.report import Report
from moteroom.reporting.settlement import settlement_summary, statement_report, unsettled
from moteroom.service import inventory
from moteroom.service.settlement import SettlementService
from moteroom.storage.rates import default_terms
from moteroom.warehouse.storage import Tariff

QUALITY_KINDS: dict[str, Callable[[Any], Report]] = {
    "colour": quality.colour_distribution,
    "class": quality.class_distribution,
    "leaf": quality.leaf_distribution,
    "staple": quality.staple_distribution,
    "findings": quality.findings_report,
    "averages": quality.averages,
}

DEFAULT_TARIFF = Tariff(
    handling=Money.parse("2.85"),
    daily=Money.parse("0.14"),
    free_days=30,
    minimum_days=60,
)


def as_csv(function: Callable[..., None]) -> Callable[..., None]:
    """Give a report command its --csv flag."""
    return click.option("--csv", "csv_out", is_flag=True, help="Comma separated instead.")(
        function
    )


def emit(report: Report, csv_out: bool) -> None:
    """Print a report either as a table or as csv."""
    click.echo(report.to_csv() if csv_out else render_report(report))


@click.group()
def report() -> None:
    """Reports off the book."""


@report.command("daily")
@click.option("--on", "day", default=None, help="Gin date, YYYY-MM-DD.")
@as_csv
@click.pass_obj
def daily_report(session: Session, day: str | None, csv_out: bool) -> None:
    """What ran on one day."""
    repos = session.open_repos()
    when = read_date(day, session.season.start)
    runs = repos.lots.for_season(session.season)
    bales = repos.bales.for_season(session.season)
    emit(daily.daily_sheet(when, runs, bales), csv_out)


@report.command("quality")
@click.option(
    "--kind",
    type=click.Choice(sorted(QUALITY_KINDS)),
    default="colour",
    show_default=True,
    help="Which cut of the cards.",
)
@as_csv
@click.pass_obj
def quality_report(session: Session, kind: str, csv_out: bool) -> None:
    """How the season classed."""
    cards = session.open_repos().cards.for_season(session.season)
    emit(QUALITY_KINDS[kind](cards), csv_out)


@report.command("position")
@click.option(
    "--by",
    "grouping",
    type=click.Choice(["house", "holder"]),
    default="house",
    show_default=True,
)
@click.option("--as-of", "as_of", default=None, help="Position date, YYYY-MM-DD.")
@as_csv
@click.pass_obj
def position_report(session: Session, grouping: str, as_of: str | None, csv_out: bool) -> None:
    """Where the bales are."""
    when = read_date(as_of, date.today())
    held = session.open_repos().receipts.outstanding()
    made = (
        position.by_house(held, when) if grouping == "house" else position.by_holder(held, when)
    )
    emit(made, csv_out)


@report.command("storage")
@click.option("--as-of", "as_of", default=None, help="Storage date, YYYY-MM-DD.")
@as_csv
@click.pass_obj
def storage_report(session: Session, as_of: str | None, csv_out: bool) -> None:
    """What the warehouse will bill."""
    when = read_date(as_of, date.today())
    held = session.open_repos().receipts.outstanding()
    emit(position.storage_owed(held, DEFAULT_TARIFF, when), csv_out)


@report.command("settlements")
@as_csv
@click.pass_obj
def settlement_report(session: Session, csv_out: bool) -> None:
    """Every settlement written this season."""
    written = session.open_repos().statements.for_season(session.season)
    emit(settlement_summary(written), csv_out)


@report.command("outstanding")
@as_csv
@click.pass_obj
def outstanding_report(session: Session, csv_out: bool) -> None:
    """Producers with cotton in and no settlement written."""
    book = session.require_book()
    repos = session.open_repos()
    terms = (
        repos.rates.get(session.season)
        if repos.rates.posted(session.season)
        else default_terms()
    )
    service = SettlementService(book, terms)
    written = repos.statements.for_season(session.season)
    emit(unsettled(service.settled_producers(session.season), written), csv_out)


@report.command("statement")
@click.argument("producer")
@as_csv
@click.pass_obj
def one_statement(session: Session, producer: str, csv_out: bool) -> None:
    """One producer's page, off the settlement already written."""
    code = producer.strip().upper()
    written = session.open_repos().statements.for_season(session.season)
    for statement in written:
        if statement.producer == code:
            emit(statement_report(statement), csv_out)
            return
    raise ValidationError("producer", f"{code} has not been settled yet")


@report.command("exceptions")
@as_of_option("Exception date")
@csv_option
@click.pass_obj
def exception_report(session: Session, as_of: str | None, csv_out: bool) -> None:
    """Everything that needs somebody to do something about it."""
    when = read_date(as_of, date.today())
    repos = session.open_repos()
    lots, bales, cards = repos.lots, repos.bales, repos.cards
    receipts, contracts, statements = repos.receipts, repos.contracts, repos.statements

    held = repos.tickets.book(session.season)
    ginned = lots.assigned_tickets(session.season)
    yard = ModuleYard()
    for one in held.live():
        yard.receive(one)
        if one.number in ginned:
            yard.gin(one.number)

    waiting = [
        (bale_id, (when - bales.get(bale_id).pressed_on).days)
        for bale_id in cards.unclassed(session.season)
    ]
    checks = []
    for run in lots.for_season(session.season):
        pressed = bales.for_lot(run.lot)
        if pressed:
            checks.append(reconcile(run, total([one.net for one in pressed]), len(pressed)))
    settled = {one.producer for one in statements.for_season(session.season)}
    findings = [
        *exceptions.from_yard(yard.running_order(when)),
        *exceptions.from_unclassed(waiting),
        *exceptions.from_reconciliations(checks),
        *exceptions.from_storage(receipts.outstanding(), when),
        *exceptions.from_contracts(
            [
                (made, contracts.fill(made.number))
                for made in contracts.for_season(session.season)
            ],
            when,
        ),
        *exceptions.from_cards(cards.for_season(session.season)),
        *exceptions.from_unsettled(
            [code for code in held.producers() if code not in settled],
            {code: held.net_for_producer(code) for code in held.producers()},
        ),
    ]
    emit(exceptions.build(findings, when), csv_out)


@report.command("inventory")
@csv_option
@click.pass_obj
def inventory_report(session: Session, csv_out: bool) -> None:
    """Where every bale pressed this season actually is."""
    book = session.require_book()
    taken = inventory.take(book, session.season)
    rows = tuple(
        (str(one.bale_id), one.where, one.detail, str(one.net.pounds))
        for one in taken.placements
    )
    notes = [str(taken), f"{taken.net} pressed"]
    notes.extend(f"{key}: {reason}" for key, reason in taken.orphans)
    emit(
        Report(
            title=f"inventory for {session.season}",
            headers=("bale", "where", "detail", "net"),
            rows=rows,
            right=(3,),
            notes=tuple(notes),
        ),
        csv_out,
    )
