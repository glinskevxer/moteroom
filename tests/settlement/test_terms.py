from moteroom.core.money import CentsPerPound, Money
from moteroom.settlement.charges import ChargeSchedule
from moteroom.settlement.seed import SeedTerms
from moteroom.settlement.terms import Terms


def terms() -> Terms:
    return Terms(
        charges=ChargeSchedule(
            ginning_per_cwt=Money.parse("4.25"),
            bagging_and_ties=Money.parse("11.50"),
            module_handling=Money.parse("18.00"),
            drying_per_cwt=Money.parse("0.65"),
            minimum_per_bale=Money.parse("60.00"),
        ),
        seed=SeedTerms(
            price_per_ton=Money.parse("205.00"),
            gin_shares=1,
            producer_shares=3,
            hauling_per_ton=Money.parse("12.50"),
        ),
        base_rate=CentsPerPound.of("52.00"),
    )


def test_the_terms_hold_three_schedules():
    made = terms()
    assert made.charges.ginning_per_cwt == Money.parse("4.25")
    assert made.seed.gin_shares == 1
    assert made.base_rate == CentsPerPound.of("52.00")


def test_the_notice_board_reads_in_order():
    named = terms().lines()
    assert [name for name, _ in named][0] == "ginning per cwt"
    assert [name for name, _ in named][-1] == "base loan rate"


def test_the_shares_read_as_a_ratio():
    assert dict(terms().lines())["seed shares"] == "1:3"


def test_terms_compare_by_value():
    assert terms() == terms()
