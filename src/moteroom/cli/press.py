"""Press commands.

The bale number comes off the press counter, which is rebuilt from the book
every time rather than kept anywhere, so two people at two terminals cannot
issue the same number.
"""

from __future__ import annotations

from decimal import Decimal

import click

from moteroom.cli.context import Session
from moteroom.cli.options import on_option, read_date
from moteroom.cli.output import render_pairs, render_table
from moteroom.core.errors import ConflictError
from moteroom.core.ids import LotId
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.weight import Weight, total
from moteroom.press.restoration import Restoration
from moteroom.press.tare import BAGS, TIES, Delivery, TareStore
from moteroom.receiving.ticket import clean_moisture


@click.group()
def bale() -> None:
    """Pressing and tagging bales."""


@bale.command("press")
@click.argument("lot", type=int)
@click.argument("gross")
@click.option("--tare", default="23", show_default=True, help="Bagging and ties.")
@click.option("--moisture", default="6.5", show_default=True, help="Bale moisture.")
@on_option("Press date")
@click.pass_obj
def press_bale(
    session: Session,
    lot: int,
    gross: str,
    tare: str,
    moisture: str,
    on_text: str | None,
) -> None:
    """Press one bale off a lot."""
    target = LotId(session.season, lot)
    with session.writing() as repos:
        gin = repos.settings.gin_code()
        lots = repos.lots
        lots.get(target)
        if lots.is_closed(target):
            raise ConflictError("lot", str(target), "is closed")
        bales = repos.bales
        counter = bales.press(session.season, gin)
        pressed = counter.press(
            target,
            read_date(on_text, session.season.start),
            Weight.parse(gross),
            Weight.parse(tare),
            clean_moisture(moisture),
        )
        bales.add(pressed)
        session.record("press", str(pressed.bale_id), f"lot {target}, {pressed.net}")
    click.echo(f"bale {pressed.bale_id.grouped()} {pressed.net}")


@bale.command("list")
@click.option("--lot", type=int, default=None, help="Only bales off this lot.")
@click.pass_obj
def list_bales(session: Session, lot: int | None) -> None:
    """Bales pressed this season."""
    bales = session.open_repos().bales
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

    one = session.open_repos().bales.get(BaleId.parse(bale_id))
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


@bale.command("restore")
@click.argument("dry_weight")
@click.argument("before")
@click.option(
    "--to", "target", default="7.5", show_default=True, help="Moisture to restore to."
)
@click.option("--price", default=None, help="Lint price, to value the water added.")
def restore(dry_weight: str, before: str, target: str, price: str | None) -> None:
    """Work out what restoring moisture does to a press weight."""
    made = Restoration(Weight.parse(dry_weight), Decimal(before), Decimal(target))
    rows = [
        ("dry weight", str(made.dry_weight)),
        ("before", f"{made.before}%"),
        ("after", f"{made.after}%"),
        ("restored", str(made.restored)),
        ("added", str(made.added)),
        ("gain", f"{made.gain}%"),
        ("ceiling", "over" if made.over_ceiling else "inside"),
    ]
    if price:
        rows.append(("water worth", str(made.value_of_water(CentsPerPound.parse(price)))))
    click.echo(render_pairs(rows))


@bale.command("wrap")
@click.argument("bags", type=int)
@click.argument("ties", type=int)
@click.option("--to-gin", type=int, default=0, show_default=True, help="Bales still to gin.")
@click.option("--bag-cost", default="6.40", show_default=True, help="What a bag cost.")
@click.option("--tie-cost", default="0.85", show_default=True, help="What a tie cost.")
@click.pass_obj
def wrap(
    session: Session, bags: int, ties: int, to_gin: int, bag_cost: str, tie_cost: str
) -> None:
    """Say whether the bagging and ties will see the season out."""
    store = TareStore()
    when = session.season.start
    store.extend(
        [
            Delivery(BAGS, when, bags, Money.parse(bag_cost), "WRAPCO"),
            Delivery(TIES, when, ties, Money.parse(tie_cost), "WRAPCO"),
        ]
    )
    short = store.short_for(to_gin) if to_gin else {}
    click.echo(
        render_pairs(
            [
                ("bags", str(store.on_hand(BAGS))),
                ("ties", str(store.on_hand(TIES))),
                ("bales it wraps", str(store.bales_left())),
                ("value", str(store.value())),
                ("a bale costs", str(store.cost_per_bale())),
                (
                    "short for the season",
                    ", ".join(f"{count} {kind}" for kind, count in short.items()) or "nothing",
                ),
            ]
        )
    )
