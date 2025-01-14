import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.weight import MAX_POUNDS, Weight, total


def test_weight_holds_whole_pounds():
    assert Weight(48_320).pounds == 48_320


def test_weight_refuses_a_negative():
    with pytest.raises(ValidationError) as caught:
        Weight(-1)
    assert caught.value.field == "pounds"


def test_weight_refuses_a_bool():
    with pytest.raises(ValidationError):
        Weight(True)


def test_weight_refuses_an_absurd_load():
    with pytest.raises(ValidationError):
        Weight(MAX_POUNDS + 1)


def test_zero_is_zero():
    assert Weight.zero().is_zero
    assert not Weight(1).is_zero


@pytest.mark.parametrize(
    ("text", "pounds"),
    [
        ("48320", 48_320),
        (" 48,320 ", 48_320),
        ("48320 lb", 48_320),
        ("48320 lbs", 48_320),
        ("0", 0),
    ],
)
def test_parse_reads_a_ticket(text, pounds):
    assert Weight.parse(text) == Weight(pounds)


@pytest.mark.parametrize("text", ["", "   ", "abc", "48.5", "-3"])
def test_parse_refuses_junk(text):
    with pytest.raises(ValidationError):
        Weight.parse(text)


def test_addition_and_subtraction():
    assert Weight(1_200) + Weight(300) == Weight(1_500)
    assert Weight(1_200) - Weight(300) == Weight(900)


def test_subtraction_cannot_go_below_zero():
    with pytest.raises(ValidationError):
        Weight(300) - Weight(301)


def test_weights_order_and_print():
    assert Weight(100) < Weight(101)
    assert str(Weight(48_320)) == "48,320 lb"


def test_hundredweight():
    assert str(Weight(48_320).hundredweight()) == "483.20"


def test_share_rounds_half_up():
    assert Weight(1_001).share(1, 2) == Weight(501)
    assert Weight(1_000).share(1, 4) == Weight(250)
    assert Weight(1_000).share(0, 4) == Weight.zero()


@pytest.mark.parametrize(("num", "den"), [(1, 0), (3, 2), (-1, 2)])
def test_share_refuses_a_bad_split(num, den):
    with pytest.raises(ValidationError):
        Weight(1_000).share(num, den)


def test_total_adds_a_run():
    assert total([Weight(10), Weight(20), Weight(30)]) == Weight(60)
    assert total([]) == Weight.zero()
