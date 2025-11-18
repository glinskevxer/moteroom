"""Loan commands: what a bale is worth and what it costs to get it back."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import click

from moteroom.cli.context import Session
from moteroom.cli.output import render_pairs, render_table
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId
from moteroom.core.money import CentsPerPound
from moteroom.loan import pool
from moteroom.loan.redemption import Redemption
from moteroom.loan.value import rate_for
from moteroom.storage.rates import default_terms


def base_rate(session: Session) -> CentsPerPound:
    """The base loan rate, off the season's posted rates or the plant setting."""
    repos = session.open_repos()
    if repos.rates.posted(session.season):
        return repos.rates.get(session.season).base_rate
    posted = repos.settings.get_or("base_loan_rate", "")
    return CentsPerPound.parse(posted) if posted else default_terms().base_rate


def read_rate(text: str, field: str) -> Decimal:
    """Read a percentage off the command line."""
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(field, f"{text!r} is not a rate") from exc


@click.group()
def loan() -> None:
    """Bales under loan."""


@loan.command("value")
@click.argument("bale_id")
@click.pass_obj
def value(session: Session, bale_id: str) -> None:
    """What one classed bale loans for, line by line."""
    repos = session.open_repos()
    tag = BaleId.parse(bale_id)
    one = repos.bales.get(tag)
    card = repos.cards.get(tag)
    breakdown = rate_for(card, base_rate(session))
    rows = [(name, f"{amount}") for name, amount in breakdown.lines()]
    click.echo(render_table(["line", "cents"], rows, right=(1,)))
    click.echo()
    click.echo(f"{one.net} at {breakdown.rate} is {breakdown.rate.on(one.net)}")


@loan.command("pool")
@click.pass_obj
def pool_report(session: Session) -> None:
    """The whole season priced at loan."""
    repos = session.open_repos()
    bales, cards = repos.bales, repos.cards
    pairs = [
        (one, cards.get(one.bale_id))
        for one in bales.for_season(session.season)
        if cards.has(one.bale_id)
    ]
    priced = pool.build(pairs, base_rate(session))
    click.echo(
        render_pairs(
            [
                ("bales", str(priced.bales)),
                ("lint", str(priced.lint)),
                ("value", str(priced.value)),
                ("average rate", str(priced.average_rate)),
                ("average bale", str(priced.average_bale)),
                ("not eligible", str(len(priced.ineligible))),
            ]
        )
    )
    for bale_id, reason in priced.ineligible:
        click.echo(f"  {bale_id}: {reason}")


@loan.command("redeem")
@click.argument("bale_id")
@click.option("--price", required=True, help="World price in cents per pound.")
@click.option("--days", type=int, default=0, show_default=True, help="Days under loan.")
@click.option("--interest", default="6.25", show_default=True, help="Annual interest rate.")
@click.pass_obj
def redeem(session: Session, bale_id: str, price: str, days: int, interest: str) -> None:
    """What it costs to take a bale back out of loan."""
    repos = session.open_repos()
    tag = BaleId.parse(bale_id)
    one = repos.bales.get(tag)
    card = repos.cards.get(tag)
    breakdown = rate_for(card, base_rate(session))
    made = Redemption(
        bale_id=str(tag),
        net=one.net,
        loan_rate=breakdown.rate,
        world_price=CentsPerPound.parse(price),
        days=days,
        annual_rate=read_rate(interest, "interest"),
    )
    click.echo(render_pairs([(name, str(amount)) for name, amount in made.lines()]))
    click.echo()
    click.echo(str(made))
