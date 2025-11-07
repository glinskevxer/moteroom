"""Settlement commands.

A settlement is previewed far more often than it is run. Preview reads the
book and works the numbers out; run does the same thing and writes the answer
down, which is what makes it a settlement rather than an opinion. Once it is
written it does not move.
"""

from __future__ import annotations

from datetime import date

import click

from moteroom.cli.context import Session
from moteroom.cli.options import on_option, read_date
from moteroom.cli.output import render_pairs, render_table
from moteroom.core.money import Money
from moteroom.service.settlement import SettlementService
from moteroom.settlement.equity import allocate_margin
from moteroom.settlement.statement import Advance, Statement
from moteroom.storage.rates import RatesRepository, default_terms
from moteroom.storage.settlement import AdvanceRepository, StatementRepository
from moteroom.storage.tickets import TicketRepository


def statement_lines(made: Statement) -> list[tuple[str, str]]:
    """A statement as name and value pairs, in the order it prints."""
    rows = [
        ("producer", made.producer),
        ("season", str(made.season)),
        ("bales", str(made.bales)),
        ("lint", str(made.lint)),
    ]
    rows.extend((name, str(amount)) for name, amount in made.lines())
    return rows


@click.group()
def settle() -> None:
    """Paying producers what the season came to."""


@settle.command("rates")
@click.option("--show", is_flag=True, help="Print the posted rates and stop.")
@click.pass_obj
def post_rates(session: Session, show: bool) -> None:
    """Post this season's rates, or read the posted ones back."""
    book = session.book()
    rates = RatesRepository(book.connection)
    if show:
        click.echo(render_pairs(rates.lines(session.season)))
        return
    with book.transaction() as conn:
        RatesRepository(conn).post(session.season, default_terms(), date.today())
    click.echo(f"rates posted for {session.season}")


@settle.command("advance")
@click.argument("producer")
@click.argument("reference")
@click.argument("amount")
@on_option("Payment date")
@click.pass_obj
def advance(
    session: Session, producer: str, reference: str, amount: str, on_text: str | None
) -> None:
    """Record money paid out before the settlement."""
    book = session.require_book()
    with book.transaction() as conn:
        AdvanceRepository(conn).add(
            session.season,
            producer.strip().upper(),
            Advance(reference.strip().upper(), Money.parse(amount)),
            read_date(on_text, session.season.start),
        )
    click.echo(f"advance {reference.strip().upper()} of {Money.parse(amount)} recorded")


@settle.command("preview")
@click.argument("producer")
@click.pass_obj
def preview(session: Session, producer: str) -> None:
    """Work a producer's settlement out without writing it down."""
    book = session.require_book()
    rates = RatesRepository(book.connection)
    terms = rates.get(session.season) if rates.posted(session.season) else default_terms()
    service = SettlementService(book, terms)
    code = producer.strip().upper()
    made = service.build(session.season, code)
    click.echo(render_pairs(statement_lines(made)))
    shares = service.shares_for(session.season, code)
    rows = [
        [
            share.lot,
            str(share.modules),
            str(share.seed_cotton.pounds),
            str(share.lint.pounds),
            str(share.bales),
            str(share.rate),
            "classed" if share.classed else "base rate",
        ]
        for share in shares
    ]
    click.echo()
    click.echo(
        render_table(
            ["lot", "modules", "seed cotton", "lint", "bales", "rate", "basis"],
            rows,
            right=(1, 2, 3, 4),
        )
    )


@settle.command("run")
@click.argument("producer")
@on_option("Settlement date")
@click.pass_obj
def run_settlement(session: Session, producer: str, on_text: str | None) -> None:
    """Settle a producer and write it down."""
    book = session.require_book()
    rates = RatesRepository(book.connection)
    terms = rates.get(session.season) if rates.posted(session.season) else default_terms()
    code = producer.strip().upper()
    with book.transaction() as conn:
        made = SettlementService(book, terms).build(session.season, code)
        StatementRepository(conn).save(made, read_date(on_text, session.season.end))
    verdict = "due" if made.is_payable else "owing"
    click.echo(f"{code} settled, {made.net} {verdict}")


@settle.command("list")
@click.pass_obj
def list_settlements(session: Session) -> None:
    """Every settlement written this season."""
    book = session.require_book()
    rows = [
        [
            made.producer,
            str(made.bales),
            str(made.lint.pounds),
            str(made.lint_proceeds),
            str(made.gin_charges),
            str(made.seed_credit),
            str(made.net),
        ]
        for made in StatementRepository(book.connection).for_season(session.season)
    ]
    click.echo(
        render_table(
            ["producer", "bales", "lint", "proceeds", "charges", "seed", "net"],
            rows,
            right=(1, 2, 3, 4, 5, 6),
        )
    )


@settle.command("equity")
@click.argument("margin")
@click.option("--cash", type=int, default=1, show_default=True, help="Shares paid in cash.")
@click.option("--retain", type=int, default=4, show_default=True, help="Shares kept as equity.")
@click.pass_obj
def equity(session: Session, margin: str, cash: int, retain: int) -> None:
    """Allocate the season's margin back to the members on ginned volume."""
    book = session.require_book()
    held = TicketRepository(book.connection).book(session.season)
    volume = {code: held.net_for_producer(code) for code in held.producers()}
    made = allocate_margin(session.season, Money.parse(margin), volume, cash, retain)
    rows = [
        [
            share.producer,
            str(share.basis.pounds),
            str(share.allocated),
            str(share.cash),
            str(share.retained),
        ]
        for share in made.shares
    ]
    click.echo(
        render_table(
            ["member", "ginned", "allocated", "cash", "equity"], rows, right=(1, 2, 3, 4)
        )
    )
    click.echo()
    click.echo(f"{made.members} members, {made.cash} in cash and {made.retained} retained")
