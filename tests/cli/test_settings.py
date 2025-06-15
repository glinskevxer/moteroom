from tests.cli.conftest import Run


def test_a_setting_writes_and_reads_back(run: Run) -> None:
    assert run("setting", "set", "gin_code", "41207").exit_code == 0
    assert run("setting", "get", "gin_code").output.strip() == "41207"


def test_a_setting_nobody_knows_is_refused(run: Run) -> None:
    assert run("setting", "set", "colour", "blue").exit_code != 0


def test_a_value_that_will_not_read_is_refused(run: Run) -> None:
    assert run("setting", "set", "gin_code", "4120").exit_code != 0


def test_reading_a_setting_nobody_wrote(run: Run) -> None:
    run("setting", "set", "gin_code", "41207")
    assert run("setting", "get", "warehouse").exit_code != 0


def test_the_list_names_what_is_still_missing(run: Run) -> None:
    run("setting", "set", "gin_code", "41207")
    listed = run("setting", "list")
    assert "41207" in listed.output
    assert "not set yet" in listed.output
    assert "warehouse" in listed.output


def test_the_list_stops_naming_them_once_they_are_set(run: Run) -> None:
    for name, value in (
        ("gin_code", "41207"),
        ("classing_office", "memphis"),
        ("warehouse", "MW14"),
        ("base_loan_rate", "52.00"),
    ):
        run("setting", "set", name, value)
    listed = run("setting", "list")
    assert "not set yet" not in listed.output
