"""Warehouse commands."""

from __future__ import annotations

import click

from moteroom.cli.context import Session
from moteroom.cli.output import render_pairs, render_table
from moteroom.cli.receiving import read_date
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId
from moteroom.core.weight import total
from moteroom.storage.lots import BaleRepository
from moteroom.storage.settings import SettingsRepository
from moteroom.storage.warehouse import OrderRepository, ReceiptRepository
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.shipping import ShippingOrder, check_against, plan_loads


@click.group()
def receipt() -> None:
    """Warehouse receipts."""


@receipt.command("issue")
@click.argument("bale_id")
@click.argument("number")
@click.option("--holder", required=True, help="Who holds the receipt.")
@click.option("--house", default=None, help="Warehouse code, or the plant's default.")
@click.option("--paper", is_flag=True, help="A paper receipt rather than electronic.")
@click.option("--on", "received_on", default=None, help="Receipt date, YYYY-MM-DD.")
@click.pass_obj
def issue(
    session: Session,
    bale_id: str,
    number: str,
    holder: str,
    house: str | None,
    paper: bool,
    received_on: str | None,
) -> None:
    """Take a bale into store."""
    book = session.require_book()
    with book.transaction() as conn:
        warehouse = house or SettingsRepository(conn).get("warehouse")
        one = BaleRepository(conn).get(BaleId.parse(bale_id))
        written = Receipt(
            number=number.strip().upper(),
            warehouse=warehouse.strip().upper(),
            bale_id=one.bale_id,
            received_on=read_date(received_on, session.season.start),
            net=one.net,
            holder=holder.strip().upper(),
            electronic=not paper,
        )
        ReceiptRepository(conn).issue(written)
    click.echo(f"receipt {written.number} for {written.bale_id} at {written.warehouse}")


@receipt.command("release")
@click.argument("number")
@click.argument("to")
@click.option("--on", "released_on", default=None, help="Release date, YYYY-MM-DD.")
@click.pass_obj
def release(session: Session, number: str, to: str, released_on: str | None) -> None:
    """Release a receipt to whoever takes the bale."""
    book = session.require_book()
    with book.transaction() as conn:
        released = ReceiptRepository(conn).release(
            number.strip().upper(),
            read_date(released_on, session.season.end),
            to.strip().upper(),
        )
    click.echo(f"receipt {released.number} released to {released.holder}")


@receipt.command("list")
@click.option("--house", default=None, help="Only this warehouse.")
@click.pass_obj
def list_receipts(session: Session, house: str | None) -> None:
    """Receipts still outstanding."""
    book = session.require_book()
    held = ReceiptRepository(book.connection).outstanding(house)
    rows = [
        [
            one.number,
            one.warehouse,
            str(one.bale_id),
            one.received_on.isoformat(),
            str(one.net.pounds),
            one.holder,
            "paper" if not one.electronic else "",
        ]
        for one in held
    ]
    click.echo(
        render_table(
            ["receipt", "house", "bale", "received", "net", "holder", "form"], rows, right=(4,)
        )
    )
    if held:
        click.echo()
        click.echo(f"{len(held)} outstanding, {total([one.net for one in held])}")


@click.group()
def order() -> None:
    """Shipping orders."""


@order.command("write")
@click.argument("number")
@click.argument("buyer")
@click.argument("receipts", nargs=-1)
@click.option("--house", default=None, help="Warehouse code, or the plant's default.")
@click.option("--on", "ordered_on", default=None, help="Order date, YYYY-MM-DD.")
@click.pass_obj
def write_order(
    session: Session,
    number: str,
    buyer: str,
    receipts: tuple[str, ...],
    house: str | None,
    ordered_on: str | None,
) -> None:
    """Write an order against receipts that are still outstanding."""
    if not receipts:
        raise ValidationError("receipts", "an order has to name a bale")
    book = session.require_book()
    with book.transaction() as conn:
        warehouse = (house or SettingsRepository(conn).get("warehouse")).strip().upper()
        written = ShippingOrder(
            number=number.strip().upper(),
            warehouse=warehouse,
            ordered_on=read_date(ordered_on, session.season.end),
            buyer=buyer.strip().upper(),
            receipts=tuple(one.strip().upper() for one in receipts),
        )
        held = ReceiptRepository(conn)
        picked = check_against(written, held.outstanding(warehouse))
        OrderRepository(conn).add(written)
    loads = plan_loads(picked)
    click.echo(f"order {written.number} {written.count} bales in {len(loads)} loads")


@order.command("show")
@click.argument("number")
@click.pass_obj
def show_order(session: Session, number: str) -> None:
    """One order and the loads it makes."""
    book = session.require_book()
    found = OrderRepository(book.connection).get(number.strip().upper())
    receipts = ReceiptRepository(book.connection)
    picked = [receipts.get(one) for one in found.receipts]
    loads = plan_loads(picked)
    click.echo(
        render_pairs(
            [
                ("order", found.number),
                ("house", found.warehouse),
                ("buyer", found.buyer),
                ("ordered", found.ordered_on.isoformat()),
                ("bales", str(found.count)),
                ("loads", str(len(loads))),
                ("weight", str(total([one.net for one in picked]))),
            ]
        )
    )
