import pytest

from moteroom.classing.defect import BELOW_GRADE_LEAF, Extraneous, LeafGrade, Level, Matter
from moteroom.core.errors import ValidationError


def test_a_leaf_grade_names_itself():
    assert LeafGrade(3).name == "leaf 3"
    assert str(LeafGrade(3)) == "3"
    assert LeafGrade.parse(" 3 ") == LeafGrade(3)


def test_below_grade_leaf_is_the_eighth_code():
    assert LeafGrade(BELOW_GRADE_LEAF).is_below_grade
    assert LeafGrade(BELOW_GRADE_LEAF).name == "below grade"
    assert not LeafGrade(7).is_below_grade


@pytest.mark.parametrize("grade", [0, 9, -1])
def test_a_leaf_grade_off_the_standards_is_refused(grade):
    with pytest.raises(ValidationError):
        LeafGrade(grade)


def test_a_leaf_grade_is_not_a_bool():
    with pytest.raises(ValidationError):
        LeafGrade(True)


@pytest.mark.parametrize("text", ["", "x", "3.0"])
def test_a_leaf_grade_refuses_junk(text):
    with pytest.raises(ValidationError):
        LeafGrade.parse(text)


def test_a_lower_leaf_grade_is_the_better_one():
    assert LeafGrade(2).is_better_than(LeafGrade(4))
    assert not LeafGrade(4).is_better_than(LeafGrade(2))


@pytest.mark.parametrize(
    ("text", "matter", "level"),
    [
        ("B1", Matter.BARK, Level.LIGHT),
        ("b2", Matter.BARK, Level.HEAVY),
        ("G1", Matter.GRASS, Level.LIGHT),
        ("S2", Matter.SEED_COAT, Level.HEAVY),
        ("O1", Matter.OIL, Level.LIGHT),
        ("P2", Matter.PLASTIC, Level.HEAVY),
        ("T1", Matter.SPINDLE_TWIST, Level.LIGHT),
    ],
)
def test_an_extraneous_code_reads_back(text, matter, level):
    found = Extraneous.parse(text)
    assert found.matter is matter
    assert found.level is level
    assert found.code == text.upper()


@pytest.mark.parametrize("text", ["", "B", "B12", "Z1", "B3", "BX"])
def test_an_extraneous_code_refuses_junk(text):
    with pytest.raises(ValidationError):
        Extraneous.parse(text)


def test_heavy_reads_as_heavy():
    assert Extraneous.parse("B2").is_heavy
    assert not Extraneous.parse("B1").is_heavy
    assert str(Extraneous.parse("B2")) == "heavy bark"


def test_the_gin_wears_the_ones_it_caused():
    assert Extraneous.parse("P2").matter.is_gin_fault
    assert Extraneous.parse("O1").matter.is_gin_fault
    assert Extraneous.parse("T1").matter.is_gin_fault
    assert not Extraneous.parse("B2").matter.is_gin_fault
    assert not Extraneous.parse("G1").matter.is_gin_fault
