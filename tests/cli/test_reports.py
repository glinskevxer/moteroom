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


def test_the_colour_ladder_prints_every_rung(worked):
    made = worked("report", "ladder")
    assert made.exit_code == 0
    assert "colour ladder" in made.output
    assert "codes used" in made.output


def test_a_band_ladder_prints_its_bands(worked):
    made = worked("report", "ladder", "--kind", "micronaire")
    assert "3.7 to 4.2" in made.output


def test_the_leaf_ladder_prints(worked):
    made = worked("report", "ladder", "--kind", "leaf", "--csv")
    assert made.output.splitlines()[0] == "grade,cents,bales,percent,moved"


def test_a_ladder_nobody_has(worked):
    assert worked("report", "ladder", "--kind", "colour-ish").exit_code != 0


def test_the_producers_page_reads_off_the_book(worked):
    made = worked("report", "producers")
    assert made.exit_code == 0
    assert "BLYTHE" in made.output
    assert "1 producers" in made.output


def test_the_producers_page_on_an_empty_book(run):
    run("init")
    assert "nobody has ginned yet" in run("report", "producers").output


def test_the_freight_page_reads_off_the_book(worked):
    worked("ticket", "freight", "TRUXTON", "1", "18", "--on", "2025-10-14")
    by_hauler = worked("report", "freight")
    assert "TRUXTON" in by_hauler.output
    by_producer = worked("report", "freight", "--by", "producer")
    assert "BLYTHE" in by_producer.output


def test_the_freight_page_on_a_season_nobody_hauled(worked):
    assert "nothing hauled yet" in worked("report", "freight").output


def test_the_cash_page_reads_off_the_register(worked):
    worked("settle", "cheque", "BLYTHE", "--amount", "500.00", "--on", "2026-02-03")
    made = worked("report", "cash", "--as-of", "2026-03-01")
    assert made.exit_code == 0
    assert "cheques outstanding" in made.output
    assert "$500.00" in made.output


def test_the_cash_page_on_a_book_with_nothing_written(worked):
    made = worked("report", "cash", "--as-of", "2026-03-01")
    assert "nothing needs chasing" in made.output


def test_the_aging_page_buckets_what_is_in_store(worked):
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
    made = worked("report", "aging", "--as-of", "2026-02-01")
    assert made.exit_code == 0
    assert "91 to 180 days" in made.output
    assert "the oldest has been there" in made.output


def test_the_aging_page_on_an_empty_store(worked):
    assert "nothing in store" in worked("report", "aging", "--as-of", "2026-02-01").output


def test_the_turnaround_page_reads_off_the_cards(worked):
    made = worked("report", "turnaround")
    assert made.exit_code == 0
    assert "no cards back yet" in made.output


def test_the_turnaround_page_groups_by_week(run):
    run("setting", "set", "gin_code", "41207")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    run("bale", "press", "1", "538", "--on", "2025-10-16")
    made = run("report", "turnaround")
    assert made.exit_code == 0
