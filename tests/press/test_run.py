from datetime import date
from decimal import Decimal

import pytest

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.ids import MAX_BALE_NUMBER, BaleId, GinCode, LotId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.press.bale import Bale
from moteroom.press.run import BalePress

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 42)
DAY = date(2025, 10, 16)


def press(first: int = 1) -> BalePress:
    return BalePress(SEASON, GIN, first)


def one(made: BalePress, lot: LotId = LOT, gross: int = 538) -> Bale:
    return made.press(lot, DAY, Weight(gross), Weight(23), Decimal("6.4"))


def test_the_counter_runs_forward():
    made = press()
    first = one(made)
    second = one(made)
    assert first.number == 1
    assert second.number == 2
    assert made.next_number == 3
    assert len(made) == 2


def test_the_counter_can_start_partway_through_a_season():
    made = press(1_204)
    assert one(made).number == 1_204


@pytest.mark.parametrize("first", [0, MAX_BALE_NUMBER + 1])
def test_the_counter_cannot_start_off_the_end(first):
    with pytest.raises(ValidationError):
        BalePress(SEASON, GIN, first)


def test_the_counter_runs_out():
    made = press(MAX_BALE_NUMBER)
    one(made)
    with pytest.raises(ConflictError) as caught:
        one(made)
    assert caught.value.kind == "press"


def test_a_lot_from_another_season_is_refused():
    with pytest.raises(ValidationError):
        one(press(), lot=LotId(Season(2024), 42))


def test_a_closed_lot_takes_no_more_bales():
    made = press()
    one(made)
    made.close(LOT)
    assert made.is_closed(LOT)
    with pytest.raises(ConflictError):
        one(made)


def test_a_lot_nobody_pressed_cannot_be_closed():
    with pytest.raises(NotFoundError):
        press().close(LOT)


def test_bales_are_kept_per_lot():
    made = press()
    other = LotId(SEASON, 43)
    one(made)
    one(made, lot=other)
    assert [b.number for b in made.for_lot(LOT)] == [1]
    assert [b.number for b in made.for_lot(other)] == [2]


def test_lint_totals_by_lot_and_for_the_season():
    made = press()
    one(made, gross=538)
    one(made, gross=548)
    assert made.lint(LOT) == Weight(515 + 525)
    assert made.lint() == Weight(515 + 525)


def test_a_bale_can_be_found_by_its_tag():
    made = press()
    bale = one(made)
    assert made.find(bale.bale_id) == bale


def test_looking_for_a_bale_nobody_pressed():
    with pytest.raises(NotFoundError):
        press().find(BaleId.build(SEASON, GIN, 9))


def test_a_restart_picks_the_counter_back_up():
    made = press()
    bale = one(made)
    restarted = press()
    restarted.restore([bale])
    assert restarted.next_number == 2
    assert len(restarted) == 1


def test_a_restart_refuses_a_bale_from_another_gin():
    other = BalePress(SEASON, GinCode("41208"), 1)
    bale = one(other)
    with pytest.raises(ValidationError):
        press().restore([bale])


def test_a_restart_refuses_the_same_bale_twice():
    made = press()
    bale = one(made)
    with pytest.raises(ConflictError):
        made.restore([bale])
