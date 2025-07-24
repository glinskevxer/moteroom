"""The daily gin sheet.

What ran yesterday, what it made and how it turned out. It is read standing up
next to the press, so it is one line per lot and the totals are at the bottom.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from moteroom.core.weight import Weight, total
from moteroom.ginning.run import GinRun
from moteroom.ginning.turnout import percent, summarise
from moteroom.press.bale import Bale
from moteroom.reporting.report import Report

HEADERS = ("lot", "modules", "seed cotton", "lint", "seed", "motes", "turnout", "bales")


def daily_sheet(day: date, runs: Sequence[GinRun], bales: Sequence[Bale]) -> Report:
    """One day's ginning, with the totals under it."""
    ran = [run for run in runs if run.ginned_on == day]
    by_lot: dict[str, list[Bale]] = {}
    for one in bales:
        by_lot.setdefault(str(one.lot), []).append(one)
    rows = []
    for run in ran:
        line = summarise(run)
        rows.append(
            (
                str(run.lot),
                str(run.module_count),
                str(run.seed_cotton.pounds),
                str(run.lint.pounds),
                str(run.seed.pounds),
                str(run.motes.pounds),
                str(line.lint_turnout),
                str(len(by_lot.get(str(run.lot), []))),
            )
        )
    notes = _totals(ran, by_lot)
    return Report(
        title=f"gin sheet for {day.isoformat()}",
        headers=HEADERS,
        rows=tuple(rows),
        right=(1, 2, 3, 4, 5, 6, 7),
        notes=notes,
    )


def _totals(runs: Sequence[GinRun], by_lot: dict[str, list[Bale]]) -> tuple[str, ...]:
    if not runs:
        return ("nothing ginned",)
    seed_cotton = total([run.seed_cotton for run in runs])
    lint = total([run.lint for run in runs])
    bales = sum(len(by_lot.get(str(run.lot), [])) for run in runs)
    turnout = percent(lint, seed_cotton)
    return (
        f"{len(runs)} lots, {seed_cotton} in, {lint} of lint, {bales} bales",
        f"turnout {turnout}%",
        f"average bale {_average(lint, bales)}",
    )


def _average(lint: Weight, bales: int) -> str:
    if bales == 0:
        return "no bales"
    return str(Weight(lint.pounds // bales))


def running_turnout(runs: Sequence[GinRun]) -> Decimal:
    """Turnout across every lot given, which is not the average of the lots."""
    if not runs:
        return Decimal("0.00")
    return percent(total([run.lint for run in runs]), total([run.seed_cotton for run in runs]))
