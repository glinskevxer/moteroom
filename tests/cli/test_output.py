import pytest

from moteroom.cli.output import EMPTY, render_pairs, render_table


def test_a_table_lines_its_columns_up():
    text = render_table(["code", "name"], [["BLYTHE", "Blythe Farms"], ["A", "B"]])
    lines = text.splitlines()
    assert lines[0].startswith("code  ")
    assert lines[1].startswith("------")
    assert lines[2].startswith("BLYTHE")


def test_a_table_right_aligns_the_columns_it_is_told_to():
    text = render_table(["code", "bales"], [["BLYTHE", "4"], ["A", "1204"]], right=(1,))
    lines = text.splitlines()
    assert lines[2].endswith("   4")
    assert lines[3].endswith("1204")


def test_a_table_with_no_rows_says_so():
    assert render_table(["code"], []) == EMPTY


def test_a_row_that_does_not_match_the_headers_is_refused():
    with pytest.raises(ValueError, match="headers"):
        render_table(["code", "name"], [["BLYTHE"]])


def test_a_header_wider_than_its_column_still_lines_up():
    text = render_table(["producer", "n"], [["A", "1"]])
    assert text.splitlines()[2].startswith("A       ")


def test_pairs_print_as_a_block():
    text = render_pairs([("code", "BLYTHE"), ("acres", "284.50")])
    assert text.splitlines()[0] == "code   BLYTHE"
    assert text.splitlines()[1] == "acres  284.50"


def test_no_pairs_says_so():
    assert render_pairs([]) == EMPTY


def test_nothing_carries_trailing_spaces():
    text = render_table(["code", "name"], [["BLYTHE", "Blythe"]])
    assert all(line == line.rstrip() for line in text.splitlines())
