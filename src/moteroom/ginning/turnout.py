"""Turnout.

Turnout is lint out over seed cotton in, and it is the number the plant is
judged on. It is reported to a hundredth of a percent because a tenth of a
point across a season is real money, and it is always taken off the lot rather
than off a single module.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun

HUNDREDTH = Decimal("0.01")
STATISTICAL_BALE = 480
LOW_TURNOUT = Decimal("30.00")
HIGH_TURNOUT = Decimal("45.00")


def percent(part: Weight, whole: Weight) -> Decimal:
    """A percentage to a hundredth, refusing a division nobody can do."""
    if whole.is_zero:
        raise ValidationError("whole", "cannot take a percentage of nothing")
    ratio = Decimal(part.pounds) * Decimal(100) / Decimal(whole.pounds)
    return ratio.quantize(HUNDREDTH, rounding=ROUND_HALF_UP)


def lint_turnout(run: GinRun) -> Decimal:
    """Lint out over seed cotton in, which is the number that matters."""
    return percent(run.lint, run.seed_cotton)


def seed_turnout(run: GinRun) -> Decimal:
    """Seed out over seed cotton in."""
    return percent(run.seed, run.seed_cotton)


def mote_fraction(run: GinRun) -> Decimal:
    """What the mote room caught, as a share of the lot."""
    return percent(run.motes, run.seed_cotton)


def bale_equivalent(lint: Weight) -> Decimal:
    """Lint stated in statistical bales of 480 pounds."""
    return (Decimal(lint.pounds) / Decimal(STATISTICAL_BALE)).quantize(HUNDREDTH)


def band(turnout: Decimal) -> str:
    """What the plant calls a turnout when it reads it off the board."""
    if turnout < LOW_TURNOUT:
        return "low"
    if turnout > HIGH_TURNOUT:
        return "high"
    return "normal"


@dataclass(frozen=True)
class TurnoutSummary:
    """Everything the daily sheet says about one lot."""

    lot: str
    modules: int
    seed_cotton: Weight
    lint: Weight
    lint_turnout: Decimal
    seed_turnout: Decimal
    mote_fraction: Decimal
    bales: Decimal

    @property
    def band(self) -> str:
        return band(self.lint_turnout)

    @property
    def accounted_percent(self) -> Decimal:
        return self.lint_turnout + self.seed_turnout + self.mote_fraction


def summarise(run: GinRun) -> TurnoutSummary:
    """Read one lot into the line the daily sheet prints."""
    return TurnoutSummary(
        lot=str(run.lot),
        modules=run.module_count,
        seed_cotton=run.seed_cotton,
        lint=run.lint,
        lint_turnout=lint_turnout(run),
        seed_turnout=seed_turnout(run),
        mote_fraction=mote_fraction(run),
        bales=bale_equivalent(run.lint),
    )
