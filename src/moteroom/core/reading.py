"""Two things the whole package was doing in six places.

Every instrument reading is checked the same way: it has a range it can report
and a step it reports in, and anything else is a keying error. Every percentage
is taken the same way: a part over a whole, to a hundredth, refusing to divide
by nothing. Both were written out wherever they were needed, and the copies
drifted, which is how a moisture reading came to be checked to a tenth in one
module and to a hundredth in another.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError

TENTH = Decimal("0.1")
HUNDREDTH = Decimal("0.01")


def checked(
    value: Decimal | str,
    field: str,
    low: Decimal,
    high: Decimal,
    step: Decimal = TENTH,
) -> Decimal:
    """One reading, checked against the range and the step it comes in."""
    reading = Decimal(value) if isinstance(value, str) else value
    if not isinstance(reading, Decimal):
        raise ValidationError(field, "must be a Decimal or text")
    if reading != reading.quantize(step):
        raise ValidationError(field, f"{reading} is finer than the instrument reports")
    if not low <= reading <= high:
        raise ValidationError(field, f"{reading} is outside {low} to {high}")
    return reading


def ratio(part: int, whole: int, field: str = "whole") -> Decimal:
    """A part of a whole as a percentage to a hundredth."""
    if whole == 0:
        raise ValidationError(field, "cannot take a percentage of nothing")
    return (Decimal(part) * Decimal(100) / Decimal(whole)).quantize(
        HUNDREDTH, rounding=ROUND_HALF_UP
    )


def share(part: int, whole: int) -> Decimal:
    """The same percentage, except that nothing out of nothing is nothing.

    Reports count things that may not be there yet, and a report that raises
    because the season has not started is a report nobody can run.
    """
    if whole <= 0:
        return Decimal("0.00")
    return ratio(part, whole)
