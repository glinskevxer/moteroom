"""The classing book.

Cards come back in files that do not line up with lots, and some of them are
for bales this gin never pressed because the office keyed a digit wrong. The
book holds what came back and answers the two questions the office manager
actually asks: which bales are still unclassed, and which cards belong to
nobody here.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.ids import BaleId
from moteroom.core.season import Season


@dataclass(frozen=True)
class MatchReport:
    """Where the cards and the press disagree."""

    classed: tuple[BaleId, ...]
    unclassed: tuple[BaleId, ...]
    unknown: tuple[BaleId, ...]

    @property
    def is_complete(self) -> bool:
        return not self.unclassed and not self.unknown

    def __str__(self) -> str:
        return (
            f"{len(self.classed)} classed, "
            f"{len(self.unclassed)} waiting, "
            f"{len(self.unknown)} not ours"
        )


class ClassingBook:
    """Every card back this season, keyed by bale."""

    def __init__(self, season: Season) -> None:
        self.season = season
        self._cards: dict[str, ClassingRecord] = {}

    def add(self, record: ClassingRecord) -> None:
        """File a card, refusing a second one for the same bale."""
        if not record.bale_id.belongs_to(self.season):
            raise ValidationError("bale_id", f"is not tagged for {self.season}")
        if not self.season.contains(record.classed_on):
            raise ValidationError("classed_on", f"is outside {self.season}")
        key = str(record.bale_id)
        held = self._cards.get(key)
        if held is not None:
            if held == record:
                return
            raise ConflictError("card", key, "is already classed differently")
        self._cards[key] = record

    def extend(self, records: Iterable[ClassingRecord]) -> None:
        for record in records:
            self.add(record)

    def replace(self, record: ClassingRecord) -> None:
        """Take a corrected card from the office over the one on file."""
        key = str(record.bale_id)
        if key not in self._cards:
            raise NotFoundError("card", key)
        self._cards[key] = record

    def get(self, bale_id: BaleId) -> ClassingRecord:
        try:
            return self._cards[str(bale_id)]
        except KeyError as exc:
            raise NotFoundError("card", str(bale_id)) from exc

    def has(self, bale_id: BaleId) -> bool:
        return str(bale_id) in self._cards

    def cards(self) -> list[ClassingRecord]:
        return [self._cards[key] for key in sorted(self._cards)]

    def below_grade(self) -> list[ClassingRecord]:
        return [card for card in self.cards() if card.is_below_grade]

    def with_gin_faults(self) -> list[ClassingRecord]:
        return [card for card in self.cards() if card.gin_faults]

    def match(self, pressed: Iterable[BaleId]) -> MatchReport:
        """Line the cards up against what the press says it stamped."""
        pressed_keys = {str(bale) for bale in pressed}
        card_keys = set(self._cards)
        return MatchReport(
            classed=tuple(BaleId(key) for key in sorted(pressed_keys & card_keys)),
            unclassed=tuple(BaleId(key) for key in sorted(pressed_keys - card_keys)),
            unknown=tuple(BaleId(key) for key in sorted(card_keys - pressed_keys)),
        )

    def __len__(self) -> int:
        return len(self._cards)

    def __iter__(self) -> Iterator[ClassingRecord]:
        return iter(self.cards())
