"""Producer and farm commands."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import click

from moteroom.cli.context import Session
from moteroom.cli.output import render_pairs, render_table
from moteroom.core.errors import ValidationError
from moteroom.receiving.party import Farm, Producer
from moteroom.storage.producers import FarmRepository, ProducerRepository


@click.group()
def producer() -> None:
    """Growers and the farms they gin off."""


@producer.command("add")
@click.argument("code")
@click.argument("name")
@click.pass_obj
def add_producer(session: Session, code: str, name: str) -> None:
    """Put a grower on the book."""
    book = session.book()
    with book.transaction() as conn:
        ProducerRepository(conn).add(Producer.parse(code, name))
    click.echo(f"added {code.strip().upper()}")


@producer.command("list")
@click.pass_obj
def list_producers(session: Session) -> None:
    """Every grower on the book."""
    book = session.require_book()
    people = ProducerRepository(book.connection).all()
    farms = FarmRepository(book.connection)
    rows = [
        [grower.code, grower.name, str(len(farms.for_producer(grower.code)))]
        for grower in people
    ]
    click.echo(render_table(["code", "name", "farms"], rows, right=(2,)))


@producer.command("show")
@click.argument("code")
@click.pass_obj
def show_producer(session: Session, code: str) -> None:
    """One grower, with their farms and acres."""
    book = session.require_book()
    grower = ProducerRepository(book.connection).get(code.strip().upper())
    farms = FarmRepository(book.connection)
    held = farms.for_producer(grower.code)
    click.echo(
        render_pairs(
            [
                ("code", grower.code),
                ("name", grower.name),
                ("farms", str(len(held))),
                ("acres", str(farms.acres_for(grower.code))),
            ]
        )
    )
    if held:
        click.echo()
        rows = [[farm.number, farm.tract, str(farm.acres)] for farm in held]
        click.echo(render_table(["farm", "tract", "acres"], rows, right=(2,)))


@producer.command("farm")
@click.argument("code")
@click.argument("number")
@click.argument("tract")
@click.argument("acres")
@click.pass_obj
def add_farm(session: Session, code: str, number: str, tract: str, acres: str) -> None:
    """Add a farm and tract to a grower."""
    try:
        measured = Decimal(acres)
    except InvalidOperation as exc:
        raise ValidationError("acres", f"{acres!r} is not an acreage") from exc
    book = session.book()
    with book.transaction() as conn:
        FarmRepository(conn).add(
            Farm(number.strip(), tract.strip(), code.strip().upper(), measured)
        )
    click.echo(f"added farm {number}-{tract} to {code.strip().upper()}")
