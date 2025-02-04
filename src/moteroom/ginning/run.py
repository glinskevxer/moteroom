"""A gin run, which the plant calls a lot.

A lot is a set of modules ginned back to back without changing the settings.
Everything weighed on the way out belongs to the lot rather than to a module,
because once seed cotton is on the feeder floor there is no telling two
producers' cotton apart. That is why the split happens on weights and shares
later rather than on bales here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from moteroom.core.errors import ValidationError
from moteroom.core.ids import LotId
from moteroom.core.weight import Weight

MAX_LOSS_FRACTION = 4  # a lot may not lose more than a quarter of what went in


@dataclass(frozen=True)
class GinRun:
    """One lot: what went in, what came out and what the mote room caught."""

    lot: LotId
    ginned_on: date
    tickets: tuple[int, ...]
    seed_cotton: Weight
    lint: Weight
    seed: Weight
    motes: Weight

    def __post_init__(self) -> None:
        if not self.tickets:
            raise ValidationError("tickets", "a lot has to gin something")
        if len(set(self.tickets)) != len(self.tickets):
            raise ValidationError("tickets", "names the same ticket twice")
        if any(number < 1 for number in self.tickets):
            raise ValidationError("tickets", "carries a ticket that is not numbered")
        if not self.lot.season.contains(self.ginned_on):
            raise ValidationError("ginned_on", f"is outside {self.lot.season}")
        if self.seed_cotton.is_zero:
            raise ValidationError("seed_cotton", "a lot has to weigh something")
        if self.lint.is_zero:
            raise ValidationError("lint", "a lot has to make lint")
        accounted = self.lint + self.seed + self.motes
        if accounted.pounds > self.seed_cotton.pounds:
            raise ValidationError(
                "seed_cotton", "less went in than came out, so a scale is wrong"
            )
        if accounted.pounds * MAX_LOSS_FRACTION < self.seed_cotton.pounds * (
            MAX_LOSS_FRACTION - 1
        ):
            raise ValidationError("seed_cotton", "a quarter of the lot is unaccounted for")

    @property
    def module_count(self) -> int:
        return len(self.tickets)

    @property
    def accounted(self) -> Weight:
        """Everything the outbound scales saw."""
        return self.lint + self.seed + self.motes

    @property
    def unaccounted(self) -> Weight:
        """Moisture driven off, dust and whatever the yard blew away."""
        return self.seed_cotton - self.accounted

    def covers(self, ticket: int) -> bool:
        return ticket in self.tickets

    def __str__(self) -> str:
        return f"lot {self.lot} {self.module_count} modules {self.lint} lint"
