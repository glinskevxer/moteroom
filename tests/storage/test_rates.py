from datetime import date
from decimal import Decimal

import pytest

from moteroom.core.errors import ConflictError, NotFoundError
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.season import Season
from moteroom.settlement.charges import ChargeSchedule
from moteroom.settlement.seed import SeedTerms
from moteroom.settlement.terms import Terms
from moteroom.storage.book import Book
from moteroom.storage.rates import RatesRepository, default_terms

SEASON = Season(2025)
DAY = date(2025, 8, 4)


@pytest.fixture()
def rates():
    with Book.open() as book:
        yield RatesRepository(book.connection)


def test_the_defaults_are_a_complete_set_of_terms():
    terms = default_terms()
    assert terms.base_rate == CentsPerPound.of("52.00")
    assert terms.seed.gin_shares == 1
    assert terms.charges.ginning_per_cwt == Money.parse("4.25")


def test_rates_post_and_read_back(rates):
    rates.post(SEASON, default_terms(), DAY)
    read = rates.get(SEASON)
    assert read == default_terms()
    assert rates.posted(SEASON)


def test_rates_post_once_per_season(rates):
    rates.post(SEASON, default_terms(), DAY)
    with pytest.raises(ConflictError):
        rates.post(SEASON, default_terms(), DAY)


def test_a_season_nobody_posted(rates):
    with pytest.raises(NotFoundError):
        rates.get(SEASON)
    assert not rates.posted(SEASON)


def test_two_seasons_are_kept_apart(rates):
    rates.post(SEASON, default_terms(), DAY)
    other = Terms(
        charges=ChargeSchedule(
            ginning_per_cwt=Money.parse("4.75"),
            bagging_and_ties=Money.parse("12.25"),
            module_handling=Money.parse("19.00"),
        ),
        seed=SeedTerms(price_per_ton=Money.parse("180.00"), gin_shares=1, producer_shares=1),
        base_rate=CentsPerPound.of("50.50"),
    )
    rates.post(Season(2026), other, date(2026, 8, 4))
    assert rates.get(SEASON).base_rate == CentsPerPound.of("52.00")
    assert rates.get(Season(2026)).base_rate == CentsPerPound.of("50.50")
    assert rates.seasons() == [SEASON, Season(2026)]


def test_the_notice_board_lines_read_back(rates):
    rates.post(SEASON, default_terms(), DAY)
    named = dict(rates.lines(SEASON))
    assert named["ginning per cwt"] == "$4.25"
    assert named["seed shares"] == "1:3"
    assert named["base loan rate"] == "52.00c"


def test_every_money_field_survives_the_round_trip(rates):
    rates.post(SEASON, default_terms(), DAY)
    read = rates.get(SEASON)
    assert read.charges.drying_per_cwt.amount == Decimal("0.65")
    assert read.seed.hauling_per_ton.amount == Decimal("12.50")
