"""One producer's season, pulled together.

A grower rings up in February and asks how they did. The answer is spread
across five tables and nobody wants to run five commands to give it, so this
gathers it: what they brought in, what it ginned out at, how their cotton
classed against everybody else's, and where the money got to.

The comparison is the part that is worth having. A turnout of 35 percent means
nothing on its own and a great deal next to the plant's average.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from moteroom.core.money import Money
from moteroom.core.reading import share
from moteroom.core.season import Season
from moteroom.core.weight import Weight, total
from moteroom.storage.book import Book
from moteroom.storage.registry import Repositories


@dataclass(frozen=True)
class Standing:
    """What one producer's season came to, and how it sits against the plant."""

    producer: str
    season: Season
    modules: int
    seed_cotton: Weight
    dry_seed_cotton: Weight
    lots: tuple[str, ...]
    bales: int
    lint: Weight
    plant_turnout: Decimal
    settled: bool
    net: Money
    advanced: Money
    cheques: int

    @property
    def turnout(self) -> Decimal:
        """Their lint over their seed cotton, which is not the plant's number."""
        return share(self.lint.pounds, self.seed_cotton.pounds)

    @property
    def against_the_plant(self) -> Decimal:
        """How far their turnout sits from the plant's, in points."""
        return self.turnout - self.plant_turnout

    @property
    def average_module(self) -> Weight:
        if self.modules == 0:
            return Weight.zero()
        return Weight(self.seed_cotton.pounds // self.modules)

    @property
    def wet_share(self) -> Decimal:
        """How much of the scale weight was water above the reference."""
        if self.seed_cotton.is_zero:
            return Decimal("0.00")
        lost = self.seed_cotton.pounds - self.dry_seed_cotton.pounds
        return share(lost, self.seed_cotton.pounds)

    def lines(self) -> list[tuple[str, str]]:
        """The answer, in the order somebody asks the questions."""
        return [
            ("producer", self.producer),
            ("season", str(self.season)),
            ("modules", str(self.modules)),
            ("seed cotton", str(self.seed_cotton)),
            ("average module", str(self.average_module)),
            ("water over the reference", f"{self.wet_share}%"),
            ("lots", ", ".join(self.lots) or "none"),
            ("bales", str(self.bales)),
            ("lint", str(self.lint)),
            ("turnout", f"{self.turnout}%"),
            ("plant turnout", f"{self.plant_turnout}%"),
            ("against the plant", f"{self.against_the_plant:+}"),
            ("settled", "yes" if self.settled else "not yet"),
            ("net", str(self.net)),
            ("advanced", str(self.advanced)),
            ("cheques", str(self.cheques)),
        ]

    def __str__(self) -> str:
        return f"{self.producer} {self.season}: {self.bales} bales, {self.lint}"


def standing(book: Book, season: Season, producer: str) -> Standing:
    """Gather one producer's season out of the book."""
    from moteroom.service.settlement import SettlementService
    from moteroom.storage.rates import default_terms

    repos = Repositories(book.connection)
    tickets = [one for one in repos.tickets.book(season).live() if one.producer == producer]
    runs = repos.lots.for_season(season)
    plant_lint = total([run.lint for run in runs])
    plant_seed_cotton = total([run.seed_cotton for run in runs])
    terms = repos.rates.get(season) if repos.rates.posted(season) else default_terms()
    shares = SettlementService(book, terms).shares_for(season, producer)
    written = [one for one in repos.statements.for_season(season) if one.producer == producer]
    return Standing(
        producer=producer,
        season=season,
        modules=len(tickets),
        seed_cotton=total([one.net for one in tickets]),
        dry_seed_cotton=total([one.dry_weight() for one in tickets]),
        lots=tuple(one.lot for one in shares),
        bales=sum(one.bales for one in shares),
        lint=total([one.lint for one in shares]),
        plant_turnout=share(plant_lint.pounds, plant_seed_cotton.pounds),
        settled=bool(written),
        net=written[0].net if written else Money.zero(),
        advanced=repos.advances.total(season, producer),
        cheques=len(repos.cheques.for_payee(season, producer)),
    )
