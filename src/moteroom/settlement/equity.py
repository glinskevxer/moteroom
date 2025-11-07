"""Patronage and equity at a co-operative gin.

A co-op gin does not keep its margin. At the end of the season what is left
over is allocated back to the members in proportion to what they ginned, part
of it paid in cash and the rest held as equity in their name. Years later that
equity is revolved out, oldest year first, which is why the ledger has to keep
the year each allocation was made in rather than a single balance.

Two rules that are easy to get wrong and are why this is not just a division.
Allocation is on ginned volume, not on what a member was paid, so a poor crop
still earns patronage. And retirement takes the oldest year first whatever the
member asks for, because a revolving fund that lets members choose is not a
revolving fund.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from moteroom.core.errors import ConflictError, ValidationError
from moteroom.core.money import Money, total_money
from moteroom.core.season import Season
from moteroom.core.weight import Weight, total

MAX_SHARES = 1_000


@dataclass(frozen=True)
class Patronage:
    """One member's share of a season's margin."""

    producer: str
    basis: Weight
    allocated: Money
    cash: Money

    @property
    def retained(self) -> Money:
        """What stays in the co-op as equity in this member's name."""
        return self.allocated - self.cash

    def __str__(self) -> str:
        return f"{self.producer} {self.allocated} allocated, {self.cash} in cash"


@dataclass(frozen=True)
class Allocation:
    """A season's margin split across the members who ginned in it."""

    season: Season
    margin: Money
    shares: tuple[Patronage, ...]

    @property
    def members(self) -> int:
        return len(self.shares)

    @property
    def cash(self) -> Money:
        return total_money([share.cash for share in self.shares])

    @property
    def retained(self) -> Money:
        return total_money([share.retained for share in self.shares])

    def for_producer(self, producer: str) -> Patronage:
        for share in self.shares:
            if share.producer == producer:
                return share
        raise ValidationError("producer", f"{producer} ginned nothing in {self.season}")


def allocate_margin(
    season: Season,
    margin: Money,
    volume: dict[str, Weight],
    cash_shares: int = 1,
    equity_shares: int = 4,
) -> Allocation:
    """Split a season's margin across the members on ginned volume."""
    if margin.amount < 0:
        raise ValidationError("margin", "a loss is not allocated as patronage")
    if not volume:
        raise ValidationError("volume", "nobody ginned anything")
    if cash_shares < 0 or equity_shares < 0:
        raise ValidationError("shares", "must not be negative")
    if cash_shares + equity_shares == 0:
        raise ValidationError("shares", "must not both be zero")
    if cash_shares + equity_shares > MAX_SHARES:
        raise ValidationError("shares", f"must not exceed {MAX_SHARES}")
    ginned = total(list(volume.values()))
    if ginned.is_zero:
        raise ValidationError("volume", "nobody ginned anything")

    names = sorted(volume)
    parts = margin.allocate([volume[name].pounds for name in names])
    shares = []
    for name, part in zip(names, parts, strict=True):
        cash = part.allocate([cash_shares, equity_shares])[0]
        shares.append(Patronage(name, volume[name], part, cash))
    return Allocation(season, margin, tuple(shares))


@dataclass(frozen=True)
class Holding:
    """Equity allocated in one season and still standing."""

    season: Season
    producer: str
    amount: Money


class EquityLedger:
    """Equity by member and by year, and the fund that revolves it out."""

    def __init__(self) -> None:
        self._holdings: dict[tuple[str, int], Money] = {}

    def credit(self, season: Season, producer: str, amount: Money) -> None:
        """Put a season's retained patronage on a member's account."""
        if amount.amount <= 0:
            raise ValidationError("amount", "equity has to be money")
        key = (producer, season.year)
        if key in self._holdings:
            raise ConflictError("equity", producer, f"is already credited for {season}")
        self._holdings[key] = amount

    def credit_all(self, allocation: Allocation) -> None:
        for share in allocation.shares:
            if not share.retained.is_zero:
                self.credit(allocation.season, share.producer, share.retained)

    def holdings(self, producer: str | None = None) -> list[Holding]:
        """Every holding, oldest season first."""
        rows = [
            Holding(Season(year), name, amount)
            for (name, year), amount in self._holdings.items()
            if producer is None or name == producer
        ]
        return sorted(rows, key=lambda held: (held.season.year, held.producer))

    def balance(self, producer: str) -> Money:
        """What the co-op owes a member in equity."""
        return total_money([held.amount for held in self.holdings(producer)])

    def total(self) -> Money:
        return total_money([held.amount for held in self.holdings()])

    def oldest_season(self) -> Season | None:
        held = self.holdings()
        return held[0].season if held else None

    def retire(self, season: Season) -> list[Holding]:
        """Revolve out a year, which has to be the oldest one standing."""
        oldest = self.oldest_season()
        if oldest is None:
            raise ValidationError("season", "there is no equity to retire")
        if season != oldest:
            raise ValidationError("season", f"{oldest} has to be retired first")
        retiring = [held for held in self.holdings() if held.season == season]
        for held in retiring:
            del self._holdings[(held.producer, season.year)]
        return retiring

    def seasons(self) -> list[Season]:
        return sorted({held.season for held in self.holdings()}, key=lambda one: one.year)

    def members(self) -> list[str]:
        return sorted({held.producer for held in self.holdings()})

    def load(self, holdings: Iterable[Holding]) -> None:
        for held in holdings:
            self.credit(held.season, held.producer, held.amount)

    def __len__(self) -> int:
        return len(self._holdings)
