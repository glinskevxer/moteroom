"""Contract commands: what a contract is worth and how much of it is left."""

from __future__ import annotations

import click

from moteroom.cli.context import Session
from moteroom.cli.output import render_pairs, render_table
from moteroom.cli.receiving import read_date
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId
from moteroom.core.money import CentsPerPound
from moteroom.settlement.contract import Contract, delivered_price, fill_of
from moteroom.storage.cards import CardRepository
from moteroom.storage.contracts import ContractRepository
from moteroom.storage.lots import BaleRepository


def build_contract(
    number: str,
    buyer: str,
    bales: int,
    signed_on: str | None,
    opens: str | None,
    closes: str | None,
    price: str | None,
    basis: str | None,
    session: Session,
) -> Contract:
    """Make a contract out of what the command line was given."""
    if (price is None) == (basis is None):
        raise ValidationError("price", "give a price or a basis, not both")
    return Contract(
        number=number.strip().upper(),
        buyer=buyer.strip().upper(),
        signed_on=read_date(signed_on, session.season.start),
        bales=bales,
        delivery_from=read_date(opens, session.season.start),
        delivery_to=read_date(closes, session.season.end),
        price=CentsPerPound.parse(price) if price else None,
        basis=CentsPerPound.parse(basis) if basis else None,
    )


@click.group()
def contract() -> None:
    """Forward contracts against the season's bales."""


@contract.command("price")
@click.argument("bale_id")
@click.option("--price", default=None, help="Flat contract price in cents.")
@click.option("--basis", default=None, help="Basis in cents, for a basis contract.")
@click.option("--futures", default=None, help="Futures price, for a basis contract.")
@click.pass_obj
def price_delivery(
    session: Session,
    bale_id: str,
    price: str | None,
    basis: str | None,
    futures: str | None,
) -> None:
    """What one classed bale is paid against a contract."""
    book = session.require_book()
    tag = BaleId.parse(bale_id)
    one = BaleRepository(book.connection).get(tag)
    card = CardRepository(book.connection).get(tag)
    made = build_contract("C000001", "BUYER", 1, None, None, None, price, basis, session)
    against = CentsPerPound.parse(futures) if futures else None
    rate = delivered_price(made, card, against)
    click.echo(
        render_pairs(
            [
                ("bale", tag.grouped()),
                ("net", str(one.net)),
                ("contract", str(made.price_against(against))),
                ("grade", f"{card.color}-{card.leaf} staple {card.staple}"),
                ("delivered", str(rate)),
                ("value", str(rate.on(one.net))),
            ]
        )
    )


@contract.command("fill")
@click.argument("number")
@click.argument("bales", type=int)
@click.argument("delivered", nargs=-1, type=int)
@click.pass_obj
def fill(session: Session, number: str, bales: int, delivered: tuple[int, ...]) -> None:
    """How much of a contract is still to go."""
    made = build_contract(number, "BUYER", bales, None, None, None, "68.50", None, session)
    click.echo(str(fill_of(made, list(delivered))))


@contract.command("write")
@click.argument("number")
@click.argument("buyer")
@click.argument("bales", type=int)
@click.option("--price", default=None, help="Flat contract price in cents.")
@click.option("--basis", default=None, help="Basis in cents, for a basis contract.")
@click.option("--signed", default=None, help="Signing date, YYYY-MM-DD.")
@click.option("--opens", default=None, help="Delivery window opens, YYYY-MM-DD.")
@click.option("--closes", default=None, help="Delivery window closes, YYYY-MM-DD.")
@click.pass_obj
def write_contract(
    session: Session,
    number: str,
    buyer: str,
    bales: int,
    price: str | None,
    basis: str | None,
    signed: str | None,
    opens: str | None,
    closes: str | None,
) -> None:
    """Put a contract on the book."""
    book = session.book()
    made = build_contract(number, buyer, bales, signed, opens, closes, price, basis, session)
    with book.transaction() as conn:
        ContractRepository(conn).add(made, session.season)
    click.echo(str(made))


@contract.command("deliver")
@click.argument("number")
@click.argument("bale_id")
@click.option("--futures", default=None, help="Futures price, for a basis contract.")
@click.option("--on", "delivered_on", default=None, help="Delivery date, YYYY-MM-DD.")
@click.pass_obj
def deliver(
    session: Session, number: str, bale_id: str, futures: str | None, delivered_on: str | None
) -> None:
    """Deliver one classed bale against a contract."""
    book = session.require_book()
    tag = BaleId.parse(bale_id)
    when = read_date(delivered_on, session.season.end)
    with book.transaction() as conn:
        contracts = ContractRepository(conn)
        made = contracts.get(number.strip().upper())
        if not made.covers(when):
            raise ValidationError("on", f"{when} is outside the delivery window")
        card = CardRepository(conn).get(tag)
        against = CentsPerPound.parse(futures) if futures else None
        rate = delivered_price(made, card, against)
        contracts.deliver(made.number, tag, when, rate)
        one = BaleRepository(conn).get(tag)
    click.echo(f"{tag} delivered at {rate}, {rate.on(one.net)}")


@contract.command("list")
@click.pass_obj
def list_contracts(session: Session) -> None:
    """Every contract this season and how much of it is left."""
    book = session.require_book()
    contracts = ContractRepository(book.connection)
    rows = []
    for made in contracts.for_season(session.season):
        filled = contracts.fill(made.number)
        rows.append(
            [
                made.number,
                made.buyer,
                str(made.bales),
                str(filled.delivered),
                str(filled.remaining),
                str(made.price) if made.price else f"basis {made.basis}",
                made.delivery_to.isoformat(),
            ]
        )
    click.echo(
        render_table(
            ["contract", "buyer", "bales", "delivered", "left", "price", "closes"],
            rows,
            right=(2, 3, 4),
        )
    )
