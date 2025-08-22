"""What a season is settled against.

The terms are three separate schedules that happen to be posted together: what
the plant charges, what the seed is worth, and what the lint loans at. They sit
in the domain because the arithmetic that uses them does, and because storage
has to be able to load them without knowing a service exists.
"""

from __future__ import annotations

from dataclasses import dataclass

from moteroom.core.money import CentsPerPound
from moteroom.settlement.charges import ChargeSchedule
from moteroom.settlement.seed import SeedTerms


@dataclass(frozen=True)
class Terms:
    """Everything a season is settled against."""

    charges: ChargeSchedule
    seed: SeedTerms
    base_rate: CentsPerPound

    def lines(self) -> list[tuple[str, str]]:
        """The posted terms as they read on the notice board."""
        return [
            ("ginning per cwt", str(self.charges.ginning_per_cwt)),
            ("bagging and ties", str(self.charges.bagging_and_ties)),
            ("module handling", str(self.charges.module_handling)),
            ("drying per cwt", str(self.charges.drying_per_cwt)),
            ("minimum per bale", str(self.charges.minimum_per_bale)),
            ("seed per ton", str(self.seed.price_per_ton)),
            ("seed shares", f"{self.seed.gin_shares}:{self.seed.producer_shares}"),
            ("seed hauling per ton", str(self.seed.hauling_per_ton)),
            ("base loan rate", str(self.base_rate)),
        ]
