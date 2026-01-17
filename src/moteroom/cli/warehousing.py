"""Warehouse commands: receipts in and out, and the orders that move them."""

from __future__ import annotations

from pathlib import Path

import click

from moteroom.cli.context import Session
from moteroom.cli.options import on_option, read_date
from moteroom.cli.output import render_pairs, render_table
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId
from moteroom.core.weight import total
from moteroom.warehouse.ewr import parse_acknowledgement, render_transfer, transfer_weight
from moteroom.warehouse.movement import arrive, send
from moteroom.warehouse.receipt import Receipt
from moteroom.warehouse.shipping import ShippingOrder, check_against, plan_loads


@click.group()
def receipt() -> None:
    """Warehouse receipts, in and out of store."""


@receipt.command("issue")
@click.argument("bale_id")
@click.argument("number")
@click.option("--holder", required=True, help="Who holds the receipt.")
@click.option("--house", default=None, help="Warehouse code, or the plant's default.")
@click.option("--paper", is_flag=True, help="A paper receipt rather than electronic.")
@on_option("Receipt date")
@click.pass_obj
def issue(
    session: Session,
    bale_id: str,
    number: str,
    holder: str,
    house: str | None,
    paper: bool,
    on_text: str | None,
) -> None:
    """Take a bale into store."""
    with session.writing() as repos:
        warehouse = house or repos.settings.get("warehouse")
        one = repos.bales.get(BaleId.parse(bale_id))
        written = Receipt(
            number=number.strip().upper(),
            warehouse=warehouse.strip().upper(),
            bale_id=one.bale_id,
            received_on=read_date(on_text, session.season.start),
            net=one.net,
            holder=holder.strip().upper(),
            electronic=not paper,
        )
        repos.receipts.issue(written)
    click.echo(f"receipt {written.number} for {written.bale_id} at {written.warehouse}")


@receipt.command("release")
@click.argument("number")
@click.argument("to")
@on_option("Release date")
@click.pass_obj
def release(session: Session, number: str, to: str, on_text: str | None) -> None:
    """Release a receipt to whoever takes the bale."""
    with session.writing() as repos:
        released = repos.receipts.release(
            number.strip().upper(),
            read_date(on_text, session.season.end),
            to.strip().upper(),
        )
    click.echo(f"receipt {released.number} released to {released.holder}")


@receipt.command("list")
@click.option("--house", default=None, help="Only this warehouse.")
@click.pass_obj
def list_receipts(session: Session, house: str | None) -> None:
    """Receipts still outstanding."""
    held = session.open_repos().receipts.outstanding(house)
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
    """Shipping orders against receipts in store."""


@order.command("write")
@click.argument("number")
@click.argument("buyer")
@click.argument("receipts", nargs=-1)
@click.option("--house", default=None, help="Warehouse code, or the plant's default.")
@on_option("Order date")
@click.pass_obj
def write_order(
    session: Session,
    number: str,
    buyer: str,
    receipts: tuple[str, ...],
    house: str | None,
    on_text: str | None,
) -> None:
    """Write an order against receipts that are still outstanding."""
    if not receipts:
        raise ValidationError("receipts", "an order has to name a bale")
    with session.writing() as repos:
        warehouse = (house or repos.settings.get("warehouse")).strip().upper()
        written = ShippingOrder(
            number=number.strip().upper(),
            warehouse=warehouse,
            ordered_on=read_date(on_text, session.season.end),
            buyer=buyer.strip().upper(),
            receipts=tuple(one.strip().upper() for one in receipts),
        )
        held = repos.receipts
        picked = check_against(written, held.outstanding(warehouse))
        repos.orders.add(written)
    loads = plan_loads(picked)
    click.echo(f"order {written.number} {written.count} bales in {len(loads)} loads")


@order.command("show")
@click.argument("number")
@click.pass_obj
def show_order(session: Session, number: str) -> None:
    """One order and the loads it makes."""
    found = session.open_repos().orders.get(number.strip().upper())
    receipts = session.open_repos().receipts
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


@receipt.command("transfer")
@click.argument("to")
@click.argument("numbers", nargs=-1)
@click.option("--provider", default="EWRCO", show_default=True, help="EWR provider code.")
@click.option("--out", "out_path", default=None, help="Write the file here instead of stdout.")
@on_option("Transfer date")
@click.pass_obj
def transfer(
    session: Session,
    to: str,
    numbers: tuple[str, ...],
    provider: str,
    out_path: str | None,
    on_text: str | None,
) -> None:
    """Write an electronic transfer for receipts still in store."""
    receipts = session.open_repos().receipts
    picked = (
        [receipts.get(number.strip().upper()) for number in numbers]
        if numbers
        else receipts.outstanding()
    )
    text = render_transfer(picked, provider, read_date(on_text, session.season.end), to)
    if out_path:
        Path(out_path).write_text(text + "\n", encoding="utf-8")
        click.echo(f"{len(picked)} receipts, {transfer_weight(picked)}, written to {out_path}")
        return
    click.echo(text)


@receipt.command("acknowledge")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--to", default=None, help="Release the accepted receipts to this holder.")
@on_option("Release date")
@click.pass_obj
def acknowledge(session: Session, path: Path, to: str | None, on_text: str | None) -> None:
    """Read the provider's answer and release what it accepted."""
    answer = parse_acknowledgement(path.read_text(encoding="utf-8"))
    click.echo(f"{answer.provider} on {answer.answered_on.isoformat()}: {answer}")
    for number, reason in answer.rejected:
        click.echo(f"  rejected {number}: {reason}")
    if to is None:
        return
    when = read_date(on_text, session.season.end)
    with session.writing() as repos:
        held = repos.receipts
        for number in answer.accepted:
            held.release(number, when, to.strip().upper())
    click.echo(f"released {len(answer.accepted)} receipts to {to.strip().upper()}")


@receipt.command("move")
@click.argument("number")
@click.argument("house")
@click.argument("new_number")
@click.option("--holder", default=None, help="Who holds it at the new house.")
@on_option("Movement date")
@click.option("--arrived", default=None, help="Arrival date, Y-m-d, if it is there.")
@click.pass_obj
def move(
    session: Session,
    number: str,
    house: str,
    new_number: str,
    holder: str | None,
    on_text: str | None,
    arrived: str | None = None,
) -> None:
    """Move a bale to another warehouse, which is two receipts and a gap."""
    left_on = read_date(on_text, session.season.end)
    with session.writing() as repos:
        receipts = repos.receipts
        held = receipts.get(number.strip().upper())
        movement = send(held, house, left_on)
        receipts.release(held.number, left_on, movement.arrived)
        if arrived:
            closed, made = arrive(
                movement,
                new_number,
                read_date(arrived, session.season.end),
                holder or held.holder,
            )
            receipts.issue(made)
            movement = closed
        session.record("move", str(movement.bale_id), f"{movement.left} to {movement.arrived}")
    click.echo(str(movement))
