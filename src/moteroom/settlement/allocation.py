"""Splitting a lot back to the producers who brought it.

Once seed cotton is on the feeder floor there is no telling one producer's
cotton from another's, so the lot's lint is divided by what each producer put
in. The basis is dry weight rather than scale weight: a producer whose modules
sat in the rain put less cotton on the floor than the scale ticket says, and
dividing on wet pounds pays them for water.

The division is by largest remainder, so the pounds allocated always add back
to the pounds the lot made. Nobody's pound goes missing in a rounding.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from moteroom.core.errors import ValidationError
from moteroom.core.weight import Weight, total
from moteroom.ginning.run import GinRun
from moteroom.receiving.ticket import ModuleTicket


@dataclass(frozen=True)
class Allocation:
    """What each producer put in and what they get out."""

    lot: str
    basis: dict[str, Weight]
    lint: dict[str, Weight]
    seed: dict[str, Weight]

    @property
    def producers(self) -> list[str]:
        return sorted(self.basis)

    @property
    def total_basis(self) -> Weight:
        return total(list(self.basis.values()))

    @property
    def total_lint(self) -> Weight:
        return total(list(self.lint.values()))

    @property
    def total_seed(self) -> Weight:
        return total(list(self.seed.values()))

    def lint_for(self, producer: str) -> Weight:
        if producer not in self.lint:
            raise ValidationError("producer", f"{producer} put nothing in this lot")
        return self.lint[producer]

    def __str__(self) -> str:
        return f"lot {self.lot} split {len(self.basis)} ways"


def divide(amount: Weight, basis: dict[str, Weight]) -> dict[str, Weight]:
    """Divide a weight on a basis, giving the odd pounds to the largest share."""
    denominator = sum(weight.pounds for weight in basis.values())
    if denominator == 0:
        raise ValidationError("basis", "nothing to divide on")
    out: dict[str, Weight] = {}
    assigned = 0
    for name in sorted(basis):
        pounds = amount.pounds * basis[name].pounds // denominator
        out[name] = Weight(pounds)
        assigned += pounds
    remainder = amount.pounds - assigned
    order = sorted(basis, key=lambda name: (-basis[name].pounds, name))
    index = 0
    while remainder > 0:
        name = order[index % len(order)]
        out[name] = Weight(out[name].pounds + 1)
        remainder -= 1
        index += 1
    return out


def divide_count(count: int, basis: dict[str, Weight]) -> dict[str, int]:
    """Divide a count of bales on the same basis the pounds were divided on."""
    if count < 0:
        raise ValidationError("count", "must not be negative")
    denominator = sum(weight.pounds for weight in basis.values())
    if denominator == 0:
        raise ValidationError("basis", "nothing to divide on")
    out = {name: count * basis[name].pounds // denominator for name in sorted(basis)}
    remainder = count - sum(out.values())
    order = sorted(basis, key=lambda name: (-basis[name].pounds, name))
    index = 0
    while remainder > 0:
        out[order[index % len(order)]] += 1
        remainder -= 1
        index += 1
    return out


def allocate(run: GinRun, tickets: Sequence[ModuleTicket]) -> Allocation:
    """Split a lot's lint and seed between the producers who fed it."""
    numbers = {ticket.number for ticket in tickets}
    if numbers != set(run.tickets):
        raise ValidationError("tickets", f"lot {run.lot} was ginned off other tickets")
    if len(numbers) != len(tickets):
        raise ValidationError("tickets", "names the same ticket twice")
    basis: dict[str, Weight] = {}
    for ticket in tickets:
        dry = ticket.dry_weight()
        basis[ticket.producer] = basis.get(ticket.producer, Weight.zero()) + dry
    return Allocation(
        lot=str(run.lot),
        basis=basis,
        lint=divide(run.lint, basis),
        seed=divide(run.seed, basis),
    )
