"""A bale.

The bale is the unit everything after the press is written against. It leaves
the plant with a tag, a gross weight off the press scale and a tare for the
bagging and ties, and the net of those two is what the warehouse receipts and
what the producer is paid on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, LotId
from moteroom.core.weight import Weight

MIN_NET_POUNDS = 300
MAX_NET_POUNDS = 700
LIGHT_BALE_POUNDS = 425
HEAVY_BALE_POUNDS = 600
MIN_TARE_POUNDS = 4
MAX_TARE_POUNDS = 40
MIN_MOISTURE = Decimal("3.0")
MAX_MOISTURE = Decimal("10.0")
TENTH = Decimal("0.1")


@dataclass(frozen=True)
class Bale:
    """One pressed bale as the tag reads it."""

    bale_id: BaleId
    lot: LotId
    pressed_on: date
    gross: Weight
    tare: Weight
    moisture: Decimal

    def __post_init__(self) -> None:
        if not self.lot.season.contains(self.pressed_on):
            raise ValidationError("pressed_on", f"is outside {self.lot.season}")
        if not self.bale_id.belongs_to(self.lot.season):
            raise ValidationError("bale_id", "does not carry this season's digit")
        if not MIN_TARE_POUNDS <= self.tare.pounds <= MAX_TARE_POUNDS:
            raise ValidationError(
                "tare", f"must lie between {MIN_TARE_POUNDS} and {MAX_TARE_POUNDS} pounds"
            )
        if self.tare >= self.gross:
            raise ValidationError("tare", "must weigh less than the gross")
        net = self.gross - self.tare
        if net.pounds < MIN_NET_POUNDS:
            raise ValidationError("net", f"{net} is too light to be a bale")
        if net.pounds > MAX_NET_POUNDS:
            raise ValidationError("net", f"{net} is too heavy to be a bale")
        if self.moisture != self.moisture.quantize(TENTH):
            raise ValidationError("moisture", "is finer than a tenth")
        if not MIN_MOISTURE <= self.moisture <= MAX_MOISTURE:
            raise ValidationError(
                "moisture", f"{self.moisture} is outside {MIN_MOISTURE}-{MAX_MOISTURE}"
            )

    @property
    def net(self) -> Weight:
        return self.gross - self.tare

    @property
    def number(self) -> int:
        return self.bale_id.bale_number

    @property
    def is_light(self) -> bool:
        """Light bales are handled and stacked differently at the warehouse."""
        return self.net.pounds < LIGHT_BALE_POUNDS

    @property
    def is_heavy(self) -> bool:
        return self.net.pounds > HEAVY_BALE_POUNDS

    def __str__(self) -> str:
        return f"bale {self.bale_id.grouped()} {self.net}"
