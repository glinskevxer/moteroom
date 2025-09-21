"""The module ticket.

A truck pulls onto the scale with a module on it, weighs, dumps, and weighs
again. The difference is seed cotton and the ticket is the only record of it,
so the ticket is written once and never edited. A correction is a second
ticket that voids the first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.ids import ModuleId
from moteroom.core.reading import TENTH, checked
from moteroom.core.season import Season
from moteroom.core.weight import Weight

MIN_MODULE_POUNDS = 1_500
MAX_MODULE_POUNDS = 30_000
MIN_MOISTURE = Decimal("2.0")
MAX_MOISTURE = Decimal("25.0")
REFERENCE_MOISTURE = Decimal("7.5")


def clean_moisture(value: Decimal | str) -> Decimal:
    """Read a moisture reading, which the probe reports to a tenth."""
    return checked(value, "moisture", MIN_MOISTURE, MAX_MOISTURE, TENTH)


@dataclass(frozen=True)
class ModuleTicket:
    """One weighed module, as the scale house wrote it down."""

    number: int
    module: ModuleId
    producer: str
    farm: str
    weighed_on: date
    gross: Weight
    tare: Weight
    moisture: Decimal
    voids: int | None = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.number, int) or isinstance(self.number, bool):
            raise ValidationError("ticket", "must be numbered")
        if self.number < 1:
            raise ValidationError("ticket", "must be numbered from one")
        if not self.producer.strip():
            raise ValidationError("producer", "is blank")
        if not self.farm.strip():
            raise ValidationError("farm", "is blank")
        if self.tare >= self.gross:
            raise ValidationError("tare", "must weigh less than the gross")
        object.__setattr__(self, "moisture", clean_moisture(self.moisture))
        net = self.gross - self.tare
        if net.pounds < MIN_MODULE_POUNDS:
            raise ValidationError("net", f"{net} is too light to be a module")
        if net.pounds > MAX_MODULE_POUNDS:
            raise ValidationError("net", f"{net} is too heavy to be a module")
        if self.voids is not None and self.voids >= self.number:
            raise ValidationError("voids", "must name an earlier ticket")

    @property
    def net(self) -> Weight:
        """Seed cotton on the ticket."""
        return self.gross - self.tare

    @property
    def season(self) -> Season:
        return Season.for_date(self.weighed_on)

    @property
    def is_correction(self) -> bool:
        return self.voids is not None

    def dry_weight(self, reference: Decimal = REFERENCE_MOISTURE) -> Weight:
        """Net weight restated at a reference moisture.

        Two modules off the same field weigh differently when one of them sat
        in the rain, so anything comparing yields has to compare dry weight.
        """
        if not MIN_MOISTURE <= reference <= MAX_MOISTURE:
            raise ValidationError("reference", "is outside the moisture range")
        adjusted = (
            Decimal(self.net.pounds)
            * (Decimal(100) - self.moisture)
            / (Decimal(100) - reference)
        )
        return Weight(int(adjusted.to_integral_value(rounding=ROUND_HALF_UP)))

    def __str__(self) -> str:
        return f"ticket {self.number} module {self.module} {self.net}"
