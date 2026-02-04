from click.testing import CliRunner

from moteroom.cli.main import main


def test_a_producer_adds_and_lists(run):
    assert run("producer", "add", "blythe", "Blythe Farms").exit_code == 0
    listed = run("producer", "list")
    assert "BLYTHE" in listed.output
    assert "Blythe Farms" in listed.output


def test_the_same_producer_twice_is_refused(run):
    run("producer", "add", "BLYTHE", "Blythe Farms")
    assert run("producer", "add", "BLYTHE", "Blythe Brothers").exit_code != 0


def test_a_producer_code_that_will_not_read(run):
    assert run("producer", "add", "1", "Blythe Farms").exit_code != 0


def test_producers_list_in_code_order(run):
    run("producer", "add", "MERRITT", "Merritt")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    listed = run("producer", "list")
    assert listed.output.index("BLYTHE") < listed.output.index("MERRITT")


def test_listing_a_book_that_does_not_exist(tmp_path):
    result = CliRunner().invoke(
        main, ["--book", str(tmp_path / "none.sqlite3"), "producer", "list"]
    )
    assert result.exit_code != 0


def test_a_farm_adds_against_a_producer(run):
    run("producer", "add", "BLYTHE", "Blythe Farms")
    assert run("producer", "farm", "blythe", "3312", "1140", "284.50").exit_code == 0
    shown = run("producer", "show", "blythe")
    assert "3312" in shown.output
    assert "284.50" in shown.output


def test_acres_that_will_not_read(run):
    run("producer", "add", "BLYTHE", "Blythe Farms")
    assert run("producer", "farm", "BLYTHE", "3312", "1140", "lots").exit_code != 0


def test_a_farm_for_a_producer_nobody_added(run):
    run("producer", "add", "BLYTHE", "Blythe Farms")
    assert run("producer", "farm", "GHOST", "3312", "1140", "10.00").exit_code != 0


def test_showing_a_producer_nobody_added(run):
    run("producer", "add", "BLYTHE", "Blythe Farms")
    assert run("producer", "show", "MERRITT").exit_code != 0


def test_showing_a_producer_with_no_farms(run):
    run("producer", "add", "BLYTHE", "Blythe Farms")
    shown = run("producer", "show", "BLYTHE")
    assert "farms" in shown.output
    assert "(nothing)" not in shown.output


def test_the_farm_count_shows_in_the_list(run):
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run("producer", "farm", "BLYTHE", "3312", "1140", "284.50")
    run("producer", "farm", "BLYTHE", "3312", "1141", "120.25")
    listed = run("producer", "list")
    assert listed.output.strip().endswith("2")


def test_a_producer_season_reads_off_the_book(run):
    run("setting", "set", "gin_code", "41207")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    shown = run("producer", "season", "blythe")
    assert shown.exit_code == 0
    assert "21,200 lb" in shown.output
    assert "plant turnout" in shown.output
    assert "not yet" in shown.output


def test_a_producer_season_for_somebody_nobody_added(run):
    run("producer", "add", "BLYTHE", "Blythe Farms")
    assert run("producer", "season", "MERRITT").exit_code != 0
