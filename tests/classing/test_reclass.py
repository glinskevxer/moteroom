from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.reclass import BETTER, SAME, WORSE, Answer, Request, render_requests
from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.money import CentsPerPound
from moteroom.core.season import Season

GIN = GinCode("41207")
SEASON = Season(2025)
BALE = BaleId.build(SEASON, GIN, 1_204)
ASKED = date(2025, 11, 3)


def request(**overrides: Any) -> Request:
    fields: dict[str, Any] = {
        "bale_id": BALE,
        "asked_on": ASKED,
        "reason": "producer disputes the leaf",
        "asked_by": "BLYTHE",
    }
    fields.update(overrides)
    return Request(**fields)


def card(**overrides: Any) -> ClassingRecord:
    fields: dict[str, Any] = {
        "bale_id": BALE,
        "classed_on": date(2025, 10, 22),
        "office": "MEMPHIS",
        "micronaire": Micronaire(Decimal("4.0")),
        "staple": Staple(36),
        "strength": Strength(Decimal("28.0")),
        "uniformity": Uniformity(Decimal("81.0")),
        "color": ColorGrade(41),
        "leaf": LeafGrade(4),
        "trash": Trash(Decimal("0.42")),
    }
    fields.update(overrides)
    return ClassingRecord(**fields)


def test_a_request_says_why():
    assert "disputes" in str(request())
    with pytest.raises(ValidationError):
        request(reason="  ")
    with pytest.raises(ValidationError):
        request(reason="x" * 121)


def test_a_request_names_who_asked():
    with pytest.raises(ValidationError):
        request(asked_by=" ")


def test_a_request_line_is_laid_out_for_the_office():
    line = request().line()
    assert line.startswith(str(BALE))
    assert "20251103" in line
    assert line.endswith("producer disputes the leaf")


def test_a_file_wraps_the_requests():
    text = render_requests([request()], "memphis", date(2025, 11, 4))
    lines = text.splitlines()
    assert lines[0].startswith("RCLHDRMEMPHIS")
    assert lines[0].endswith("000001")
    assert lines[-1] == "RCLTRL000001"


def test_a_file_has_to_ask_about_something():
    with pytest.raises(ValidationError):
        render_requests([], "MEMPHIS", ASKED)


def test_a_file_cannot_ask_about_one_bale_twice():
    with pytest.raises(ValidationError):
        render_requests([request(), request()], "MEMPHIS", ASKED)


def test_an_answer_holds_both_cards():
    made = Answer(request(), card(), card(classed_on=date(2025, 11, 10), leaf=LeafGrade(3)))
    assert made.changed
    assert made.leaf_changed
    assert not made.colour_changed
    assert str(made).endswith("came back as 41-3")


def test_an_answer_that_changed_nothing_says_so():
    made = Answer(request(), card(), card(classed_on=date(2025, 11, 10)))
    assert not made.changed
    assert str(made).endswith("came back the same")


def test_an_answer_is_priced_rather_than_guessed():
    made = Answer(request(), card(), card(classed_on=date(2025, 11, 10), leaf=LeafGrade(3)))
    assert made.moved(CentsPerPound.of("52.00"), CentsPerPound.of("52.55")) == BETTER
    assert made.moved(CentsPerPound.of("52.00"), CentsPerPound.of("51.00")) == WORSE
    assert made.moved(CentsPerPound.of("52.00"), CentsPerPound.of("52.00")) == SAME


def test_an_answer_has_to_be_about_the_bale_that_was_asked_about():
    other = card(bale_id=BaleId.build(SEASON, GIN, 1_205))
    with pytest.raises(ValidationError):
        Answer(request(), other, card())
    with pytest.raises(ValidationError):
        Answer(request(), card(), other)


def test_an_answer_cannot_predate_the_card_it_replaces():
    with pytest.raises(ValidationError):
        Answer(request(), card(), card(classed_on=date(2025, 10, 1)))
