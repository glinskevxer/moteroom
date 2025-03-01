from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.classing.book import ClassingBook
from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season

GIN = GinCode("41207")
SEASON = Season(2025)


def bale(number: int) -> BaleId:
    return BaleId.build(SEASON, GIN, number)


def card(number: int = 1_204, **overrides: Any) -> ClassingRecord:
    fields: dict[str, Any] = {
        "bale_id": bale(number),
        "classed_on": date(2025, 10, 22),
        "office": "MEMPHIS",
        "micronaire": Micronaire(Decimal("4.3")),
        "staple": Staple(36),
        "strength": Strength(Decimal("29.4")),
        "uniformity": Uniformity(Decimal("81.2")),
        "color": ColorGrade(31),
        "leaf": LeafGrade(3),
        "trash": Trash(Decimal("0.42")),
    }
    fields.update(overrides)
    return ClassingRecord(**fields)


def book(*cards: ClassingRecord) -> ClassingBook:
    made = ClassingBook(SEASON)
    made.extend(cards)
    return made


def test_a_card_files_and_reads_back():
    held = book(card())
    assert held.get(bale(1_204)).office == "MEMPHIS"
    assert held.has(bale(1_204))
    assert len(held) == 1


def test_a_card_nobody_filed():
    with pytest.raises(NotFoundError):
        book().get(bale(9))


def test_the_same_card_twice_is_not_a_conflict():
    held = book(card())
    held.add(card())
    assert len(held) == 1


def test_a_different_card_for_the_same_bale_is_a_conflict():
    held = book(card())
    with pytest.raises(ConflictError):
        held.add(card(leaf=LeafGrade(5)))


def test_a_corrected_card_replaces_the_one_on_file():
    held = book(card())
    held.replace(card(leaf=LeafGrade(5)))
    assert str(held.get(bale(1_204)).leaf) == "5"


def test_a_correction_for_a_bale_nobody_classed():
    with pytest.raises(NotFoundError):
        book().replace(card())


def test_a_card_from_another_season_is_refused():
    with pytest.raises(ValidationError):
        book().add(card(bale_id=BaleId.build(Season(2026), GIN, 1_204)))


def test_a_card_classed_outside_the_season_is_refused():
    with pytest.raises(ValidationError):
        book().add(card(classed_on=date(2026, 9, 1)))


def test_the_book_lists_in_bale_order():
    held = book(card(1_205), card(1_204))
    assert [c.bale_id.bale_number for c in held] == [1_204, 1_205]


def test_below_grade_and_gin_faults_are_picked_out():
    held = book(
        card(1_204, leaf=LeafGrade(8)),
        card(1_205, extraneous=(Extraneous.parse("P2"),)),
        card(1_206),
    )
    assert [c.bale_id.bale_number for c in held.below_grade()] == [1_204]
    assert [c.bale_id.bale_number for c in held.with_gin_faults()] == [1_205]


def test_matching_against_the_press_finds_both_gaps():
    held = book(card(1_204), card(9_999))
    report = held.match([bale(1_204), bale(1_205)])
    assert [b.bale_number for b in report.classed] == [1_204]
    assert [b.bale_number for b in report.unclassed] == [1_205]
    assert [b.bale_number for b in report.unknown] == [9_999]
    assert not report.is_complete
    assert str(report) == "1 classed, 1 waiting, 1 not ours"


def test_a_complete_match_says_so():
    held = book(card(1_204))
    assert held.match([bale(1_204)]).is_complete
