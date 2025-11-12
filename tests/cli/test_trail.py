import pytest

from tests.conftest import Run


@pytest.fixture()
def worked(run: Run) -> Run:
    run("setting", "set", "gin_code", "41207")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    run("bale", "press", "1", "538", "--on", "2025-10-16")
    return run


def test_the_trail_records_what_was_done(worked):
    listed = worked("audit", "list")
    assert listed.exit_code == 0
    assert "weigh" in listed.output
    assert "gin" in listed.output
    assert "press" in listed.output


def test_the_trail_is_newest_first(worked):
    listed = worked("audit", "list")
    assert listed.output.index("press") < listed.output.index("weigh")


def test_one_subject_shows_its_own_history(worked):
    worked("ticket", "correct", "1", "38500", "17200")
    shown = worked("audit", "subject", "hw-004181")
    assert shown.output.count("HW-004181") == 0
    assert "weigh" in shown.output
    assert "correct" in shown.output


def test_the_actions_are_counted(worked):
    counted = worked("audit", "actions")
    assert "weigh" in counted.output
    assert "entries" in counted.output


def test_a_rolled_back_command_leaves_no_trail(worked):
    worked("bale", "press", "1", "180", "--on", "2025-10-16")
    assert worked("audit", "list").output.count("press") == 1


def test_an_empty_trail_says_nothing(run: Run) -> None:
    run("init")
    assert "(nothing)" in run("audit", "list").output
