"""Setting the driers.

Seed cotton comes in wetter than the gin stand wants it and the driers take
the difference out. How much heat that takes depends on what came in, and the
ceiling is not a matter of opinion: above the damage line the fibre is cooked,
the classing office sees it, and the bale is discounted for something the
plant did rather than something the field did.

There are two stages and they are not set to the same temperature. The first
takes the bulk of the water out of a wet load and the second trims. Running the
second hotter than the first is how a plant scorches cotton while both stages
are individually inside the ceiling.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.reading import TENTH, checked

MIN_TEMPERATURE = 120
MAX_TEMPERATURE = 350
DAMAGE_LINE = 350
FIRST_STAGE_MARGIN = 20

MIN_MOISTURE = Decimal("2.0")
MAX_MOISTURE = Decimal("25.0")
TARGET_MOISTURE = Decimal("6.5")

# What the first stage is set to for the moisture that came in.
SETTINGS: tuple[tuple[Decimal, Decimal, int], ...] = (
    (Decimal("2.0"), Decimal("7.0"), 140),
    (Decimal("7.1"), Decimal("9.0"), 180),
    (Decimal("9.1"), Decimal("11.0"), 230),
    (Decimal("11.1"), Decimal("13.0"), 280),
    (Decimal("13.1"), Decimal("16.0"), 320),
    (Decimal("16.1"), Decimal("25.0"), 345),
)


def recommended(moisture: Decimal) -> int:
    """What the first stage should be set to for cotton coming in this wet."""
    reading = checked(moisture, "moisture", MIN_MOISTURE, MAX_MOISTURE, TENTH)
    for low, high, temperature in SETTINGS:
        if low <= reading <= high:
            return temperature
    raise ValidationError("moisture", f"{reading} falls in no drier band")


@dataclass(frozen=True)
class Setting:
    """What the two stages are actually set to, against what came in."""

    moisture: Decimal
    first: int
    second: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "moisture",
            checked(self.moisture, "moisture", MIN_MOISTURE, MAX_MOISTURE, TENTH),
        )
        for name, value in (("first", self.first), ("second", self.second)):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValidationError(name, "must be a whole number of degrees")
            if not MIN_TEMPERATURE <= value <= MAX_TEMPERATURE:
                raise ValidationError(
                    name, f"must lie between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}"
                )

    @property
    def recommended_first(self) -> int:
        return recommended(self.moisture)

    @property
    def over_the_damage_line(self) -> bool:
        """Whether either stage is set where it cooks the fibre."""
        return max(self.first, self.second) >= DAMAGE_LINE

    @property
    def second_runs_hotter(self) -> bool:
        """The trim stage should never be the hot one."""
        return self.second > self.first - FIRST_STAGE_MARGIN

    @property
    def under_set(self) -> bool:
        """Set colder than the incoming moisture calls for."""
        return self.first < self.recommended_first - FIRST_STAGE_MARGIN

    @property
    def over_set(self) -> bool:
        return self.first > self.recommended_first + FIRST_STAGE_MARGIN

    def warnings(self) -> tuple[str, ...]:
        """Everything wrong with the way the driers are set, worst first."""
        found = []
        if self.over_the_damage_line:
            found.append("a stage is at the damage line")
        if self.second_runs_hotter:
            found.append("the trim stage is not cooler than the first")
        if self.under_set:
            found.append("colder than this moisture calls for")
        if self.over_set:
            found.append("hotter than this moisture calls for")
        return tuple(found)

    @property
    def is_sound(self) -> bool:
        return not self.warnings()

    def __str__(self) -> str:
        if self.is_sound:
            return f"{self.first} and {self.second} on {self.moisture}% is sound"
        return f"{self.first} and {self.second} on {self.moisture}%: {self.warnings()[0]}"


def settings_for(moisture: Decimal) -> Setting:
    """The setting the plant would use for cotton coming in this wet."""
    first = recommended(moisture)
    return Setting(moisture, first, max(first - 40, MIN_TEMPERATURE))
