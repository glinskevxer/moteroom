from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.reporting.report import Report


def report(**overrides: Any) -> Report:
    fields: dict[str, Any] = {
        "title": "gin sheet",
        "headers": ("lot", "lint"),
        "rows": (("2025-0001", "14900"), ("2025-0002", "15100")),
        "right": (1,),
    }
    fields.update(overrides)
    return Report(**fields)


def test_a_report_carries_its_shape():
    assert report().width == 2
    assert not report().is_empty
    assert report(rows=()).is_empty


def test_a_report_needs_a_title_and_columns():
    with pytest.raises(ValidationError):
        report(title="  ")
    with pytest.raises(ValidationError):
        report(headers=())


def test_a_row_that_does_not_match_the_columns_is_refused():
    with pytest.raises(ValidationError):
        report(rows=(("2025-0001",),))


def test_a_right_aligned_column_has_to_exist():
    with pytest.raises(ValidationError):
        report(right=(5,))


def test_a_column_can_be_pulled_out_by_name():
    assert report().column("lint") == ["14900", "15100"]


def test_a_column_nobody_has():
    with pytest.raises(ValidationError):
        report().column("turnout")


def test_a_report_writes_itself_as_csv():
    assert report().to_csv().splitlines()[0] == "lot,lint"
    assert report().to_csv().splitlines()[1] == "2025-0001,14900"


def test_csv_quotes_a_cell_with_a_comma_in_it():
    made = report(rows=(("Blythe, Farms", "1"),))
    assert made.to_csv().splitlines()[1] == '"Blythe, Farms",1'


def test_csv_doubles_a_quote_inside_a_cell():
    made = report(rows=(('the "big" farm', "1"),))
    assert made.to_csv().splitlines()[1] == '"the ""big"" farm",1'
