import pytest

from tests.conftest import Run


@pytest.fixture()
def worked(run: Run) -> Run:
    run("setting", "set", "gin_code", "41207")
    run("setting", "set", "warehouse", "MW14")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run(
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
    for gross in ("538", "548"):
        run("bale", "press", "1", gross, "--on", "2025-10-16")
    return run


def test_the_daily_sheet_shows_the_day_asked_for(worked):
    made = worked("report", "daily", "--on", "2025-10-16")
    assert made.exit_code == 0
    assert "2025-0001" in made.output
    assert "turnout" in made.output


def test_a_day_with_nothing_still_prints(worked):
    made = worked("report", "daily", "--on", "2025-10-17")
    assert "nothing ginned" in made.output


def test_a_report_can_come_out_as_csv(worked):
    made = worked("report", "daily", "--on", "2025-10-16", "--csv")
    assert made.output.splitlines()[0].startswith("lot,modules")
    assert "=" not in made.output


def test_the_quality_report_takes_a_kind(worked):
    assert worked("report", "quality").exit_code == 0
    assert "no cards back yet" in worked("report", "quality", "--kind", "averages").output


def test_a_kind_nobody_has(worked):
    assert worked("report", "quality", "--kind", "colour-ish").exit_code != 0


def test_the_position_report_reads_by_house_and_by_holder(worked):
    worked(
        "receipt",
        "issue",
        "541207000018",
        "MW00000001",
        "--holder",
        "BLYTHE",
        "--on",
        "2025-10-20",
    )
    house = worked("report", "position", "--as-of", "2025-12-01")
    holder = worked("report", "position", "--by", "holder", "--as-of", "2025-12-01")
    assert "MW14" in house.output
    assert "BLYTHE" in holder.output


def test_the_storage_report_bills_what_is_in_store(worked):
    worked(
        "receipt",
        "issue",
        "541207000018",
        "MW00000001",
        "--holder",
        "BLYTHE",
        "--on",
        "2025-10-20",
    )
    made = worked("report", "storage", "--as-of", "2025-12-01")
    assert "owed" in made.output


def test_the_settlement_report_starts_empty(worked):
    assert "nothing settled yet" in worked("report", "settlements").output


def test_the_settlement_report_fills_in(worked):
    worked("settle", "rates")
    worked("settle", "run", "BLYTHE", "--on", "2026-02-03")
    made = worked("report", "settlements")
    assert "BLYTHE" in made.output
    assert "1 to pay" in made.output


def test_the_outstanding_report_names_who_is_left(worked):
    assert "BLYTHE" in worked("report", "outstanding").output
    worked("settle", "rates")
    worked("settle", "run", "BLYTHE", "--on", "2026-02-03")
    assert "0 of 1" in worked("report", "outstanding").output


def test_a_statement_prints_once_it_is_settled(worked):
    assert worked("report", "statement", "BLYTHE").exit_code != 0
    worked("settle", "rates")
    worked("settle", "run", "BLYTHE", "--on", "2026-02-03")
    made = worked("report", "statement", "blythe")
    assert "lint proceeds" in made.output
    assert "due to the producer" in made.output


def test_a_report_on_a_book_that_does_not_exist(run: Run) -> None:
    assert run("report", "daily").exit_code != 0
