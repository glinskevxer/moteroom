"""The classing record.

One card per bale, back from the classing office some days after the bale was
pressed. The gin does not get to edit it. What the gin does is check that the
card is for a bale it actually pressed, that it is complete, and that the
office did not send the same bale twice with different numbers on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId

MAX_EXTRANEOUS = 4


@dataclass(frozen=True)
class ClassingRecord:
    """What the office said about one bale."""

    bale_id: BaleId
    classed_on: date
    office: str
    micronaire: Micronaire
    staple: Staple
    strength: Strength
    uniformity: Uniformity
    color: ColorGrade
    leaf: LeafGrade
    trash: Trash
    extraneous: tuple[Extraneous, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.office.strip():
            raise ValidationError("office", "is blank")
        if len(self.extraneous) > MAX_EXTRANEOUS:
            raise ValidationError("extraneous", f"more than {MAX_EXTRANEOUS} findings")
        seen = [finding.matter for finding in self.extraneous]
        if len(set(seen)) != len(seen):
            raise ValidationError("extraneous", "names the same matter twice")

    @property
    def is_below_grade(self) -> bool:
        """A bale the loan will not take, whichever grade put it there."""
        return self.leaf.is_below_grade

    @property
    def has_bark(self) -> bool:
        return any(finding.code.startswith("B") for finding in self.extraneous)

    @property
    def gin_faults(self) -> tuple[Extraneous, ...]:
        """Findings the plant caused rather than the field."""
        return tuple(f for f in self.extraneous if f.matter.is_gin_fault)

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(finding.code for finding in self.extraneous)

    def card(self) -> str:
        """The one line summary the office fax used to print."""
        tail = " " + " ".join(self.codes) if self.codes else ""
        return (
            f"{self.bale_id} {self.color}-{self.leaf} "
            f"{self.staple} {self.micronaire} {self.strength} {self.uniformity}{tail}"
        )

    def __str__(self) -> str:
        return self.card()
