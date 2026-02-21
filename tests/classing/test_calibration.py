from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest

from moteroom.classing.calibration import (
    MEASURES,
    CalibrationLog,
    Check,
    Standard,
)
from moteroom.core.errors import ValidationError

DAY = date(2025, 10, 14)
ASSIGNED = {
    "micronaire": Decimal("4.3"),
    "strength": Decimal("29.4"),
    "uniformity": Decimal("81.2"),
    "length": Decimal("1.1"),
}


def standard(**overrides: Any) -> Standard:
    values = dict(ASSIGNED)
    values.update(overrides)
    return Standard("SC-114", values)


def check(day: date = DAY, **readings: Decimal) -> Check:
    values = dict(ASSIGNED)
    values.update(readings)
    return Check(standard(), day, values, "TALLEY")


def test_a_standard_carries_every_measure():
    assert str(standard()) == "standard SC-114"
    with pytest.raises(ValidationError):
        Standard("SC-114", {"micronaire": Decimal("4.3")})
    with pytest.raises(ValidationError):
        Standard(" ", dict(ASSIGNED))


def test_a_standard_refuses_a_measure_nobody_checks():
    with pytest.raises(ValidationError):
        Standard("SC-114", {**ASSIGNED, "colour": Decimal("1.0")})


def test_a_standard_value_has_to_be_readable():
    with pytest.raises(ValidationError):
        standard(micronaire=Decimal("9.9"))


def test_a_check_names_an_operator_and_every_measure():
    with pytest.raises(ValidationError):
        Check(standard(), DAY, dict(ASSIGNED), "  ")
    with pytest.raises(ValidationError):
        Check(standard(), DAY, {"micronaire": Decimal("4.3")}, "TALLEY")


def test_a_check_on_the_assigned_values_passes():
    made = check()
    assert made.passed
    assert made.failures == ()
    assert str(made).endswith("passed")
    for measure in MEASURES:
        assert made.deviation(measure) == Decimal("0.0")


def test_a_reading_inside_tolerance_still_passes():
    assert check(micronaire=Decimal("4.4")).passed


def test_a_reading_outside_tolerance_fails_and_says_which():
    made = check(micronaire=Decimal("4.5"))
    assert not made.passed
    assert made.failures == ("micronaire",)
    assert "out on micronaire" in str(made)


def test_asking_about_a_measure_nobody_checks():
    with pytest.raises(ValidationError):
        check().deviation("colour")


def test_the_log_keeps_the_checks_oldest_first():
    log = CalibrationLog()
    log.extend([check(DAY + timedelta(days=1)), check(DAY)])
    assert [one.checked_on for one in log.checks()] == [DAY, DAY + timedelta(days=1)]
    assert len(log) == 2


def test_an_empty_log_has_nothing_to_say():
    log = CalibrationLog()
    assert log.latest() is None
    assert log.last_good() is None
    assert log.suspect_since() is None
    assert not log.drifting("micronaire")


def test_the_cards_are_suspect_back_to_the_last_good_check():
    log = CalibrationLog()
    log.extend(
        [
            check(DAY),
            check(DAY + timedelta(days=1)),
            check(DAY + timedelta(days=2), micronaire=Decimal("4.6")),
        ]
    )
    assert log.suspect_since() == DAY + timedelta(days=1)
    assert [one.checked_on for one in log.failures()] == [DAY + timedelta(days=2)]


def test_nothing_is_suspect_while_the_line_reads_true():
    log = CalibrationLog()
    log.extend([check(DAY), check(DAY + timedelta(days=1))])
    assert log.suspect_since() is None


def test_everything_is_suspect_when_no_check_ever_passed():
    log = CalibrationLog()
    log.add(check(DAY, micronaire=Decimal("4.6")))
    assert log.suspect_since() == DAY


def test_a_line_creeping_one_way_is_drifting():
    log = CalibrationLog()
    for offset in range(4):
        log.add(check(DAY + timedelta(days=offset), micronaire=Decimal("4.4")))
    assert log.drifting("micronaire")
    assert log.drift("micronaire") == Decimal("0.0")


def test_a_line_that_wanders_either_side_is_not_drifting():
    log = CalibrationLog()
    readings = ["4.4", "4.2", "4.4", "4.2"]
    for offset, value in enumerate(readings):
        log.add(check(DAY + timedelta(days=offset), micronaire=Decimal(value)))
    assert not log.drifting("micronaire")


def test_a_short_log_cannot_be_called_drifting():
    log = CalibrationLog()
    log.add(check(DAY, micronaire=Decimal("4.4")))
    assert not log.drifting("micronaire")
    assert log.drift("micronaire") == Decimal("0.0")


def test_drift_asks_about_a_measure_nobody_checks():
    with pytest.raises(ValidationError):
        CalibrationLog().drifting("colour")
