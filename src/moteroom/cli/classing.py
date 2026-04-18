"""Classing commands.

Loading a transfer is the one command that carries on after an error. The
office sends a file a week and a single unreadable line in it must not stop
the other four hundred bales from being classed, so the rejects are reported
and the rest goes in.
"""

from __future__ import annotations

from pathlib import Path

import click

from moteroom.classing.calibration import MEASURES, CalibrationLog, Check, Standard
from moteroom.classing.reclass import Request, render_requests
from moteroom.classing.sample import cut
from moteroom.classing.transfer import parse_file
from moteroom.cli.context import Session
from moteroom.cli.options import on_option, read_date, read_pairs
from moteroom.cli.output import render_pairs, render_table
from moteroom.core.errors import ConflictError, ValidationError
from moteroom.core.ids import BaleId


@click.group()
def card() -> None:
    """Classing cards back from the office."""


@card.command("load")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_obj
def load_cards(session: Session, path: Path) -> None:
    """Load a classing transfer file."""
    transfer = parse_file(path.read_text(encoding="utf-8"))
    skipped: list[tuple[str, str]] = []
    with session.writing() as repos:
        known = {str(one.bale_id) for one in repos.bales.for_season(session.season)}
        filing = []
        for record in transfer.records:
            key = str(record.bale_id)
            if key not in known:
                skipped.append((key, "no such bale here"))
                continue
            if repos.cards.has(record.bale_id):
                skipped.append((key, "already classed"))
                continue
            filing.append(record)
        loaded = repos.cards.add_all(filing)
    click.echo(f"loaded {loaded} of {transfer.declared} from {transfer.office}")
    for reject in transfer.rejects:
        click.echo(f"  rejected {reject}")
    for key, reason in skipped:
        click.echo(f"  skipped {key}: {reason}")


@card.command("show")
@click.argument("bale_id")
@click.pass_obj
def show_card(session: Session, bale_id: str) -> None:
    """One card, as the office sent it."""
    found = session.open_repos().cards.get(BaleId.parse(bale_id))
    click.echo(
        render_pairs(
            [
                ("bale", found.bale_id.grouped()),
                ("classed", found.classed_on.isoformat()),
                ("office", found.office),
                ("colour", f"{found.color} {found.color.name}"),
                ("leaf", f"{found.leaf} {found.leaf.name}"),
                ("staple", f"{found.staple} ({found.staple.inches} in)"),
                ("micronaire", str(found.micronaire)),
                ("strength", str(found.strength)),
                ("uniformity", str(found.uniformity)),
                ("trash", str(found.trash)),
                ("findings", " ".join(found.codes) if found.codes else "none"),
            ]
        )
    )


@card.command("list")
@click.pass_obj
def list_cards(session: Session) -> None:
    """Every card back this season."""
    rows = [
        [
            str(found.bale_id),
            str(found.color),
            str(found.leaf),
            str(found.staple),
            str(found.micronaire),
            " ".join(found.codes),
        ]
        for found in session.open_repos().cards.for_season(session.season)
    ]
    click.echo(
        render_table(
            ["bale", "colour", "leaf", "staple", "mike", "findings"], rows, right=(3, 4)
        )
    )


@card.command("waiting")
@click.pass_obj
def waiting(session: Session) -> None:
    """Bales pressed with no card back yet."""
    outstanding = session.open_repos().cards.unclassed(session.season)
    rows = [[str(one), one.grouped()] for one in outstanding]
    click.echo(render_table(["bale", "tag"], rows))
    click.echo()
    click.echo(f"{len(outstanding)} waiting")


@card.command("correct")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_obj
def correct_cards(session: Session, path: Path) -> None:
    """Take a corrected transfer over cards already on file."""
    transfer = parse_file(path.read_text(encoding="utf-8"))
    if transfer.rejects:
        raise ValidationError("transfer", "a correction file has to read cleanly")
    replaced = 0
    with session.writing() as repos:
        cards = repos.cards
        for record in transfer.records:
            if not cards.has(record.bale_id):
                raise ConflictError("card", str(record.bale_id), "was never classed")
            cards.replace(record)
            replaced += 1
    click.echo(f"replaced {replaced} cards")


@card.command("reclass")
@click.argument("bales", nargs=-1)
@click.option("--reason", required=True, help="Why the bale is going back.")
@click.option("--by", "asked_by", required=True, help="Who is asking.")
@click.option("--out", "out_path", default=None, help="Write the file here instead of stdout.")
@on_option("Request date")
@click.pass_obj
def reclass(
    session: Session,
    bales: tuple[str, ...],
    reason: str,
    asked_by: str,
    out_path: str | None,
    on_text: str | None,
) -> None:
    """Ask the office to look at a bale again."""
    if not bales:
        raise ValidationError("bales", "a re-class has to name a bale")
    repos = session.open_repos()
    when = read_date(on_text, session.season.end)
    office = repos.settings.get_or("classing_office", "MEMPHIS")
    requests = []
    for text in bales:
        tag = BaleId.parse(text)
        repos.cards.get(tag)
        requests.append(
            Request(
                bale_id=tag, asked_on=when, reason=reason, asked_by=asked_by.strip().upper()
            )
        )
    made = render_requests(requests, office, when)
    if out_path:
        Path(out_path).write_text(made + "\n", encoding="utf-8")
        click.echo(f"{len(requests)} bales back to {office}, written to {out_path}")
        return
    click.echo(made)


@card.command("calibrate")
@click.argument("standard_name")
@click.argument("readings", nargs=-1)
@click.option("--assigned", required=True, help="Assigned values as measure=value pairs.")
@click.option("--by", "operator", default="OFFICE", show_default=True, help="Who ran it.")
@on_option("Check date")
@click.pass_obj
def calibrate(
    session: Session,
    standard_name: str,
    readings: tuple[str, ...],
    assigned: str,
    operator: str,
    on_text: str | None,
) -> None:
    """Check the classing line against a standard and say whether it is out."""
    made = Standard(standard_name.strip().upper(), read_pairs(assigned, "assigned"))
    run = Check(
        standard=made,
        checked_on=read_date(on_text, session.season.start),
        readings=read_pairs(",".join(readings), "readings"),
        operator=operator.strip().upper(),
    )
    log = CalibrationLog()
    log.add(run)
    rows = [
        [
            measure,
            str(made.values[measure]),
            str(run.readings[measure]),
            f"{run.deviation(measure):+}",
            "ok" if run.within(measure) else "out",
        ]
        for measure in MEASURES
    ]
    click.echo(
        render_table(["measure", "assigned", "read", "off by", "state"], rows, right=(1, 2, 3))
    )
    click.echo()
    click.echo(str(run))


@card.command("sample")
@click.argument("bale_id")
@click.option("--by", "cut_by", required=True, help="Who cut the samples.")
@click.option("--grams", type=int, default=100, show_default=True, help="Grams a side.")
@on_option("Sampling date")
@click.pass_obj
def sample(
    session: Session, bale_id: str, cut_by: str, grams: int, on_text: str | None
) -> None:
    """Cut both samples off a bale for the office."""
    tag = BaleId.parse(bale_id)
    session.open_repos().bales.get(tag)
    made = cut(tag, read_date(on_text, session.season.start), cut_by.strip().upper(), grams)
    click.echo(
        render_pairs(
            [
                ("bale", tag.grouped()),
                ("cut", made.first.cut_on.isoformat()),
                ("by", made.first.cut_by),
                ("side a", f"{made.first.grams}g"),
                ("side b", f"{made.second.grams}g"),
                ("enough", "yes" if made.is_enough else "no"),
            ]
        )
    )
