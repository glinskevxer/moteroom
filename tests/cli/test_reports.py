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


def test_an_empty_book_has_nothing_to_report(run):
    run("init")
    made = run("report", "exceptions", "--as-of", "2025-10-17")
    assert made.exit_code == 0
    assert "nothing needs attention" in made.output


def test_a_wet_module_held_too_long_shows_up(run):
    run("setting", "set", "gin_code", "41207")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket",
        "weigh",
        "HW-004181",
        "BLYTHE",
        "3312",
        "38400",
        "17200",
        "--moisture",
        "12.4",
        "--on",
        "2025-10-14",
    )
    made = run("report", "exceptions", "--as-of", "2025-10-30")
    assert "urgent" in made.output
    assert "HW-004181" in made.output


def test_an_unclassed_bale_shows_up_after_three_weeks(worked):
    made = worked("report", "exceptions", "--as-of", "2025-12-01")
    assert "not classed" in made.output
    assert "findings" in made.output


def test_an_unsettled_producer_is_noted_until_they_are_settled(worked):
    made = worked("report", "exceptions", "--as-of", "2025-10-17")
    assert "not settled, 21,200 lb of lint" in made.output
    worked("settle", "rates")
    worked("settle", "run", "BLYTHE", "--on", "2026-02-03")
    after = worked("report", "exceptions", "--as-of", "2025-10-17")
    assert "not settled" not in after.output


def test_the_exception_report_can_come_out_as_csv(worked):
    made = worked("report", "exceptions", "--as-of", "2025-12-01", "--csv")
    assert made.output.splitlines()[0] == "level,what,detail"


def test_the_inventory_places_every_bale(worked):
    made = worked("report", "inventory")
    assert made.exit_code == 0
    assert "2 at the gin" in made.output
    assert "1,040 lb pressed" in made.output


def test_the_inventory_moves_a_bale_into_store(worked):
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
    made = worked("report", "inventory")
    assert "in store" in made.output
    assert "1 at the gin, 1 in store" in made.output


def test_the_season_page_reads_off_the_book(worked):
    made = worked("report", "season")
    assert made.exit_code == 0
    assert "turnout" in made.output
    assert "modules" in made.output
    assert "2 bales off 1 modules" in made.output


def test_the_season_page_on_an_empty_book(run):
    run("init")
    made = run("report", "season")
    assert made.exit_code == 0
    assert "0.00%" in made.output


def test_the_season_page_comes_out_as_csv(worked):
    made = worked("report", "season", "--csv")
    assert made.output.splitlines()[0] == "measure,value"
