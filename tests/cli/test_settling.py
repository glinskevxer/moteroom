import pytest

from tests.conftest import Run


@pytest.fixture()
def ginned(run: Run) -> Run:
    run("setting", "set", "gin_code", "41207")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run("producer", "add", "MERRITT", "Merritt")
    for number, producer in ((1, "BLYTHE"), (2, "MERRITT")):
        run(
            "ticket",
            "weigh",
            f"HW-00418{number}",
            producer,
            "3312",
            "38400",
            "17200",
            "--moisture",
            "7.5",
            "--on",
            "2025-10-14",
        )
    run("lot", "gin", "1,2", "--lint", "14900", "--seed", "23600", "--motes", "2600")
    for _ in range(4):
        run("bale", "press", "1", "538", "--on", "2025-10-16")
    return run


def test_rates_post_once_and_read_back(ginned):
    assert ginned("settle", "rates").exit_code == 0
    assert "4.25" in ginned("settle", "rates", "--show").output
    assert ginned("settle", "rates").exit_code != 0


def test_reading_rates_nobody_posted(ginned):
    assert ginned("settle", "rates", "--show").exit_code != 0


def test_a_preview_shows_the_lot_shares(ginned):
    ginned("settle", "rates")
    shown = ginned("settle", "preview", "blythe")
    assert "7,450 lb" in shown.output
    assert "base rate" in shown.output
    assert "2025-0001" in shown.output


def test_a_preview_works_without_posted_rates(ginned):
    assert ginned("settle", "preview", "BLYTHE").exit_code == 0


def test_a_preview_for_a_producer_with_no_cotton(ginned):
    ginned("producer", "add", "COLE", "Cole")
    assert ginned("settle", "preview", "COLE").exit_code != 0


def test_an_advance_comes_off_the_preview(ginned):
    ginned("settle", "rates")
    before = ginned("settle", "preview", "BLYTHE").output
    ginned("settle", "advance", "BLYTHE", "A-114", "1000.00", "--on", "2025-11-03")
    after = ginned("settle", "preview", "BLYTHE").output
    assert "advance A-114" in after
    assert before != after


def test_the_same_advance_twice_is_refused(ginned):
    ginned("settle", "advance", "BLYTHE", "A-114", "1000.00", "--on", "2025-11-03")
    assert ginned("settle", "advance", "BLYTHE", "A-114", "10.00").exit_code != 0


def test_an_advance_that_will_not_read(ginned):
    assert ginned("settle", "advance", "BLYTHE", "A-114", "lots").exit_code != 0


def test_a_settlement_writes_once(ginned):
    ginned("settle", "rates")
    first = ginned("settle", "run", "BLYTHE", "--on", "2026-02-03")
    assert first.exit_code == 0
    assert "due" in first.output
    assert ginned("settle", "run", "BLYTHE", "--on", "2026-02-03").exit_code != 0


def test_a_settlement_comes_out_owing_when_the_advances_are_bigger(ginned):
    ginned("settle", "rates")
    ginned("settle", "advance", "BLYTHE", "A-114", "9000.00", "--on", "2025-11-03")
    result = ginned("settle", "run", "BLYTHE", "--on", "2026-02-03")
    assert "owing" in result.output


def test_the_list_shows_what_has_been_settled(ginned):
    ginned("settle", "rates")
    ginned("settle", "run", "BLYTHE", "--on", "2026-02-03")
    listed = ginned("settle", "list")
    assert "BLYTHE" in listed.output
    assert "MERRITT" not in listed.output


def test_an_empty_list_says_nothing(ginned):
    assert "(nothing)" in ginned("settle", "list").output


def test_the_margin_allocates_on_ginned_volume(ginned):
    made = ginned("settle", "equity", "30000.00")
    assert made.exit_code == 0
    assert "BLYTHE" in made.output
    assert "MERRITT" in made.output
    assert "2 members" in made.output


def test_the_cash_and_equity_shares_can_be_set(ginned):
    all_cash = ginned("settle", "equity", "30000.00", "--cash", "1", "--retain", "0")
    assert "$30,000.00 in cash" in all_cash.output
    assert "$0.00 retained" in all_cash.output


def test_a_margin_that_will_not_read(ginned):
    assert ginned("settle", "equity", "lots").exit_code != 0


def test_a_loss_is_not_allocated(ginned):
    assert ginned("settle", "equity", "-100.00").exit_code != 0


def test_allocating_with_nothing_ginned(run: Run) -> None:
    run("producer", "add", "BLYTHE", "Blythe Farms")
    assert run("settle", "equity", "30000.00").exit_code != 0
