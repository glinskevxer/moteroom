import pytest

from tests.cli.conftest import Run


@pytest.fixture()
def pressed(run: Run) -> Run:
    run("setting", "set", "gin_code", "41207")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    for number in range(1, 3):
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
    run("lot", "gin", "1,2", "--lint", "14900", "--seed", "23600", "--motes", "2600")
    return run


def test_a_bale_presses_and_prints_its_tag(pressed):
    result = pressed("bale", "press", "1", "538", "--on", "2025-10-16")
    assert result.exit_code == 0
    assert "5-41207-00001-" in result.output
    assert "515 lb" in result.output


def test_bale_numbers_run_forward(pressed):
    pressed("bale", "press", "1", "538", "--on", "2025-10-16")
    second = pressed("bale", "press", "1", "548", "--on", "2025-10-16")
    assert "00002" in second.output


def test_a_bale_off_a_lot_nobody_ginned(pressed):
    assert pressed("bale", "press", "9", "538").exit_code != 0


def test_a_closed_lot_takes_no_more_bales(pressed):
    pressed("bale", "press", "1", "538", "--on", "2025-10-16")
    pressed("lot", "close", "1")
    assert pressed("bale", "press", "1", "538", "--on", "2025-10-16").exit_code != 0


def test_a_bale_that_does_not_weigh_like_one(pressed):
    assert pressed("bale", "press", "1", "180", "--on", "2025-10-16").exit_code != 0


def test_pressing_without_a_gin_code_is_refused(run: Run) -> None:
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    assert run("bale", "press", "1", "538", "--on", "2025-10-16").exit_code != 0


def test_the_list_totals_the_bales(pressed):
    pressed("bale", "press", "1", "538", "--on", "2025-10-16")
    pressed("bale", "press", "1", "548", "--on", "2025-10-16")
    listed = pressed("bale", "list")
    assert "2 bales" in listed.output
    assert "1,040 lb" in listed.output


def test_the_list_can_be_narrowed_to_a_lot(pressed):
    pressed("bale", "press", "1", "538", "--on", "2025-10-16")
    assert "(nothing)" in pressed("bale", "list", "--lot", "2").output


def test_an_empty_list_says_nothing(pressed):
    assert "(nothing)" in pressed("bale", "list").output


def test_a_light_bale_is_flagged_in_the_list(pressed):
    pressed("bale", "press", "1", "420", "--on", "2025-10-16")
    assert "light" in pressed("bale", "list").output


def test_a_bale_shows_off_its_tag(pressed):
    made = pressed("bale", "press", "1", "538", "--on", "2025-10-16")
    tag = made.output.split()[1]
    shown = pressed("bale", "show", tag)
    assert "515 lb" in shown.output
    assert "flag      none" in shown.output


def test_a_tag_that_will_not_read(pressed):
    assert pressed("bale", "show", "123").exit_code != 0


def test_a_bale_nobody_pressed(pressed):
    assert pressed("bale", "show", "541207000019").exit_code != 0
