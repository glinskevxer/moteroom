"""The crop year, which is not the calendar year.

A gin's books close on a crop year running 1 August through 31 July. Cotton
picked in October 2025 belongs to the 2025 crop and so does a bale that leaves
the warehouse in June 2026. Everything the package stores carries a season, and
the season is derived from the date the seed cotton was weighed in, never from
the date a report is run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Self

from moteroom.core.errors import ValidationError

SEASON_START_MONTH = 8
SEASON_START_DAY = 1
EARLIEST_SEASON = 1980
LATEST_SEASON = 2099

_SHORT = re.compile(r"^(\d{4})$")
_SLASHED = re.compile(r"^(\d{4})[/-](\d{2}|\d{4})$")


@dataclass(frozen=True, order=True)
class Season:
    """One crop year, named for the calendar year it opens in."""

    year: int

    def __post_init__(self) -> None:
        if not isinstance(self.year, int) or isinstance(self.year, bool):
            raise ValidationError("season", "must be a four digit year")
        if not EARLIEST_SEASON <= self.year <= LATEST_SEASON:
            raise ValidationError(
                "season", f"must lie between {EARLIEST_SEASON} and {LATEST_SEASON}"
            )

    @classmethod
    def for_date(cls, day: date) -> Self:
        """Which crop year a date falls in."""
        if (day.month, day.day) >= (SEASON_START_MONTH, SEASON_START_DAY):
            return cls(day.year)
        return cls(day.year - 1)

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read a season off a form, which may be written either way round."""
        cleaned = text.strip()
        short = _SHORT.match(cleaned)
        if short:
            return cls(int(short.group(1)))
        slashed = _SLASHED.match(cleaned)
        if slashed:
            opening = int(slashed.group(1))
            closing = slashed.group(2)
            expected = (opening + 1) % 100 if len(closing) == 2 else opening + 1
            if int(closing) != expected:
                raise ValidationError("season", f"{text!r} does not name consecutive years")
            return cls(opening)
        raise ValidationError("season", f"{text!r} is not a season")

    @property
    def start(self) -> date:
        return date(self.year, SEASON_START_MONTH, SEASON_START_DAY)

    @property
    def end(self) -> date:
        return date(self.year + 1, SEASON_START_MONTH, SEASON_START_DAY) - timedelta(days=1)

    @property
    def label(self) -> str:
        return f"{self.year}/{(self.year + 1) % 100:02d}"

    @property
    def digit(self) -> int:
        """The last digit of the opening year, which is what a bale tag carries."""
        return self.year % 10

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def next(self) -> Season:
        return Season(self.year + 1)

    def previous(self) -> Season:
        return Season(self.year - 1)

    def __str__(self) -> str:
        return self.label
