"""Getting the modules to the gin.

Module trucks are hired by the load and paid two ways at once: a rate per
module and a rate per mile, with a floor under the whole load so a short run
still covers the driver's day. Which of the three actually decides the bill
changes from load to load, so all three are kept and the charge says which one
bound.

The charge is against the producer whose modules were on the truck. A load
carrying two producers' modules splits on the count, not on the mileage,
because the truck drove the same miles either way.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money, total_money

CENT = Decimal("0.01")
MAX_MILES = 500


@dataclass(frozen=True)
class Rate:
    """What one hauler charges."""

    hauler: str
    per_module: Money
    per_mile: Money
    minimum: Money = Money.zero()

    def __post_init__(self) -> None:
        if not self.hauler.strip():
            raise ValidationError("hauler", "is blank")
        for name, amount in (
            ("per_module", self.per_module),
            ("per_mile", self.per_mile),
            ("minimum", self.minimum),
        ):
            if amount.amount < 0:
                raise ValidationError(name, "must not be negative")

    def __str__(self) -> str:
        return f"{self.hauler} {self.per_module} a module and {self.per_mile} a mile"


@dataclass(frozen=True)
class Charge:
    """What a load came to, and which of the three rates decided it."""

    modules: Money
    miles: Money
    minimum: Money
    bound_by: str

    @property
    def total(self) -> Money:
        return max(self.modules + self.miles, self.minimum)

    def __str__(self) -> str:
        return f"{self.total} on the {self.bound_by}"


@dataclass(frozen=True)
class Haul:
    """One truckload of modules."""

    hauler: str
    hauled_on: date
    tickets: tuple[int, ...]
    miles: int

    def __post_init__(self) -> None:
        if not self.hauler.strip():
            raise ValidationError("hauler", "is blank")
        if not self.tickets:
            raise ValidationError("tickets", "a load has to carry something")
        if len(set(self.tickets)) != len(self.tickets):
            raise ValidationError("tickets", "carries the same module twice")
        if not 0 < self.miles <= MAX_MILES:
            raise ValidationError("miles", f"must lie between 1 and {MAX_MILES}")

    @property
    def modules(self) -> int:
        return len(self.tickets)

    def charge(self, rate: Rate) -> Charge:
        """Price the load, saying which rate bound."""
        if rate.hauler != self.hauler:
            raise ValidationError("hauler", f"{rate.hauler} did not haul this load")
        by_module = rate.per_module.times(self.modules)
        by_mile = Money(
            (rate.per_mile.amount * Decimal(self.miles)).quantize(CENT, rounding=ROUND_HALF_UP)
        )
        running = by_module + by_mile
        if rate.minimum > running:
            bound = "minimum"
        elif by_mile > by_module:
            bound = "mileage"
        else:
            bound = "modules"
        return Charge(by_module, by_mile, rate.minimum, bound)

    def __str__(self) -> str:
        return f"{self.hauler} {self.modules} modules {self.miles} miles"


class FreightLedger:
    """Every load hauled in this season."""

    def __init__(self, rates: Iterable[Rate] = ()) -> None:
        self._rates = {rate.hauler: rate for rate in rates}
        self._hauls: list[Haul] = []

    def post(self, rate: Rate) -> None:
        """Post a hauler's rates, which cannot be posted twice."""
        if rate.hauler in self._rates:
            raise ValidationError("hauler", f"{rate.hauler} already has rates posted")
        self._rates[rate.hauler] = rate

    def haul(self, load: Haul) -> Charge:
        """Record a load and price it."""
        if load.hauler not in self._rates:
            raise ValidationError("hauler", f"{load.hauler} has no rates posted")
        self._hauls.append(load)
        return load.charge(self._rates[load.hauler])

    def hauls(self, hauler: str | None = None) -> list[Haul]:
        rows = [one for one in self._hauls if hauler is None or one.hauler == hauler]
        return sorted(rows, key=lambda one: (one.hauled_on, one.hauler))

    def owed(self, hauler: str | None = None) -> Money:
        """What the haulers are owed."""
        return total_money(
            [one.charge(self._rates[one.hauler]).total for one in self.hauls(hauler)]
        )

    def haulers(self) -> list[str]:
        return sorted(self._rates)

    def per_ticket(self) -> dict[int, Money]:
        """The freight against each module, which is how it reaches a producer."""
        out: dict[int, Money] = {}
        for load in self._hauls:
            charge = load.charge(self._rates[load.hauler])
            parts = charge.total.allocate([1] * load.modules)
            for ticket, part in zip(load.tickets, parts, strict=True):
                out[ticket] = out.get(ticket, Money.zero()) + part
        return out

    def for_tickets(self, tickets: Sequence[int]) -> Money:
        """The freight on a set of modules, which a settlement asks for."""
        charged = self.per_ticket()
        return total_money([charged.get(ticket, Money.zero()) for ticket in tickets])

    def __len__(self) -> int:
        return len(self._hauls)
