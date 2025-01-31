"""Who the cotton belongs to.

A gin does not deal with one owner per module. The grower has a landlord, the
landlord may have two heirs, and the shares are written on the lease long
before any cotton is picked. Everything downstream splits on the same object,
so it lives here next to the ticket rather than in the settlement code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.core.weight import Weight

_CODE = re.compile(r"^[A-Z][A-Z0-9]{1,11}$")
_FARM = re.compile(r"^\d{1,6}$")
_TRACT = re.compile(r"^\d{1,6}$")
MAX_ACRES = Decimal("50000.00")


@dataclass(frozen=True, order=True)
class Producer:
    """A grower the gin writes cheques to."""

    code: str
    name: str

    def __post_init__(self) -> None:
        if not _CODE.match(self.code):
            raise ValidationError("producer", f"{self.code!r} is not a producer code")
        if not self.name.strip():
            raise ValidationError("name", "is blank")

    @classmethod
    def parse(cls, code: str, name: str) -> Self:
        return cls(code.strip().upper(), name.strip())

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


@dataclass(frozen=True, order=True)
class Farm:
    """An FSA farm and tract, which is how acreage is reported."""

    number: str
    tract: str
    producer: str
    acres: Decimal

    def __post_init__(self) -> None:
        if not _FARM.match(self.number):
            raise ValidationError("farm", f"{self.number!r} is not a farm number")
        if not _TRACT.match(self.tract):
            raise ValidationError("tract", f"{self.tract!r} is not a tract number")
        if not _CODE.match(self.producer):
            raise ValidationError("producer", f"{self.producer!r} is not a producer code")
        if self.acres != self.acres.quantize(Decimal("0.01")):
            raise ValidationError("acres", "is finer than a hundredth")
        if not Decimal(0) < self.acres <= MAX_ACRES:
            raise ValidationError("acres", f"must lie between 0 and {MAX_ACRES}")

    @property
    def key(self) -> str:
        return f"{self.number}-{self.tract}"

    def __str__(self) -> str:
        return f"farm {self.number} tract {self.tract}"


@dataclass(frozen=True)
class ShareSplit:
    """How a farm's cotton divides, in whole shares rather than percentages.

    Leases are written as quarters and thirds, so shares are integers and the
    division happens once at the end. Nobody stores 0.3333 anywhere.
    """

    shares: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if not self.shares:
            raise ValidationError("shares", "is empty")
        seen: set[str] = set()
        for code, share in self.shares:
            if not _CODE.match(code):
                raise ValidationError("shares", f"{code!r} is not a producer code")
            if code in seen:
                raise ValidationError("shares", f"{code} appears twice")
            seen.add(code)
            if not isinstance(share, int) or isinstance(share, bool):
                raise ValidationError("shares", "must be whole shares")
            if share < 0:
                raise ValidationError("shares", "must not be negative")
        if sum(share for _, share in self.shares) == 0:
            raise ValidationError("shares", "must not all be zero")

    @classmethod
    def whole(cls, code: str) -> Self:
        """The common case, where one grower owns all of it."""
        return cls(((code, 1),))

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read a lease line such as ``BLYTHE:3,MERRITT:1``."""
        entries: list[tuple[str, int]] = []
        for part in text.split(","):
            code, sep, share = part.strip().partition(":")
            if not sep or not share.strip().isdigit():
                raise ValidationError("shares", f"{part.strip()!r} is not a share")
            entries.append((code.strip().upper(), int(share)))
        return cls(tuple(entries))

    @property
    def total_shares(self) -> int:
        return sum(share for _, share in self.shares)

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(code for code, _ in self.shares)

    def share_of(self, code: str) -> int:
        for owner, share in self.shares:
            if owner == code:
                return share
        raise ValidationError("shares", f"{code} holds no share here")

    def split_weight(self, weight: Weight) -> dict[str, Weight]:
        """Split lint between owners, giving the odd pound to the largest share."""
        out: dict[str, Weight] = {}
        assigned = 0
        for code, share in self.shares:
            pounds = weight.pounds * share // self.total_shares
            out[code] = Weight(pounds)
            assigned += pounds
        remainder = weight.pounds - assigned
        if remainder:
            biggest = max(self.shares, key=lambda entry: (entry[1], entry[0]))[0]
            out[biggest] = Weight(out[biggest].pounds + remainder)
        return out

    def split_money(self, amount: Money) -> dict[str, Money]:
        """Split money on the same shares, keeping every penny."""
        parts = amount.allocate([share for _, share in self.shares])
        return dict(zip(self.codes, parts, strict=True))

    def __str__(self) -> str:
        return ",".join(f"{code}:{share}" for code, share in self.shares)
