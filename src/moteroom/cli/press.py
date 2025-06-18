"""Press commands.

The bale number comes off the press counter, which is rebuilt from the book
every time rather than kept anywhere, so two people at two terminals cannot
issue the same number.
"""

from __future__ import annotations

import click

from moteroom.cli.context import Session
from moteroom.cli.output import render_pairs, render_table
from moteroom.cli.receiving import read_date
from moteroom.core.errors import ConflictError
from moteroom.core.ids import LotId
from moteroom.core.weight import Weight, total
from moteroom.receiving.ticket import clean_moisture
from moteroom.storage.lots import BaleRepository, LotRepository
from moteroom.storage.settings import SettingsRepository


@click.group()
def bale() -> None:
    """Pressing and tagging bales."""


@bale.command("press")
@click.argument("lot", type=int)
@click.argument("gross")
@click.option("--tare", default="23", show_default=True, help="Bagging and ties.")
@click.option("--moisture", default="6.5", show_default=True, help="Bale moisture.")
@click.option("--on", "pressed_on", default=None, help="Press date, YYYY-MM-DD.")
@click.pass_obj
def press_bale(
    session: Session,
    lot: int,
    gross: str,
    tare: str,
    moisture: str,
    pressed_on: str | None,
) -> None:
    """Press one bale off a lot."""
    book = session.require_book()
    target = LotId(session.season, lot)
    with book.transaction() as conn:
        gin = SettingsRepository(conn).gin_code()
        lots = LotRepository(conn)
        lots.get(target)
        if lots.is_closed(target):
            raise ConflictError("lot", str(target), "is closed")
        bales = BaleRepository(conn)
        counter = bales.press(session.season, gin)
        pressed = counter.press(
            target,
            read_date(pressed_on, session.season.start),
            Weight.parse(gross),
            Weight.parse(tare),
            clean_moisture(moisture),
        )
        bales.add(pressed)
    click.echo(f"bale {pressed.bale_id.grouped()} {pressed.net}")


@bale.command("list")
@click.option("--lot", type=int, default=None, help="Only bales off this lot.")
@click.pass_obj
def list_bales(session: Session, lot: int | None) -> None:
    """Bales pressed this season."""
    book = session.require_book()
    bales = BaleRepository(book.connection)
    held = (
        bales.for_lot(LotId(session.season, lot))
        if lot is not None
        else bales.for_season(session.season)
    )
    rows = [
        [
            str(one.bale_id),
            str(one.lot),
            one.pressed_on.isoformat(),
            str(one.net.pounds),
            "light" if one.is_light else "heavy" if one.is_heavy else "",
        ]
        for one in held
    ]
    click.echo(render_table(["bale", "lot", "pressed", "net", "flag"], rows, right=(3,)))
    if held:
        click.echo()
        click.echo(f"{len(held)} bales, {total([one.net for one in held])}")


@bale.command("show")
@click.argument("bale_id")
@click.pass_obj
def show_bale(session: Session, bale_id: str) -> None:
    """One bale off its tag."""
    from moteroom.core.ids import BaleId

    book = session.require_book()
    one = BaleRepository(book.connection).get(BaleId.parse(bale_id))
    click.echo(
        render_pairs(
            [
                ("bale", one.bale_id.grouped()),
                ("lot", str(one.lot)),
                ("pressed", one.pressed_on.isoformat()),
                ("gross", str(one.gross)),
                ("tare", str(one.tare)),
                ("net", str(one.net)),
                ("moisture", f"{one.moisture}%"),
                ("flag", "light" if one.is_light else "heavy" if one.is_heavy else "none"),
            ]
        )
    )
