"""Reconciling the press against the gin run.

The lot sheet says how much lint the lot made and the press says how many
bales it stamped. Those two numbers come off different scales and they never
agree exactly, so the question is not whether they differ but whether they
differ by more than the plant tolerates.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.reading import ratio
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun

DEFAULT_TOLERANCE = Decimal("1.50")


@dataclass(frozen=True)
class Reconciliation:
    """What the lot sheet and the press each said, and by how much they differ."""

    lot: str
    sheet_lint: Weight
    pressed_lint: Weight
    bales: int
    tolerance: Decimal

    @property
    def difference(self) -> int:
        """Pressed less sheet, in pounds, signed the way the plant reads it."""
        return self.pressed_lint.pounds - self.sheet_lint.pounds

    @property
    def drift(self) -> Decimal:
        """The difference as a percentage of what the lot sheet claimed."""
        return ratio(self.difference, self.sheet_lint.pounds, "sheet_lint")

    @property
    def agrees(self) -> bool:
        return abs(self.drift) <= self.tolerance

    @property
    def average_bale(self) -> Weight:
        if self.bales == 0:
            return Weight.zero()
        return Weight(self.pressed_lint.pounds // self.bales)

    def __str__(self) -> str:
        verdict = "agrees" if self.agrees else "off"
        return f"lot {self.lot} {verdict} by {self.drift}% over {self.bales} bales"


def reconcile(
    run: GinRun,
    pressed_lint: Weight,
    bales: int,
    tolerance: Decimal = DEFAULT_TOLERANCE,
) -> Reconciliation:
    """Compare a lot sheet against what the press actually stamped."""
    if bales < 0:
        raise ValidationError("bales", "must not be negative")
    if tolerance < 0:
        raise ValidationError("tolerance", "must not be negative")
    if bales == 0 and not pressed_lint.is_zero:
        raise ValidationError("bales", "no bales cannot weigh something")
    return Reconciliation(
        lot=str(run.lot),
        sheet_lint=run.lint,
        pressed_lint=pressed_lint,
        bales=bales,
        tolerance=tolerance,
    )
