"""Producer and farm commands."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import click

from moteroom.cli.context import Session
from moteroom.cli.output import render_pairs, render_table
from moteroom.core.errors import ValidationError
from moteroom.receiving.party import Farm, Producer
from moteroom.service.producer import standing


@click.group()
def producer() -> None:
    """Growers and the farms they gin off."""


@producer.command("add")
@click.argument("code")
@click.argument("name")
@click.pass_obj
def add_producer(session: Session, code: str, name: str) -> None:
    """Put a grower on the book."""
    with session.writing(True) as repos:
        repos.producers.add(Producer.parse(code, name))
    click.echo(f"added {code.strip().upper()}")


@producer.command("list")
@click.pass_obj
def list_producers(session: Session) -> None:
    """Every grower on the book."""
    people = session.open_repos().producers.all()
    farms = session.open_repos().farms
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
    grower = session.open_repos().producers.get(code.strip().upper())
    farms = session.open_repos().farms
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
    with session.writing(True) as repos:
        repos.farms.add(Farm(number.strip(), tract.strip(), code.strip().upper(), measured))
    click.echo(f"added farm {number}-{tract} to {code.strip().upper()}")


@producer.command("season")
@click.argument("code")
@click.pass_obj
def show_season(session: Session, code: str) -> None:
    """One grower's whole season, and how it sits against the plant."""
    book = session.require_book()
    grower = session.open_repos().producers.get(code.strip().upper())
    click.echo(render_pairs(standing(book, session.season, grower.code).lines()))
