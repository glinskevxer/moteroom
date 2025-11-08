"""Scales and their certificates.

Every weight in the book came off a scale, and a scale is only worth anything
while its certificate is current. Weights are still recorded on a scale whose
certificate has lapsed, because refusing to weigh a truck that is already on
the pad helps nobody, but they are marked, and a settlement built on marked
weights says so.

A certificate is issued for a period and can be revoked inside it, so being
inside the dates is necessary and not sufficient.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from moteroom.core.errors import ConflictError, NotFoundError, ValidationError
from moteroom.core.reading import checked
from moteroom.core.weight import Weight

_SCALE = re.compile(r"^[A-Z]{2}\d{2}$")
MAX_ERROR = Decimal("5.0")
WARNING_DAYS = 30


@dataclass(frozen=True)
class Certificate:
    """One certification of one scale, by whoever tested it."""

    scale: str
    tested_on: date
    expires_on: date
    tester: str
    error: Decimal
    revoked_on: date | None = None

    def __post_init__(self) -> None:
        if not _SCALE.match(self.scale):
            raise ValidationError("scale", f"{self.scale!r} is not a scale")
        if not self.tester.strip():
            raise ValidationError("tester", "is blank")
        if self.expires_on <= self.tested_on:
            raise ValidationError("expires_on", "is not after the test")
        object.__setattr__(
            self, "error", checked(self.error, "error", -MAX_ERROR, MAX_ERROR, Decimal("0.1"))
        )
        if self.revoked_on is not None and self.revoked_on < self.tested_on:
            raise ValidationError("revoked_on", "is before the scale was tested")

    def covers(self, day: date) -> bool:
        """Whether this certificate stands on a day."""
        if self.revoked_on is not None and day >= self.revoked_on:
            return False
        return self.tested_on <= day <= self.expires_on

    def expiring(self, day: date) -> bool:
        """Whether it runs out inside the warning period."""
        return self.covers(day) and day + timedelta(days=WARNING_DAYS) > self.expires_on

    def days_left(self, day: date) -> int:
        return max((self.expires_on - day).days, 0)

    def __str__(self) -> str:
        return f"{self.scale} certified to {self.expires_on.isoformat()} by {self.tester}"


class ScaleBook:
    """Every certificate the plant holds, by scale."""

    def __init__(self) -> None:
        self._certificates: list[Certificate] = []

    def certify(self, certificate: Certificate) -> None:
        """File a certificate, refusing one that overlaps another for the scale."""
        for held in self.for_scale(certificate.scale):
            if held.tested_on <= certificate.expires_on and (
                certificate.tested_on <= held.expires_on
            ):
                raise ConflictError(
                    "scale", certificate.scale, "already has a certificate here"
                )
        self._certificates.append(certificate)

    def extend(self, certificates: Iterable[Certificate]) -> None:
        for certificate in certificates:
            self.certify(certificate)

    def for_scale(self, scale: str) -> list[Certificate]:
        return sorted(
            (one for one in self._certificates if one.scale == scale),
            key=lambda one: one.tested_on,
        )

    def current(self, scale: str, day: date) -> Certificate:
        """The certificate that stands for a scale on a day."""
        for held in self.for_scale(scale):
            if held.covers(day):
                return held
        raise NotFoundError("certificate", f"{scale} on {day.isoformat()}")

    def is_certified(self, scale: str, day: date) -> bool:
        try:
            self.current(scale, day)
        except NotFoundError:
            return False
        return True

    def expiring(self, day: date) -> list[Certificate]:
        """Certificates that run out soon, worst first."""
        found = [one for one in self._certificates if one.expiring(day)]
        return sorted(found, key=lambda one: (one.expires_on, one.scale))

    def scales(self) -> list[str]:
        return sorted({one.scale for one in self._certificates})

    def correction(self, scale: str, day: date, weight: Weight) -> Weight:
        """What a weight would be if the scale's known error were taken out."""
        held = self.current(scale, day)
        adjusted = Decimal(weight.pounds) * (Decimal(100) - held.error) / Decimal(100)
        return Weight(int(adjusted.to_integral_value(rounding="ROUND_HALF_UP")))

    def __len__(self) -> int:
        return len(self._certificates)
