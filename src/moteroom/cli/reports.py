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
from moteroom.cli.output import render_report
from moteroom.cli.receiving import read_date
from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.reporting import daily, position, quality
from moteroom.reporting.report import Report
from moteroom.reporting.settlement import settlement_summary, statement_report, unsettled
from moteroom.service.settlement import SettlementService
from moteroom.storage.cards import CardRepository
from moteroom.storage.lots import BaleRepository, LotRepository
from moteroom.storage.rates import RatesRepository, default_terms
from moteroom.storage.settlement import StatementRepository
from moteroom.storage.warehouse import ReceiptRepository
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
    book = session.require_book()
    when = read_date(day, session.season.start)
    runs = LotRepository(book.connection).for_season(session.season)
    bales = BaleRepository(book.connection).for_season(session.season)
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
    book = session.require_book()
    cards = CardRepository(book.connection).for_season(session.season)
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
    book = session.require_book()
    when = read_date(as_of, date.today())
    receipts = ReceiptRepository(book.connection)
    held = receipts.outstanding()
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
    book = session.require_book()
    when = read_date(as_of, date.today())
    held = ReceiptRepository(book.connection).outstanding()
    emit(position.storage_owed(held, DEFAULT_TARIFF, when), csv_out)


@report.command("settlements")
@as_csv
@click.pass_obj
def settlement_report(session: Session, csv_out: bool) -> None:
    """Every settlement written this season."""
    book = session.require_book()
    written = StatementRepository(book.connection).for_season(session.season)
    emit(settlement_summary(written), csv_out)


@report.command("outstanding")
@as_csv
@click.pass_obj
def outstanding_report(session: Session, csv_out: bool) -> None:
    """Producers with cotton in and no settlement written."""
    book = session.require_book()
    rates = RatesRepository(book.connection)
    terms = rates.get(session.season) if rates.posted(session.season) else default_terms()
    service = SettlementService(book, terms)
    written = StatementRepository(book.connection).for_season(session.season)
    emit(unsettled(service.settled_producers(session.season), written), csv_out)


@report.command("statement")
@click.argument("producer")
@as_csv
@click.pass_obj
def one_statement(session: Session, producer: str, csv_out: bool) -> None:
    """One producer's page, off the settlement already written."""
    book = session.require_book()
    code = producer.strip().upper()
    written = StatementRepository(book.connection).for_season(session.season)
    for statement in written:
        if statement.producer == code:
            emit(statement_report(statement), csv_out)
            return
    raise ValidationError("producer", f"{code} has not been settled yet")
