import pytest

from moteroom.cli.ginning import read_tickets
from moteroom.core.errors import ValidationError
from tests.conftest import Run


@pytest.fixture()
def ginned(run: Run) -> Run:
    run("producer", "add", "BLYTHE", "Blythe Farms")
    for number in range(1, 4):
        run(
            "ticket",
            "weigh",
            f"HW-00418{number}",
            "BLYTHE",
            "3312",
            "38400",
            "17200",
            "--on",
            "2025-10-14",
        )
    return run


def test_a_lot_gins_and_takes_its_weight_off_the_tickets(ginned):
    result = ginned(
        "lot", "gin", "1,2", "--lint", "14900", "--seed", "23600", "--motes", "2600"
    )
    assert result.exit_code == 0
    assert "42,400 lb" in result.output
    assert "2025-0001" in result.output


def test_a_lot_cannot_gin_a_ticket_twice(ginned):
    ginned("lot", "gin", "1,2", "--lint", "14900", "--seed", "23600", "--motes", "2600")
    again = ginned("lot", "gin", "2,3", "--lint", "14900", "--seed", "23600")
    assert again.exit_code != 0


def test_a_lot_cannot_gin_a_voided_ticket(ginned):
    ginned("ticket", "correct", "1", "38500", "17200")
    result = ginned("lot", "gin", "1", "--lint", "7400", "--seed", "11800")
    assert result.exit_code != 0


def test_a_lot_cannot_gin_a_ticket_nobody_wrote(ginned):
    assert ginned("lot", "gin", "9", "--lint", "7400", "--seed", "11800").exit_code != 0


def test_a_ticket_list_that_will_not_read(ginned):
    assert ginned("lot", "gin", "one,two", "--lint", "7400", "--seed", "11800").exit_code != 0


def test_a_lot_that_makes_more_than_went_in_is_refused(ginned):
    result = ginned("lot", "gin", "1", "--lint", "20000", "--seed", "20000")
    assert result.exit_code != 0


def test_lots_number_themselves(ginned):
    ginned("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    second = ginned("lot", "gin", "2", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    assert "2025-0002" in second.output


def test_the_list_shows_turnout_and_a_band(ginned):
    ginned("lot", "gin", "1,2", "--lint", "14900", "--seed", "23600", "--motes", "2600")
    listed = ginned("lot", "list")
    assert "35.14" in listed.output
    assert "normal" in listed.output


def test_an_empty_list_says_nothing(ginned):
    assert "(nothing)" in ginned("lot", "list").output


def test_showing_a_lot_before_any_bales(ginned):
    ginned("lot", "gin", "1,2", "--lint", "14900", "--seed", "23600", "--motes", "2600")
    shown = ginned("lot", "show", "1")
    assert "no bales yet" in shown.output
    assert "closed       no" in shown.output


def test_showing_a_lot_nobody_ginned(ginned):
    assert ginned("lot", "show", "9").exit_code != 0


def test_a_lot_closes_once(ginned):
    ginned("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    assert ginned("lot", "close", "1").exit_code == 0
    assert "closed       yes" in ginned("lot", "show", "1").output
    assert ginned("lot", "close", "1").exit_code != 0


def test_closing_a_lot_nobody_ginned(ginned):
    assert ginned("lot", "close", "9").exit_code != 0


def test_read_tickets_reads_a_list():
    assert read_tickets("1,2, 3") == (1, 2, 3)


@pytest.mark.parametrize("text", ["", "one", "1,,2", "1;2"])
def test_read_tickets_refuses_junk(text):
    with pytest.raises(ValidationError):
        read_tickets(text)


def test_a_shift_reports_its_rate(ginned):
    made = ginned(
        "lot", "shift", "07:00", "19:00", "360", "--stop", "choke:45", "--on", "2025-10-16"
    )
    assert made.exit_code == 0
    assert "32.00 an hour running" in made.output
    assert "choke 45 min" in made.output


def test_a_shift_with_nothing_stopping_it(ginned):
    made = ginned("lot", "shift", "07:00", "19:00", "360", "--on", "2025-10-16")
    assert "nothing stopped it" in made.output
    assert "100.00%" in made.output


def test_a_stoppage_that_will_not_read(ginned):
    assert ginned("lot", "shift", "07:00", "19:00", "360", "--stop", "choke").exit_code != 0


def test_a_time_that_will_not_read(ginned):
    assert ginned("lot", "shift", "seven", "19:00", "360").exit_code != 0


def test_a_stoppage_longer_than_the_shift(ginned):
    assert ginned("lot", "shift", "07:00", "19:00", "360", "--stop", "choke:900").exit_code != 0
