"""The identifiers a gin prints on things.

The bale id is the one that matters. It is stamped on the bale tag at the press
and every later record keys off it, so it carries its own check digit and is
never accepted unchecked. The layout is twelve characters:

    S GGGGG NNNNN C
    |  |     |    check digit
    |  |     bale number inside the season, 1 through 99999
    |  gin code assigned to the plant
    last digit of the crop year

The check digit is a weighted sum of the first eleven digits, weights running
7, 3, 1 from the left, taken mod ten and subtracted from ten.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Self

from moteroom.core.errors import ValidationError
from moteroom.core.season import Season

GIN_CODE_DIGITS = 5
BALE_NUMBER_DIGITS = 5
BALE_ID_LENGTH = 12
MAX_BALE_NUMBER = 99_999
CHECK_WEIGHTS = (7, 3, 1)

_MODULE_ID = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,15}$")


def check_digit(digits: str) -> int:
    """The trailing digit of a bale id, computed off the eleven in front of it."""
    if not digits.isdigit():
        raise ValidationError("bale_id", "carries something that is not a digit")
    running = 0
    for position, character in enumerate(digits):
        running += int(character) * CHECK_WEIGHTS[position % len(CHECK_WEIGHTS)]
    return (10 - running % 10) % 10


@dataclass(frozen=True, order=True)
class GinCode:
    """The five digit code the plant gins under."""

    code: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str):
            raise ValidationError("gin_code", "must be text")
        if len(self.code) != GIN_CODE_DIGITS or not self.code.isdigit():
            raise ValidationError("gin_code", f"must be {GIN_CODE_DIGITS} digits")

    @classmethod
    def parse(cls, text: str) -> Self:
        return cls(text.strip())

    def __str__(self) -> str:
        return self.code


@dataclass(frozen=True, order=True)
class BaleId:
    """A twelve character bale id with its check digit already verified."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise ValidationError("bale_id", "must be text")
        if len(self.value) != BALE_ID_LENGTH or not self.value.isdigit():
            raise ValidationError("bale_id", f"must be {BALE_ID_LENGTH} digits")
        if int(self.value[-1]) != check_digit(self.value[:-1]):
            raise ValidationError("bale_id", f"{self.value} fails its check digit")
        if self.bale_number == 0:
            raise ValidationError("bale_id", "bale number must not be zero")

    @classmethod
    def build(cls, season: Season, gin: GinCode, number: int) -> Self:
        """Make the id the press would print for this bale."""
        if not isinstance(number, int) or isinstance(number, bool):
            raise ValidationError("bale_number", "must be a whole number")
        if not 1 <= number <= MAX_BALE_NUMBER:
            raise ValidationError("bale_number", f"must lie between 1 and {MAX_BALE_NUMBER}")
        body = f"{season.digit}{gin.code}{number:0{BALE_NUMBER_DIGITS}d}"
        return cls(f"{body}{check_digit(body)}")

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read a bale id off a tag, which is often written in groups."""
        cleaned = text.strip().replace(" ", "").replace("-", "")
        return cls(cleaned)

    @property
    def season_digit(self) -> int:
        return int(self.value[0])

    @property
    def gin_code(self) -> GinCode:
        return GinCode(self.value[1 : 1 + GIN_CODE_DIGITS])

    @property
    def bale_number(self) -> int:
        start = 1 + GIN_CODE_DIGITS
        return int(self.value[start : start + BALE_NUMBER_DIGITS])

    def belongs_to(self, season: Season) -> bool:
        """A tag only carries one digit of the year, so this is not proof."""
        return season.digit == self.season_digit

    def grouped(self) -> str:
        """How the id reads on the tag itself."""
        return f"{self.value[0]}-{self.value[1:6]}-{self.value[6:11]}-{self.value[11]}"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class ModuleId:
    """What the module tag says, normalised to upper case."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise ValidationError("module_id", "must be text")
        if not _MODULE_ID.match(self.value):
            raise ValidationError("module_id", f"{self.value!r} is not a module tag")

    @classmethod
    def parse(cls, text: str) -> Self:
        return cls(text.strip().upper())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True)
class LotId:
    """A gin lot, which is a season and a running number inside it."""

    season: Season
    number: int

    def __post_init__(self) -> None:
        if not isinstance(self.number, int) or isinstance(self.number, bool):
            raise ValidationError("lot", "must be a whole number")
        if not 1 <= self.number <= 9_999:
            raise ValidationError("lot", "must lie between 1 and 9999")

    @classmethod
    def parse(cls, text: str) -> Self:
        cleaned = text.strip()
        if "-" not in cleaned:
            raise ValidationError("lot", f"{text!r} is not a lot number")
        head, _, tail = cleaned.partition("-")
        if not tail.isdigit():
            raise ValidationError("lot", f"{text!r} is not a lot number")
        return cls(Season.parse(head), int(tail))

    def __str__(self) -> str:
        return f"{self.season.year}-{self.number:04d}"
