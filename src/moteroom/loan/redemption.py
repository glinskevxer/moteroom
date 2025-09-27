"""Getting a bale back out of loan.

A bale under loan is redeemed one of two ways. If the world price has come up
past the loan rate, the producer repays the loan with interest and sells. If it
has fallen below, the loan is repaid at the lower rate instead and the
difference stays with the producer as a market gain, and no interest is owed
on a loan repaid that way.

So the two paths are not a discount and a surcharge on the same number. They
are different repayments, and which one applies is decided by the price rather
than by anybody's choice.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from moteroom.core.errors import ValidationError
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.weight import Weight

DAYS_IN_YEAR = 365
CENT = Decimal("0.01")
MAX_ANNUAL_RATE = Decimal("25.00")


def interest_on(principal: Money, annual_rate: Decimal, days: int) -> Money:
    """Simple interest on a principal for a number of days.

    The loan carries simple interest on a 365 day year, which is what the
    lender's own statement works to, so nothing here compounds.
    """
    if days < 0:
        raise ValidationError("days", "must not be negative")
    if annual_rate < 0 or annual_rate > MAX_ANNUAL_RATE:
        raise ValidationError("annual_rate", f"must lie between 0 and {MAX_ANNUAL_RATE}")
    amount = (
        principal.amount * annual_rate / Decimal(100) * Decimal(days) / Decimal(DAYS_IN_YEAR)
    )
    return Money(amount.quantize(CENT, rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Redemption:
    """What it costs to take one bale back out of loan."""

    bale_id: str
    net: Weight
    loan_rate: CentsPerPound
    world_price: CentsPerPound
    days: int
    annual_rate: Decimal

    def __post_init__(self) -> None:
        if self.days < 0:
            raise ValidationError("days", "must not be negative")
        if self.annual_rate < 0 or self.annual_rate > MAX_ANNUAL_RATE:
            raise ValidationError("annual_rate", f"must lie between 0 and {MAX_ANNUAL_RATE}")
        if self.net.is_zero:
            raise ValidationError("net", "a bale has to weigh something")

    @property
    def loan_value(self) -> Money:
        """What the bale was advanced against."""
        return self.loan_rate.on(self.net)

    @property
    def below_loan(self) -> bool:
        """Whether the world price sits under the loan rate."""
        return self.world_price < self.loan_rate

    @property
    def repayment_rate(self) -> CentsPerPound:
        """The rate the loan actually repays at."""
        return self.world_price if self.below_loan else self.loan_rate

    @property
    def repayment(self) -> Money:
        return self.repayment_rate.on(self.net)

    @property
    def market_gain(self) -> Money:
        """What stays with the producer when the price fell."""
        return self.loan_value - self.repayment

    @property
    def interest(self) -> Money:
        """Interest, which is only owed on a loan repaid at the loan rate."""
        if self.below_loan:
            return Money.zero()
        return interest_on(self.loan_value, self.annual_rate, self.days)

    @property
    def due(self) -> Money:
        """What has to be paid to release the bale."""
        return self.repayment + self.interest

    def lines(self) -> list[tuple[str, Money]]:
        return [
            ("loan value", self.loan_value),
            ("repayment", self.repayment),
            ("market gain", self.market_gain),
            ("interest", self.interest),
            ("due", self.due),
        ]

    def __str__(self) -> str:
        path = "at the world price" if self.below_loan else "at the loan rate"
        return f"bale {self.bale_id} redeems {path} for {self.due}"
