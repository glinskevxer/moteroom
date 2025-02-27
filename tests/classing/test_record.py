from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season

GIN = GinCode("41207")
BALE = BaleId.build(Season(2025), GIN, 1_204)


def record(**overrides: Any) -> ClassingRecord:
    fields: dict[str, Any] = {
        "bale_id": BALE,
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


def test_a_card_reads_the_way_the_office_prints_it():
    assert record().card() == f"{BALE} 31-3 36 4.3 29.4 81.2"


def test_a_card_carries_its_extraneous_codes():
    carded = record(extraneous=(Extraneous.parse("B2"), Extraneous.parse("G1")))
    assert carded.codes == ("B2", "G1")
    assert carded.card().endswith("B2 G1")
    assert str(carded) == carded.card()


def test_the_office_has_to_be_named():
    with pytest.raises(ValidationError):
        record(office="   ")


def test_a_below_grade_bale_says_so():
    assert record(leaf=LeafGrade(8)).is_below_grade
    assert not record().is_below_grade


def test_bark_is_picked_out_because_the_warehouse_asks():
    assert record(extraneous=(Extraneous.parse("B1"),)).has_bark
    assert not record(extraneous=(Extraneous.parse("G1"),)).has_bark
    assert not record().has_bark


def test_the_gin_faults_are_separated_from_the_field_ones():
    carded = record(extraneous=(Extraneous.parse("B2"), Extraneous.parse("P1")))
    assert [f.code for f in carded.gin_faults] == ["P1"]


def test_the_same_matter_cannot_be_called_twice():
    with pytest.raises(ValidationError):
        record(extraneous=(Extraneous.parse("B1"), Extraneous.parse("B2")))


def test_a_card_cannot_carry_a_pile_of_findings():
    findings = tuple(Extraneous.parse(code) for code in ("B1", "G1", "S1", "O1", "P1"))
    with pytest.raises(ValidationError):
        record(extraneous=findings)


def test_a_card_with_no_findings_prints_no_tail():
    assert not record().card().endswith(" ")
    assert record().codes == ()
