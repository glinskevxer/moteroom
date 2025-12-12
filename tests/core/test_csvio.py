import pytest

from moteroom.core.csvio import field, normalise, read_rows, write_rows
from moteroom.core.errors import ValidationError

FILE = "Module ID,Producer,Gross\nHW-004181,BLYTHE,38400\nHW-004182,BLYTHE,39100\n"


def test_a_header_normalises():
    assert normalise(" Module ID ") == "moduleid"
    assert normalise("module_id") == "moduleid"


def test_a_file_reads_by_header_name():
    rows = read_rows(FILE, ["module id", "producer"])
    assert rows[0]["moduleid"] == "HW-004181"
    assert rows[1]["gross"] == "39100"
    assert len(rows) == 2


def test_the_column_order_does_not_matter():
    swapped = "Gross,Producer,Module ID\n38400,BLYTHE,HW-004181\n"
    assert read_rows(swapped, ["module id"])[0]["moduleid"] == "HW-004181"


def test_a_blank_line_is_skipped():
    assert len(read_rows(FILE + ",,\n", ["module id"])) == 2


def test_an_empty_file_is_refused():
    with pytest.raises(ValidationError):
        read_rows("", ["module id"])


def test_a_missing_column_is_named():
    with pytest.raises(ValidationError) as caught:
        read_rows(FILE, ["module id", "tare"])
    assert "tare" in caught.value.message


def test_a_repeated_column_is_refused():
    with pytest.raises(ValidationError):
        read_rows("a,A\n1,2\n", ["a"])


def test_a_short_row_is_refused():
    with pytest.raises(ValidationError) as caught:
        read_rows(FILE + "HW-004183,BLYTHE\n", ["module id"])
    assert "row 4" in caught.value.message


def test_a_field_comes_out_by_the_name_the_caller_knows():
    row = read_rows(FILE, ["module id"])[0]
    assert field(row, "Module ID") == "HW-004181"
    assert field(row, "module_id") == "HW-004181"


def test_a_field_nobody_has():
    with pytest.raises(ValidationError):
        field(read_rows(FILE, ["module id"])[0], "tare")


def test_writing_a_csv_quotes_what_needs_it():
    text = write_rows(["a", "b"], [["1", "x,y"]])
    assert text.splitlines()[1] == '1,"x,y"'


def test_writing_refuses_a_row_that_does_not_match():
    with pytest.raises(ValidationError):
        write_rows(["a", "b"], [["1"]])


def test_a_written_file_reads_back():
    text = write_rows(["module id", "producer"], [["HW-004181", "BLYTHE"]])
    assert read_rows(text, ["module id"])[0]["producer"] == "BLYTHE"
