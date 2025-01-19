import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId, check_digit
from moteroom.core.season import Season

GIN = GinCode("41207")


def test_gin_code_is_five_digits():
    assert str(GinCode.parse(" 41207 ")) == "41207"


@pytest.mark.parametrize("code", ["4120", "412077", "4120A", ""])
def test_gin_code_refuses_anything_else(code):
    with pytest.raises(ValidationError):
        GinCode(code)


def test_gin_code_refuses_a_number():
    with pytest.raises(ValidationError):
        GinCode(41207)  # type: ignore[arg-type]


def test_check_digit_closes_the_sum():
    body = "5412070042" + "1"
    digit = check_digit(body)
    assert 0 <= digit <= 9
    assert check_digit(body) == digit


def test_check_digit_refuses_letters():
    with pytest.raises(ValidationError):
        check_digit("54120A")


def test_build_lays_the_id_out_in_order():
    bale = BaleId.build(Season(2025), GIN, 42)
    assert str(bale)[0] == "5"
    assert str(bale)[1:6] == "41207"
    assert str(bale)[6:11] == "00042"
    assert len(str(bale)) == 12


def test_a_built_id_reads_back():
    bale = BaleId.build(Season(2025), GIN, 42)
    assert bale.gin_code == GIN
    assert bale.bale_number == 42
    assert bale.season_digit == 5
    assert bale.belongs_to(Season(2025))
    assert not bale.belongs_to(Season(2026))


def test_a_tag_can_be_read_back_in_groups():
    bale = BaleId.build(Season(2025), GIN, 42)
    assert BaleId.parse(bale.grouped()) == bale
    assert bale.grouped().count("-") == 3


def test_a_transposed_digit_is_caught():
    good = str(BaleId.build(Season(2025), GIN, 12_345))
    swapped = good[:6] + good[7] + good[6] + good[8:]
    assert swapped != good
    with pytest.raises(ValidationError):
        BaleId(swapped)


def test_a_wrong_check_digit_is_caught():
    good = str(BaleId.build(Season(2025), GIN, 42))
    wrong = good[:-1] + str((int(good[-1]) + 1) % 10)
    with pytest.raises(ValidationError):
        BaleId(wrong)


@pytest.mark.parametrize("number", [0, -1, 100_000])
def test_build_refuses_a_bale_number_off_the_press(number):
    with pytest.raises(ValidationError):
        BaleId.build(Season(2025), GIN, number)


def test_build_refuses_a_bool():
    with pytest.raises(ValidationError):
        BaleId.build(Season(2025), GIN, True)


@pytest.mark.parametrize("value", ["", "12345", "54120700042A"])
def test_bale_id_refuses_the_wrong_shape(value):
    with pytest.raises(ValidationError):
        BaleId(value)


def test_bale_id_refuses_a_number():
    with pytest.raises(ValidationError):
        BaleId(541207000426)  # type: ignore[arg-type]


def test_module_id_normalises():
    assert str(ModuleId.parse(" hw-004182 ")) == "HW-004182"


@pytest.mark.parametrize("value", ["", "AB", "-ABCD", "AB CD", "A" * 17])
def test_module_id_refuses_junk(value):
    with pytest.raises(ValidationError):
        ModuleId(value)


def test_module_id_refuses_a_number():
    with pytest.raises(ValidationError):
        ModuleId(4182)  # type: ignore[arg-type]


def test_lot_prints_season_and_number():
    assert str(LotId(Season(2025), 42)) == "2025-0042"


def test_lot_reads_back():
    assert LotId.parse("2025-0042") == LotId(Season(2025), 42)


@pytest.mark.parametrize("text", ["", "2025", "2025-", "2025-abc", "abc-1"])
def test_lot_refuses_junk(text):
    with pytest.raises(ValidationError):
        LotId.parse(text)


@pytest.mark.parametrize("number", [0, 10_000])
def test_lot_refuses_a_number_off_the_book(number):
    with pytest.raises(ValidationError):
        LotId(Season(2025), number)
