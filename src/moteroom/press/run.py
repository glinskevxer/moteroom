"""The press run.

Bale numbers come off one counter for the whole season and the counter never
goes backwards, so the press is the only thing allowed to issue them. A lot is
closed once the last bale is off it, and a closed lot refuses another bale
rather than quietly extending itself.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.ids import MAX_BALE_NUMBER, BaleId, GinCode, LotId
from moteroom.core.season import Season
from moteroom.core.weight import Weight, total
from moteroom.press.bale import Bale


class BalePress:
    """The counter at the press, and the bales it has already stamped."""

    def __init__(self, season: Season, gin: GinCode, first_number: int = 1) -> None:
        if not 1 <= first_number <= MAX_BALE_NUMBER:
            raise ValidationError("first_number", "is off the counter")
        self.season = season
        self.gin = gin
        self._next = first_number
        self._bales: list[Bale] = []
        self._closed: set[str] = set()

    @property
    def next_number(self) -> int:
        return self._next

    def press(
        self,
        lot: LotId,
        pressed_on: date,
        gross: Weight,
        tare: Weight,
        moisture: Decimal,
    ) -> Bale:
        """Stamp the next bale off the press."""
        if lot.season != self.season:
            raise ValidationError("lot", f"{lot} is not in {self.season}")
        if str(lot) in self._closed:
            raise ConflictError("lot", str(lot), "is closed")
        if self._next > MAX_BALE_NUMBER:
            raise ConflictError("press", str(self.season), "has run out of bale numbers")
        bale = Bale(
            bale_id=BaleId.build(self.season, self.gin, self._next),
            lot=lot,
            pressed_on=pressed_on,
            gross=gross,
            tare=tare,
            moisture=moisture,
        )
        self._next += 1
        self._bales.append(bale)
        return bale

    def close(self, lot: LotId) -> None:
        """Say a lot is off the press, so nothing else can be added to it."""
        if not self.for_lot(lot):
            raise NotFoundError("lot", str(lot))
        self._closed.add(str(lot))

    def is_closed(self, lot: LotId) -> bool:
        return str(lot) in self._closed

    def restore(self, bales: Iterable[Bale]) -> None:
        """Load bales already pressed, which is what a restart does."""
        for bale in bales:
            if bale.bale_id.gin_code != self.gin:
                raise ValidationError("bale_id", "was pressed at another gin")
            if any(held.bale_id == bale.bale_id for held in self._bales):
                raise ConflictError("bale", str(bale.bale_id), "is already pressed")
            self._bales.append(bale)
            self._next = max(self._next, bale.number + 1)

    def issued(self) -> list[Bale]:
        return list(self._bales)

    def for_lot(self, lot: LotId) -> list[Bale]:
        return [bale for bale in self._bales if bale.lot == lot]

    def lint(self, lot: LotId | None = None) -> Weight:
        """Net lint pressed, for one lot or for the whole season."""
        bales = self._bales if lot is None else self.for_lot(lot)
        return total([bale.net for bale in bales])

    def find(self, bale_id: BaleId) -> Bale:
        for bale in self._bales:
            if bale.bale_id == bale_id:
                return bale
        raise NotFoundError("bale", str(bale_id))

    def __len__(self) -> int:
        return len(self._bales)
