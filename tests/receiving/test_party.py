from decimal import Decimal

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money, total_money
from moteroom.core.weight import Weight
from moteroom.receiving.party import Farm, Producer, ShareSplit


def test_a_producer_carries_a_code_and_a_name():
    grower = Producer.parse(" blythe ", " Blythe Farms ")
    assert grower.code == "BLYTHE"
    assert str(grower) == "BLYTHE Blythe Farms"


@pytest.mark.parametrize("code", ["", "b", "1BLYTHE", "BLYTHE FARMS", "B" * 13])
def test_a_producer_code_has_a_shape(code):
    with pytest.raises(ValidationError):
        Producer(code, "Blythe Farms")


def test_a_producer_needs_a_name():
    with pytest.raises(ValidationError):
        Producer("BLYTHE", "   ")


def test_a_farm_is_a_number_and_a_tract():
    farm = Farm("3312", "1140", "BLYTHE", Decimal("284.50"))
    assert farm.key == "3312-1140"
    assert str(farm) == "farm 3312 tract 1140"


@pytest.mark.parametrize(
    ("number", "tract", "producer", "acres"),
    [
        ("", "1140", "BLYTHE", Decimal("10.00")),
        ("3312", "", "BLYTHE", Decimal("10.00")),
        ("3312", "1140", "blythe", Decimal("10.00")),
        ("3312", "1140", "BLYTHE", Decimal("0.00")),
        ("3312", "1140", "BLYTHE", Decimal("-1.00")),
        ("3312", "1140", "BLYTHE", Decimal("10.005")),
        ("3312", "1140", "BLYTHE", Decimal("50000.01")),
        ("33A2", "1140", "BLYTHE", Decimal("10.00")),
    ],
)
def test_a_farm_refuses_junk(number, tract, producer, acres):
    with pytest.raises(ValidationError):
        Farm(number, tract, producer, acres)


def test_a_whole_share_is_one_owner():
    split = ShareSplit.whole("BLYTHE")
    assert split.codes == ("BLYTHE",)
    assert split.total_shares == 1


def test_a_lease_line_reads_back():
    split = ShareSplit.parse("blythe:3, merritt:1")
    assert split.codes == ("BLYTHE", "MERRITT")
    assert split.share_of("MERRITT") == 1
    assert str(split) == "BLYTHE:3,MERRITT:1"


@pytest.mark.parametrize("text", ["", "BLYTHE", "BLYTHE:", "BLYTHE:x", ":3"])
def test_a_lease_line_refuses_junk(text):
    with pytest.raises(ValidationError):
        ShareSplit.parse(text)


def test_a_split_refuses_a_repeated_owner():
    with pytest.raises(ValidationError):
        ShareSplit((("BLYTHE", 1), ("BLYTHE", 2)))


def test_a_split_refuses_nothing_at_all():
    with pytest.raises(ValidationError):
        ShareSplit(())
    with pytest.raises(ValidationError):
        ShareSplit((("BLYTHE", 0), ("MERRITT", 0)))


def test_a_split_refuses_a_negative_or_fractional_share():
    with pytest.raises(ValidationError):
        ShareSplit((("BLYTHE", -1),))
    with pytest.raises(ValidationError):
        ShareSplit((("BLYTHE", True),))


def test_asking_for_a_share_nobody_holds():
    with pytest.raises(ValidationError):
        ShareSplit.whole("BLYTHE").share_of("MERRITT")


def test_weight_splits_and_still_adds_up():
    split = ShareSplit.parse("BLYTHE:3,MERRITT:1")
    parts = split.split_weight(Weight(4_001))
    assert sum(w.pounds for w in parts.values()) == 4_001
    assert parts["BLYTHE"] == Weight(3_001)
    assert parts["MERRITT"] == Weight(1_000)


def test_money_splits_and_still_adds_up():
    split = ShareSplit.parse("BLYTHE:1,MERRITT:1,COLE:1")
    parts = split.split_money(Money.parse("100.00"))
    assert total_money(list(parts.values())) == Money.parse("100.00")
    assert set(parts) == {"BLYTHE", "MERRITT", "COLE"}


def test_a_zero_share_owner_gets_nothing():
    split = ShareSplit((("BLYTHE", 1), ("MERRITT", 0)))
    assert split.split_weight(Weight(1_000))["MERRITT"].is_zero
    assert split.split_money(Money.parse("10.00"))["MERRITT"].is_zero
