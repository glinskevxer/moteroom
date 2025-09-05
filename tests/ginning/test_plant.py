from datetime import date, time
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.ginning.plant import Shift, ShiftLog, Stoppage

DAY = date(2025, 10, 16)


def shift(**overrides: Any) -> Shift:
    fields: dict[str, Any] = {
        "started_on": DAY,
        "started": time(7, 0),
        "finished": time(19, 0),
        "bales": 360,
        "stoppages": (Stoppage("choke", 45), Stoppage("trucks", 30)),
    }
    fields.update(overrides)
    return Shift(**fields)


def test_a_stoppage_names_a_reason_the_plant_logs():
    assert str(Stoppage("choke", 45)) == "choke 45 min"


@pytest.mark.parametrize("reason", ["", "gremlins", "CHOKE"])
def test_a_stoppage_reason_nobody_logs(reason):
    with pytest.raises(ValidationError):
        Stoppage(reason, 45)


@pytest.mark.parametrize("minutes", [0, -5])
def test_a_stoppage_has_to_last(minutes):
    with pytest.raises(ValidationError):
        Stoppage("choke", minutes)


def test_a_stoppage_is_whole_minutes():
    with pytest.raises(ValidationError):
        Stoppage("choke", True)


def test_a_shift_measures_itself():
    made = shift()
    assert made.elapsed == 720
    assert made.stopped == 75
    assert made.running == 645


def test_a_shift_that_runs_past_midnight():
    made = shift(started=time(19, 0), finished=time(7, 0))
    assert made.elapsed == 720


def test_a_shift_has_to_last():
    with pytest.raises(ValidationError):
        shift(started=time(7, 0), finished=time(7, 0))


def test_the_plant_cannot_stop_longer_than_it_ran():
    with pytest.raises(ValidationError):
        shift(stoppages=(Stoppage("choke", 800),))


@pytest.mark.parametrize("bales", [-1])
def test_a_negative_bale_count_is_refused(bales):
    with pytest.raises(ValidationError):
        shift(bales=bales)


def test_a_bale_count_is_not_a_bool():
    with pytest.raises(ValidationError):
        shift(bales=True)


def test_the_rate_on_running_time_beats_the_rate_on_the_shift():
    made = shift()
    assert made.bales_per_hour == Decimal("33.49")
    assert made.bales_per_shift_hour == Decimal("30.00")
    assert made.bales_per_hour > made.bales_per_shift_hour


def test_a_shift_that_never_ran_makes_nothing_an_hour():
    made = shift(bales=0, stoppages=(Stoppage("power", 720),))
    assert made.running == 0
    assert made.bales_per_hour == Decimal("0.00")


def test_availability_is_running_over_elapsed():
    assert shift().availability == Decimal("89.58")
    assert shift(stoppages=()).availability == Decimal("100.00")


def test_the_worst_stoppage_is_the_longest_one():
    found = shift().worst_stoppage()
    assert found is not None
    assert found.reason == "choke"
    assert shift(stoppages=()).worst_stoppage() is None


def test_a_shift_prints_its_line():
    assert str(shift()) == "2025-10-16 360 bales at 33.49 an hour"


def test_a_log_totals_the_season():
    log = ShiftLog()
    log.extend([shift(), shift(started_on=date(2025, 10, 17), bales=400)])
    assert len(log) == 2
    assert log.bales() == 760
    assert log.elapsed() == 1_440
    assert log.running() == 1_290


def test_a_log_weights_the_rate_by_time():
    log = ShiftLog()
    log.extend(
        [
            shift(bales=100, stoppages=()),
            shift(started=time(7, 0), finished=time(9, 0), bales=100, stoppages=()),
        ]
    )
    assert log.rate() == Decimal("14.29")
    assert log.availability() == Decimal("100.00")


def test_an_empty_log_reports_nothing_rather_than_dividing():
    log = ShiftLog()
    assert log.rate() == Decimal("0.00")
    assert log.availability() == Decimal("0.00")
    assert log.worst_reason() is None


def test_the_season_is_told_what_cost_it_the_most():
    log = ShiftLog()
    log.extend(
        [
            shift(stoppages=(Stoppage("choke", 45),)),
            shift(started_on=date(2025, 10, 17), stoppages=(Stoppage("trucks", 90),)),
        ]
    )
    assert log.by_reason() == {"trucks": 90, "choke": 45}
    assert log.worst_reason() == "trucks"


def test_shifts_come_back_oldest_first_and_by_day():
    late = shift(started_on=date(2025, 10, 17))
    log = ShiftLog()
    log.extend([late, shift()])
    assert [one.started_on for one in log.shifts()] == [DAY, date(2025, 10, 17)]
    assert list(log.for_day(DAY)) == [shift()]
