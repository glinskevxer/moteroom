from decimal import Decimal

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.reading import HUNDREDTH, TENTH, checked, ratio, share


def test_a_reading_inside_the_range_comes_back():
    assert checked(Decimal("4.3"), "mike", Decimal("2.0"), Decimal("6.9")) == Decimal("4.3")
    assert checked("4.3", "mike", Decimal("2.0"), Decimal("6.9")) == Decimal("4.3")


def test_both_ends_of_the_range_are_inside_it():
    assert checked(Decimal("2.0"), "mike", Decimal("2.0"), Decimal("6.9")) == Decimal("2.0")
    assert checked(Decimal("6.9"), "mike", Decimal("2.0"), Decimal("6.9")) == Decimal("6.9")


@pytest.mark.parametrize("value", ["1.9", "7.0"])
def test_a_reading_off_the_range_is_refused(value):
    with pytest.raises(ValidationError):
        checked(Decimal(value), "mike", Decimal("2.0"), Decimal("6.9"))


def test_a_reading_finer_than_the_step_is_refused():
    with pytest.raises(ValidationError):
        checked(Decimal("4.35"), "mike", Decimal("2.0"), Decimal("6.9"), TENTH)
    assert checked(Decimal("4.35"), "mike", Decimal("2.0"), Decimal("6.9"), HUNDREDTH)


def test_a_reading_that_is_not_a_number_is_refused():
    with pytest.raises(ValidationError):
        checked(4.3, "mike", Decimal("2.0"), Decimal("6.9"))  # type: ignore[arg-type]


def test_the_field_name_comes_back_with_the_error():
    with pytest.raises(ValidationError) as caught:
        checked(Decimal("9.9"), "trash", Decimal("0.0"), Decimal("1.0"))
    assert caught.value.field == "trash"


def test_a_ratio_is_a_percentage_to_a_hundredth():
    assert ratio(1, 3) == Decimal("33.33")
    assert ratio(2, 3) == Decimal("66.67")
    assert ratio(-500, 22_300) == Decimal("-2.24")


def test_a_ratio_of_nothing_is_refused():
    with pytest.raises(ValidationError) as caught:
        ratio(1, 0, "sheet_lint")
    assert caught.value.field == "sheet_lint"


def test_a_share_of_nothing_is_nothing_rather_than_an_error():
    assert share(0, 0) == Decimal("0.00")
    assert share(1, 0) == Decimal("0.00")
    assert share(1, 3) == Decimal("33.33")
