from datetime import date
from typing import Any

import pytest
from click.testing import Result

from moteroom.cli.options import read_date
from moteroom.core.errors import ValidationError
from tests.conftest import Run


@pytest.fixture()
def seeded(run: Run) -> Run:
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run("producer", "add", "MERRITT", "Merritt")
    return run


def weigh(
    run: Run,
    module: str = "HW-004182",
    producer: str = "BLYTHE",
    gross: str = "38400",
    tare: str = "17200",
    **kwargs: Any,
) -> Result:
    args = ["ticket", "weigh", module, producer, "3312", gross, tare]
    for name, value in kwargs.items():
        args.extend([f"--{name.replace('_', '-')}", value])
    return run(*args)


def test_a_ticket_weighs_in_and_prints_its_net(seeded):
    result = weigh(seeded)
    assert result.exit_code == 0
    assert "ticket 1" in result.output
    assert "21,200 lb" in result.output


def test_tickets_number_themselves(seeded):
    weigh(seeded)
    second = weigh(seeded, module="HW-004183")
    assert "ticket 2" in second.output


def test_a_module_cannot_weigh_in_twice(seeded):
    weigh(seeded)
    assert weigh(seeded).exit_code != 0


def test_a_producer_nobody_added_is_refused(seeded):
    assert weigh(seeded, producer="GHOST").exit_code != 0


def test_a_tare_over_the_gross_is_refused(seeded):
    assert weigh(seeded, gross="17000", tare="17200").exit_code != 0


def test_a_weight_that_will_not_read_is_refused(seeded):
    assert weigh(seeded, gross="lots").exit_code != 0


def test_a_moisture_off_the_probe_is_refused(seeded):
    assert weigh(seeded, moisture="99.0").exit_code != 0


def test_a_weigh_date_outside_the_season_is_refused(seeded):
    assert weigh(seeded, on="2024-10-14").exit_code != 0


def test_a_date_that_will_not_read_is_refused(seeded):
    assert weigh(seeded, on="last tuesday").exit_code != 0


def test_a_ticket_shows_everything_the_scale_house_wrote(seeded):
    weigh(seeded, on="2025-10-14", moisture="9.4")
    shown = seeded("ticket", "show", "1")
    assert "21,200 lb" in shown.output
    assert "9.4%" in shown.output
    assert "live" in shown.output


def test_a_ticket_nobody_wrote(seeded):
    assert seeded("ticket", "show", "9").exit_code != 0


def test_a_correction_voids_the_first_ticket(seeded):
    weigh(seeded)
    corrected = seeded("ticket", "correct", "1", "38500", "17200")
    assert corrected.exit_code == 0
    assert "voids 1" in corrected.output
    assert "voided" in seeded("ticket", "show", "1").output
    assert "live" in seeded("ticket", "show", "2").output


def test_a_correction_for_a_ticket_nobody_wrote(seeded):
    assert seeded("ticket", "correct", "9", "38500", "17200").exit_code != 0


def test_the_list_skips_the_voided_ticket(seeded):
    weigh(seeded)
    weigh(seeded, module="HW-004183")
    seeded("ticket", "correct", "1", "38500", "17200")
    listed = seeded("ticket", "list")
    assert listed.output.count("HW-004182") == 1
    assert "HW-004183" in listed.output


def test_the_list_can_be_narrowed_to_one_producer(seeded):
    weigh(seeded)
    weigh(seeded, module="HW-004183", producer="MERRITT")
    listed = seeded("ticket", "list", "--producer", "merritt")
    assert "MERRITT" in listed.output
    assert "HW-004182" not in listed.output


def test_an_empty_list_says_nothing(seeded):
    assert "(nothing)" in seeded("ticket", "list").output


def test_read_date_falls_back_to_the_day_given():
    assert read_date(None, date(2025, 8, 1)) == date(2025, 8, 1)
    assert read_date("2025-10-14", date(2025, 8, 1)) == date(2025, 10, 14)


def test_read_date_refuses_junk():
    with pytest.raises(ValidationError):
        read_date("14/10/2025", date(2025, 8, 1))


def test_the_yard_shows_what_is_waiting(seeded):
    weigh(seeded, on="2025-10-14")
    weigh(seeded, module="HW-004183", on="2025-10-14", moisture="12.0")
    listed = seeded("ticket", "yard", "--as-of", "2025-10-15")
    assert listed.output.index("HW-004183") < listed.output.index("HW-004182")
    assert "wet" in listed.output


def test_the_yard_drops_a_module_once_it_is_ginned(seeded):
    weigh(seeded, on="2025-10-14")
    weigh(seeded, module="HW-004183", on="2025-10-14")
    seeded(
        "lot",
        "gin",
        "1",
        "--lint",
        "7400",
        "--seed",
        "11800",
        "--motes",
        "1300",
        "--on",
        "2025-10-16",
    )
    listed = seeded("ticket", "yard", "--as-of", "2025-10-16")
    assert "HW-004182" not in listed.output
    assert "HW-004183" in listed.output


def test_the_yard_warns_about_a_module_held_too_long(seeded):
    weigh(seeded, on="2025-10-14", moisture="12.0")
    listed = seeded("ticket", "yard", "--as-of", "2025-10-30")
    assert "past their hold" in listed.output


def test_an_empty_yard_says_nothing(seeded):
    assert "(nothing)" in seeded("ticket", "yard", "--as-of", "2025-10-15").output
