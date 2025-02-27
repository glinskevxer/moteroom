"""Reading the classing file the office sends.

The file is fixed width and it has not changed shape in twenty years. Each
line is one bale. A header names the office and says how many bales are in the
file, and a trailer repeats the count, so a truncated transfer is caught
rather than half loaded.

    columns  field
    1-12     bale id
    13-20    class date, YYYYMMDD
    21-28    office, left justified
    29-31    micronaire times ten
    32-33    staple in thirty seconds
    34-36    strength times ten
    37-39    uniformity times ten
    40-41    colour code
    42       leaf grade
    43-45    trash times one hundred
    46-53    up to four extraneous codes, two characters each

A line the parser cannot read is not fatal. It is set aside with its line
number so the office can be asked about that bale and the rest of the file
still loads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from moteroom.classing.color import ColorGrade
from moteroom.classing.defect import Extraneous, LeafGrade
from moteroom.classing.measure import Micronaire, Staple, Strength, Trash, Uniformity
from moteroom.classing.record import ClassingRecord
from moteroom.core.errors import MoteroomError, ValidationError
from moteroom.core.ids import BaleId

LINE_WIDTH = 53
HEADER_TAG = "HDR"
TRAILER_TAG = "TRL"


@dataclass(frozen=True)
class Reject:
    """A line that did not read, kept with the reason and where it was."""

    line_number: int
    text: str
    reason: str

    def __str__(self) -> str:
        return f"line {self.line_number}: {self.reason}"


@dataclass(frozen=True)
class ClassingFile:
    """What one transfer from the office contained."""

    office: str
    sent_on: date
    records: tuple[ClassingRecord, ...]
    rejects: tuple[Reject, ...]

    @property
    def declared(self) -> int:
        return len(self.records) + len(self.rejects)

    @property
    def is_clean(self) -> bool:
        return not self.rejects


def _scaled(text: str, places: str) -> Decimal:
    if not text.strip().isdigit():
        raise ValidationError("reading", f"{text!r} is not a reading")
    return (Decimal(text.strip()) / Decimal(places)).quantize(
        Decimal("0.1") if places == "10" else Decimal("0.01")
    )


def _staple(text: str) -> Staple:
    if not text.strip().isdigit():
        raise ValidationError("staple", f"{text!r} is not a staple")
    return Staple(int(text))


def parse_line(line: str) -> ClassingRecord:
    """Read one bale line, raising if any column will not read."""
    if len(line) < LINE_WIDTH:
        raise ValidationError("line", f"is {len(line)} columns, not {LINE_WIDTH}")
    try:
        classed_on = datetime.strptime(line[12:20], "%Y%m%d").date()
    except ValueError as exc:
        raise ValidationError("classed_on", f"{line[12:20]!r} is not a date") from exc
    office = line[20:28].strip()
    findings = []
    for start in range(45, 53, 2):
        code = line[start : start + 2].strip()
        if code:
            findings.append(Extraneous.parse(code))
    return ClassingRecord(
        bale_id=BaleId(line[0:12]),
        classed_on=classed_on,
        office=office,
        micronaire=Micronaire(_scaled(line[28:31], "10")),
        staple=_staple(line[31:33]),
        strength=Strength(_scaled(line[33:36], "10")),
        uniformity=Uniformity(_scaled(line[36:39], "10")),
        color=ColorGrade.parse(line[39:41]),
        leaf=LeafGrade.parse(line[41:42]),
        trash=Trash(_scaled(line[42:45], "100")),
        extraneous=tuple(findings),
    )


def parse_file(text: str) -> ClassingFile:
    """Read a whole transfer, setting bad lines aside rather than failing."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise MoteroomError("the transfer is empty")
    header = lines[0]
    if not header.startswith(HEADER_TAG):
        raise MoteroomError("the transfer has no header")
    office = header[3:11].strip()
    try:
        sent_on = datetime.strptime(header[11:19], "%Y%m%d").date()
        declared = int(header[19:25])
    except ValueError as exc:
        raise MoteroomError("the header will not read") from exc
    if not lines[-1].startswith(TRAILER_TAG):
        raise MoteroomError("the transfer has no trailer")
    if int(lines[-1][3:9]) != declared:
        raise MoteroomError("the header and trailer disagree on the count")

    records: list[ClassingRecord] = []
    rejects: list[Reject] = []
    for offset, line in enumerate(lines[1:-1], start=2):
        try:
            records.append(parse_line(line))
        except (ValidationError, ValueError) as exc:
            rejects.append(Reject(offset, line, str(exc)))
    if len(records) + len(rejects) != declared:
        raise MoteroomError("the file holds a different count than the header claims")
    return ClassingFile(office, sent_on, tuple(records), tuple(rejects))
