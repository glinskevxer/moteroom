from datetime import date

import pytest

from moteroom.classing.transfer import parse_file, parse_line
from moteroom.core.errors import MoteroomError, ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season

GIN = GinCode("41207")
BALE = str(BaleId.build(Season(2025), GIN, 1_204))
OTHER = str(BaleId.build(Season(2025), GIN, 1_205))


def line(bale: str = BALE, tail: str = "        ") -> str:
    return f"{bale}20251022MEMPHIS 04336294812313042{tail}"


def transfer(*body: str, declared: int | None = None) -> str:
    count = len(body) if declared is None else declared
    head = f"HDRMEMPHIS 20251022{count:06d}"
    return "\n".join([head, *body, f"TRL{count:06d}"])


def test_a_line_reads_into_a_card():
    card = parse_line(line())
    assert str(card.bale_id) == BALE
    assert card.classed_on == date(2025, 10, 22)
    assert card.office == "MEMPHIS"
    assert str(card.micronaire) == "4.3"
    assert str(card.staple) == "36"
    assert str(card.strength) == "29.4"
    assert str(card.uniformity) == "81.2"
    assert str(card.color) == "31"
    assert str(card.leaf) == "3"
    assert str(card.trash) == "0.42"
    assert card.codes == ()


def test_a_line_carries_up_to_four_findings():
    card = parse_line(line(tail="B2G1    "))
    assert card.codes == ("B2", "G1")


def test_a_short_line_is_refused():
    with pytest.raises(ValidationError):
        parse_line(line()[:40])


def test_a_line_with_a_bad_date_is_refused():
    with pytest.raises(ValidationError):
        parse_line(line().replace("20251022", "20251332", 1))


def test_a_line_with_a_bad_reading_is_refused():
    with pytest.raises(ValidationError):
        parse_line(line().replace("043", "xxx", 1))


def test_a_line_with_a_bad_staple_is_refused():
    with pytest.raises(ValidationError):
        parse_line(line().replace("04336", "043xx", 1))


def test_a_file_reads_end_to_end():
    read = parse_file(transfer(line(), line(OTHER)))
    assert read.office == "MEMPHIS"
    assert read.sent_on == date(2025, 10, 22)
    assert len(read.records) == 2
    assert read.is_clean
    assert read.declared == 2


def test_a_bad_line_is_set_aside_and_the_rest_loads():
    read = parse_file(transfer(line(), "junk"))
    assert len(read.records) == 1
    assert len(read.rejects) == 1
    assert read.rejects[0].line_number == 3
    assert not read.is_clean
    assert str(read.rejects[0]).startswith("line 3:")


@pytest.mark.parametrize("text", ["", "   \n  "])
def test_an_empty_transfer_is_refused(text):
    with pytest.raises(MoteroomError):
        parse_file(text)


def test_a_transfer_without_a_header_is_refused():
    with pytest.raises(MoteroomError):
        parse_file(f"{line()}\nTRL000001")


def test_a_transfer_without_a_trailer_is_refused():
    with pytest.raises(MoteroomError):
        parse_file(f"HDRMEMPHIS 20251022000001\n{line()}")


def test_a_header_that_will_not_read_is_refused():
    with pytest.raises(MoteroomError):
        parse_file(f"HDRMEMPHIS 2025xx22000001\n{line()}\nTRL000001")


def test_a_header_and_trailer_that_disagree():
    with pytest.raises(MoteroomError):
        parse_file(f"HDRMEMPHIS 20251022000002\n{line()}\nTRL000001")


def test_a_truncated_transfer_is_caught_by_the_count():
    with pytest.raises(MoteroomError):
        parse_file(transfer(line(), declared=4))
