"""The rates a season is settled against.

Rates are posted once at the start of a season and then they do not move,
because a producer ginned in October and settled in March has to be settled at
what was posted when their cotton went through. So the table is keyed by
season and a second posting for the same season is refused rather than
overwriting the first.
"""

from __future__ import annotations

from datetime import date

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.season import Season
from moteroom.settlement.charges import ChargeSchedule
from moteroom.settlement.seed import SeedTerms
from moteroom.settlement.terms import Terms
from moteroom.storage import rows as read
from moteroom.storage.repository import Repository

COLUMNS = (
    "season, ginning_per_cwt, bagging_and_ties, module_handling, drying_per_cwt, "
    "minimum_per_bale, seed_price_per_ton, seed_gin_shares, seed_producer_shares, "
    "seed_hauling_per_ton, base_loan_rate, posted_on"
)

DEFAULTS: dict[str, str] = {
    "ginning_per_cwt": "4.25",
    "bagging_and_ties": "11.50",
    "module_handling": "18.00",
    "drying_per_cwt": "0.65",
    "minimum_per_bale": "60.00",
    "seed_price_per_ton": "205.00",
    "seed_hauling_per_ton": "12.50",
    "base_loan_rate": "52.00",
}


class RatesRepository(Repository):
    """Posted rates, one row per season."""

    def post(self, season: Season, terms: Terms, posted_on: date) -> None:
        """Post a season's rates, which can only happen once."""
        self.write(
            f"INSERT INTO season_rates ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                season.year,
                str(terms.charges.ginning_per_cwt.amount),
                str(terms.charges.bagging_and_ties.amount),
                str(terms.charges.module_handling.amount),
                str(terms.charges.drying_per_cwt.amount),
                str(terms.charges.minimum_per_bale.amount),
                str(terms.seed.price_per_ton.amount),
                terms.seed.gin_shares,
                terms.seed.producer_shares,
                str(terms.seed.hauling_per_ton.amount),
                str(terms.base_rate.cents),
                posted_on.isoformat(),
            ),
            lambda: ConflictError("rates", str(season), "are already posted"),
        )

    def get(self, season: Season) -> Terms:
        row = self.connection.execute(
            f"SELECT {COLUMNS} FROM season_rates WHERE season = ?", (season.year,)
        ).fetchone()
        if row is None:
            raise NotFoundError("rates", str(season))
        return Terms(
            charges=ChargeSchedule(
                ginning_per_cwt=read.money(row, "ginning_per_cwt"),
                bagging_and_ties=read.money(row, "bagging_and_ties"),
                module_handling=read.money(row, "module_handling"),
                drying_per_cwt=read.money(row, "drying_per_cwt"),
                minimum_per_bale=read.money(row, "minimum_per_bale"),
            ),
            seed=SeedTerms(
                price_per_ton=read.money(row, "seed_price_per_ton"),
                gin_shares=int(row["seed_gin_shares"]),
                producer_shares=int(row["seed_producer_shares"]),
                hauling_per_ton=read.money(row, "seed_hauling_per_ton"),
            ),
            base_rate=read.rate(row, "base_loan_rate"),
        )

    def posted(self, season: Season) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM season_rates WHERE season = ?", (season.year,)
        ).fetchone()
        return row is not None

    def seasons(self) -> list[Season]:
        rows = self.connection.execute("SELECT season FROM season_rates ORDER BY season")
        return [Season(int(row["season"])) for row in rows]

    def lines(self, season: Season) -> list[tuple[str, str]]:
        """The posted rates as they print on the notice board."""
        return self.get(season).lines()


def default_terms() -> Terms:
    """The rates a new season starts from before anybody posts their own."""
    return Terms(
        charges=ChargeSchedule(
            ginning_per_cwt=Money.parse(DEFAULTS["ginning_per_cwt"]),
            bagging_and_ties=Money.parse(DEFAULTS["bagging_and_ties"]),
            module_handling=Money.parse(DEFAULTS["module_handling"]),
            drying_per_cwt=Money.parse(DEFAULTS["drying_per_cwt"]),
            minimum_per_bale=Money.parse(DEFAULTS["minimum_per_bale"]),
        ),
        seed=SeedTerms(
            price_per_ton=Money.parse(DEFAULTS["seed_price_per_ton"]),
            gin_shares=1,
            producer_shares=3,
            hauling_per_ton=Money.parse(DEFAULTS["seed_hauling_per_ton"]),
        ),
        base_rate=CentsPerPound.parse(DEFAULTS["base_loan_rate"]),
    )
