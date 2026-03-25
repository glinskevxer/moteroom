"""Writing the season out to a folder.

At the end of a season somebody wants the whole thing as files: one csv per
report, one page per producer, in a folder they can put on a stick and hand to
the accountant. Nothing here is new information. It is the same reports written
somewhere other than a terminal, which is why it lives above them rather than
inside them.

Files are written into a folder named for the season, and an export refuses to
write over one that is already there rather than mixing two runs together.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from moteroom.core.errors import ValidationError
from moteroom.core.season import Season
from moteroom.core.weight import total
from moteroom.reporting import position, quality
from moteroom.reporting.daily import daily_sheet
from moteroom.reporting.report import Report
from moteroom.reporting.settlement import settlement_summary, statement_report
from moteroom.storage.book import Book
from moteroom.storage.registry import Repositories


@dataclass(frozen=True)
class Export:
    """What an export wrote and where."""

    folder: Path
    files: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(self.files)

    def __str__(self) -> str:
        return f"{self.count} files in {self.folder}"


def reports(book: Book, season: Season, as_of: date) -> dict[str, Report]:
    """Every report an export writes, by the name of its file."""
    repos = Repositories(book.connection)
    cards = repos.cards.for_season(season)
    runs = repos.lots.for_season(season)
    bales = repos.bales.for_season(season)
    receipts = repos.receipts.outstanding()
    written = repos.statements.for_season(season)
    made = {
        "colour": quality.colour_distribution(cards),
        "leaf": quality.leaf_distribution(cards),
        "staple": quality.staple_distribution(cards),
        "findings": quality.findings_report(cards),
        "averages": quality.averages(cards),
        "position": position.by_house(receipts, as_of),
        "holdings": position.by_holder(receipts, as_of),
        "settlements": settlement_summary(written),
    }
    for run in runs:
        key = f"gin-sheet-{run.ginned_on.isoformat()}"
        made[key] = daily_sheet(run.ginned_on, runs, bales)
    for statement in written:
        made[f"statement-{statement.producer.lower()}"] = statement_report(statement)
    return made


def write(book: Book, season: Season, into: Path, as_of: date) -> Export:
    """Write the season into a folder named for it."""
    folder = into / f"moteroom-{season.year}"
    if folder.exists():
        raise ValidationError("folder", f"{folder} is already there")
    folder.mkdir(parents=True)
    written = []
    for name, report in sorted(reports(book, season, as_of).items()):
        path = folder / f"{name}.csv"
        path.write_text(report.to_csv() + "\n", encoding="utf-8")
        written.append(path.name)
    summary = folder / "season.txt"
    summary.write_text(_summary(book, season, as_of), encoding="utf-8")
    written.append(summary.name)
    return Export(folder, tuple(written))


def _summary(book: Book, season: Season, as_of: date) -> str:
    repos = Repositories(book.connection)
    tickets = repos.tickets.book(season)
    runs = repos.lots.for_season(season)
    lines = [
        f"moteroom export for {season}",
        f"written {as_of.isoformat()}",
        "",
        f"producers    {len(tickets.producers())}",
        f"modules      {len(tickets)}",
        f"seed cotton  {tickets.net()}",
        f"lots         {len(runs)}",
        f"lint         {total([run.lint for run in runs])}",
        f"bales        {len(repos.bales.for_season(season))}",
        f"cards        {len(repos.cards.for_season(season))}",
        f"settlements  {len(repos.statements.for_season(season))}",
    ]
    return "\n".join(lines) + "\n"
