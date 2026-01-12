"""The cheque register.

Settling a producer says what they are owed. The cheque is the thing that pays
it, and the two are not the same event: a settlement written in February is
paid by a cheque that clears in March, or does not clear at all and is voided
and rewritten.

A cheque is never edited. It is issued, and then it either clears or is voided,
and both of those are recorded against the original rather than replacing it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money, total_money

_NUMBER = re.compile(r"^\d{4,8}$")
STALE_DAYS = 180


@dataclass(frozen=True)
class Cheque:
    """One cheque as the register holds it."""

    number: str
    payee: str
    amount: Money
    issued_on: date
    cleared_on: date | None = None
    voided_on: date | None = None
    void_reason: str = ""

    def __post_init__(self) -> None:
        if not _NUMBER.match(self.number):
            raise ValidationError("cheque", f"{self.number!r} is not a cheque number")
        if not self.payee.strip():
            raise ValidationError("payee", "is blank")
        if self.amount.amount <= 0:
            raise ValidationError("amount", "a cheque has to be for money")
        if self.cleared_on is not None and self.cleared_on < self.issued_on:
            raise ValidationError("cleared_on", "is before the cheque was written")
        if self.voided_on is not None and self.voided_on < self.issued_on:
            raise ValidationError("voided_on", "is before the cheque was written")
        if self.cleared_on is not None and self.voided_on is not None:
            raise ValidationError("voided_on", "a cheque that cleared cannot be voided")
        if self.voided_on is not None and not self.void_reason.strip():
            raise ValidationError("void_reason", "a void has to say why")

    @property
    def is_outstanding(self) -> bool:
        """Written, not cleared and not voided, which is what the bank is owed."""
        return self.cleared_on is None and self.voided_on is None

    @property
    def is_voided(self) -> bool:
        return self.voided_on is not None

    def is_stale(self, as_of: date) -> bool:
        """Outstanding long enough that the bank will not take it."""
        return self.is_outstanding and as_of - self.issued_on > timedelta(days=STALE_DAYS)

    def clear(self, on: date) -> Cheque:
        """Mark it cleared, which makes a new record rather than editing."""
        if not self.is_outstanding:
            raise ValidationError("cheque", f"{self.number} is not outstanding")
        return Cheque(self.number, self.payee, self.amount, self.issued_on, cleared_on=on)

    def void(self, on: date, reason: str) -> Cheque:
        """Void it, which needs a reason and cannot be undone."""
        if not self.is_outstanding:
            raise ValidationError("cheque", f"{self.number} is not outstanding")
        return Cheque(
            self.number,
            self.payee,
            self.amount,
            self.issued_on,
            voided_on=on,
            void_reason=reason,
        )

    def __str__(self) -> str:
        if self.is_voided:
            return f"cheque {self.number} to {self.payee} voided, {self.void_reason}"
        state = "outstanding" if self.is_outstanding else "cleared"
        return f"cheque {self.number} to {self.payee} {self.amount} {state}"


class Register:
    """Every cheque written, in number order."""

    def __init__(self) -> None:
        self._cheques: dict[str, Cheque] = {}

    def issue(self, cheque: Cheque) -> None:
        """Write a cheque, refusing a number already used."""
        if cheque.number in self._cheques:
            raise ValidationError("cheque", f"{cheque.number} is already in the register")
        self._cheques[cheque.number] = cheque

    def extend(self, cheques: Iterable[Cheque]) -> None:
        for cheque in cheques:
            self.issue(cheque)

    def get(self, number: str) -> Cheque:
        if number not in self._cheques:
            raise ValidationError("cheque", f"{number} is not in the register")
        return self._cheques[number]

    def clear(self, number: str, on: date) -> Cheque:
        cleared = self.get(number).clear(on)
        self._cheques[number] = cleared
        return cleared

    def void(self, number: str, on: date, reason: str) -> Cheque:
        voided = self.get(number).void(on, reason)
        self._cheques[number] = voided
        return voided

    def cheques(self) -> list[Cheque]:
        return [self._cheques[number] for number in sorted(self._cheques)]

    def outstanding(self) -> list[Cheque]:
        return [one for one in self.cheques() if one.is_outstanding]

    def stale(self, as_of: date) -> list[Cheque]:
        return [one for one in self.cheques() if one.is_stale(as_of)]

    def for_payee(self, payee: str) -> list[Cheque]:
        return [one for one in self.cheques() if one.payee == payee]

    def owed(self) -> Money:
        """What the account still has to cover."""
        return total_money([one.amount for one in self.outstanding()])

    def paid(self) -> Money:
        """What has actually left the account."""
        return total_money([one.amount for one in self.cheques() if one.cleared_on is not None])

    def next_number(self) -> str:
        """The next number to write, which follows the highest used."""
        if not self._cheques:
            return "1001"
        return str(max(int(number) for number in self._cheques) + 1)

    def __len__(self) -> int:
        return len(self._cheques)
