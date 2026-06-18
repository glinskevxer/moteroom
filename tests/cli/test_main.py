from datetime import date

import pytest
from click.testing import CliRunner

from moteroom import __version__
from moteroom.cli.context import Session
from moteroom.cli.main import main
from moteroom.core.errors import ValidationError
from moteroom.core.season import Season


@pytest.fixture()
def runner():
    return CliRunner()


def test_the_version_prints(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_about_says_there_is_no_book_yet(runner, tmp_path):
    result = runner.invoke(main, ["--book", str(tmp_path / "none.sqlite3"), "about"])
    assert result.exit_code == 0
    assert "no book yet" in result.output


def test_init_creates_the_book(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    result = runner.invoke(main, ["--book", str(path), "init"])
    assert result.exit_code == 0
    assert "created" in result.output
    assert path.exists()


def test_init_on_an_existing_book_opens_it(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    runner.invoke(main, ["--book", str(path), "init"])
    result = runner.invoke(main, ["--book", str(path), "init"])
    assert "opened" in result.output


def test_about_counts_the_tables(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    runner.invoke(main, ["--book", str(path), "init"])
    result = runner.invoke(main, ["--book", str(path), "about"])
    assert "producers" in result.output
    assert "schema" in result.output


def test_the_season_can_be_given(runner, tmp_path):
    result = runner.invoke(
        main, ["--book", str(tmp_path / "none.sqlite3"), "--season", "2024/25", "about"]
    )
    assert "2024/25" in result.output


def test_a_season_that_will_not_read_is_refused(runner, tmp_path):
    result = runner.invoke(
        main, ["--book", str(tmp_path / "none.sqlite3"), "--season", "cotton", "about"]
    )
    assert result.exit_code != 0


def test_the_book_can_come_from_the_environment(runner, tmp_path, monkeypatch):
    path = tmp_path / "env.sqlite3"
    monkeypatch.setenv("MOTEROOM_BOOK", str(path))
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert path.exists()


def test_a_session_reads_the_season_off_the_date():
    session = Session.build(":memory:", None, date(2025, 10, 14))
    assert session.season == Season(2025)


def test_a_session_takes_the_season_it_is_given():
    session = Session.build(":memory:", "2024", date(2025, 10, 14))
    assert session.season == Season(2024)


def test_a_session_opens_the_book_once():
    session = Session.build(":memory:", "2025", date(2025, 10, 14))
    assert session.book() is session.book()
    session.close()


def test_requiring_a_book_that_is_not_there(tmp_path):
    session = Session.build(tmp_path / "none.sqlite3", "2025", date(2025, 10, 14))
    with pytest.raises(ValidationError):
        session.require_book()


def test_requiring_a_book_that_is_there(tmp_path):
    path = tmp_path / "season.sqlite3"
    Session.build(path, "2025", date(2025, 10, 14)).book().close()
    session = Session.build(path, "2025", date(2025, 10, 14))
    assert session.require_book().version > 0
    session.close()


def test_closing_an_empty_season_passes(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    runner.invoke(main, ["--book", str(path), "init"])
    result = runner.invoke(main, ["--book", str(path), "--season", "2025", "close"])
    assert result.exit_code == 0
    assert "can close" in result.output
    assert "ok   modules ginned" in result.output


def test_closing_a_season_with_cotton_in_the_yard_fails(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    base = ["--book", str(path), "--season", "2025"]
    runner.invoke(main, [*base, "producer", "add", "BLYTHE", "Blythe Farms"])
    runner.invoke(
        main,
        [
            *base,
            "ticket",
            "weigh",
            "HW-004181",
            "BLYTHE",
            "3312",
            "38400",
            "17200",
            "--on",
            "2025-10-14",
        ],
    )
    result = runner.invoke(main, [*base, "close"])
    assert result.exit_code != 0
    assert "still in the yard" in result.output


def test_closing_a_book_that_is_not_there(runner, tmp_path):
    result = runner.invoke(main, ["--book", str(tmp_path / "none.sqlite3"), "close"])
    assert result.exit_code != 0


def test_a_backup_copies_the_book(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    runner.invoke(main, ["--book", str(path), "init"])
    copy = tmp_path / "copy.sqlite3"
    result = runner.invoke(main, ["--book", str(path), "backup", str(copy)])
    assert result.exit_code == 0
    assert copy.exists()
    assert "copied" in result.output


def test_a_backup_will_not_write_over_something(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    runner.invoke(main, ["--book", str(path), "init"])
    copy = tmp_path / "copy.sqlite3"
    runner.invoke(main, ["--book", str(path), "backup", str(copy)])
    assert runner.invoke(main, ["--book", str(path), "backup", str(copy)]).exit_code != 0


def test_verify_reads_the_book_it_is_given(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    runner.invoke(main, ["--book", str(path), "init"])
    result = runner.invoke(main, ["--book", str(path), "verify"])
    assert result.exit_code == 0
    assert "is sound" in result.output


def test_verify_fails_on_a_book_that_is_not_there(runner, tmp_path):
    result = runner.invoke(main, ["--book", str(tmp_path / "none.sqlite3"), "verify"])
    assert result.exit_code != 0


def test_a_write_that_raises_leaves_nothing_behind(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    base = ["--book", str(path), "--season", "2025"]
    runner.invoke(main, [*base, "producer", "add", "BLYTHE", "Blythe Farms"])
    runner.invoke(
        main,
        [
            *base,
            "ticket",
            "weigh",
            "HW-004181",
            "BLYTHE",
            "3312",
            "38400",
            "17200",
            "--on",
            "2025-10-14",
        ],
    )
    failed = runner.invoke(
        main,
        [
            *base,
            "ticket",
            "weigh",
            "HW-004181",
            "BLYTHE",
            "3312",
            "38400",
            "17200",
            "--on",
            "2025-10-14",
        ],
    )
    assert failed.exit_code != 0
    listed = runner.invoke(main, [*base, "ticket", "list"])
    assert listed.output.count("HW-004181") == 1
    trail = runner.invoke(main, [*base, "audit", "list"])
    assert trail.output.count("weigh") == 1


def test_a_write_command_makes_the_book_when_it_has_to(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    result = runner.invoke(
        main, ["--book", str(path), "producer", "add", "BLYTHE", "Blythe Farms"]
    )
    assert result.exit_code == 0
    assert path.exists()


def test_a_write_command_that_needs_a_book_says_so(runner, tmp_path):
    result = runner.invoke(
        main,
        [
            "--book",
            str(tmp_path / "none.sqlite3"),
            "--season",
            "2025",
            "lot",
            "gin",
            "1",
            "--lint",
            "100",
            "--seed",
            "100",
        ],
    )
    assert result.exit_code != 0


def test_the_size_command_reads_the_book(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    base = ["--book", str(path), "--season", "2025"]
    runner.invoke(main, [*base, "producer", "add", "BLYTHE", "Blythe Farms"])
    result = runner.invoke(main, [*base, "size"])
    assert result.exit_code == 0
    assert "pages free" in result.output
    assert "producers" in result.output


def test_compacting_says_what_it_saved(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    base = ["--book", str(path), "--season", "2025"]
    runner.invoke(main, [*base, "init"])
    result = runner.invoke(main, [*base, "compact"])
    assert result.exit_code == 0
    assert "before" in result.output
    assert "saved" in result.output


def test_size_on_a_book_that_is_not_there(runner, tmp_path):
    result = runner.invoke(main, ["--book", str(tmp_path / "none.sqlite3"), "size"])
    assert result.exit_code != 0


def test_an_export_writes_the_season_out(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    base = ["--book", str(path), "--season", "2025"]
    runner.invoke(main, [*base, "producer", "add", "BLYTHE", "Blythe Farms"])
    result = runner.invoke(
        main, [*base, "export", str(tmp_path / "out"), "--as-of", "2026-02-03"]
    )
    assert result.exit_code == 0
    assert "files in" in result.output
    assert (tmp_path / "out" / "moteroom-2025" / "season.txt").exists()


def test_an_export_will_not_write_over_another(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    base = ["--book", str(path), "--season", "2025"]
    runner.invoke(main, [*base, "init"])
    runner.invoke(main, [*base, "export", str(tmp_path / "out"), "--as-of", "2026-02-03"])
    again = runner.invoke(
        main, [*base, "export", str(tmp_path / "out"), "--as-of", "2026-02-03"]
    )
    assert again.exit_code != 0


def test_the_doctor_looks_over_a_fresh_book(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    base = ["--book", str(path), "--season", "2025"]
    runner.invoke(main, [*base, "init"])
    result = runner.invoke(main, [*base, "doctor", "--as-of", "2025-12-01"])
    assert result.exit_code == 0
    assert "the book is missing" in result.output
    assert "gin_code" in result.output


def test_the_doctor_reads_fine_once_the_book_is_set_up(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    base = ["--book", str(path), "--season", "2025"]
    for name, value in (
        ("gin_code", "41207"),
        ("classing_office", "MEMPHIS"),
        ("warehouse", "MW14"),
        ("base_loan_rate", "52.00"),
    ):
        runner.invoke(main, [*base, "setting", "set", name, value])
    runner.invoke(main, [*base, "settle", "rates"])
    result = runner.invoke(main, [*base, "doctor", "--as-of", "2025-12-01"])
    assert "the book is fine" in result.output


def test_the_doctor_needs_a_book(runner, tmp_path):
    result = runner.invoke(main, ["--book", str(tmp_path / "none.sqlite3"), "doctor"])
    assert result.exit_code != 0


def test_the_seasons_command_lists_what_the_book_holds(runner, tmp_path):
    path = tmp_path / "gin.sqlite3"
    for season, weighed in (("2024", "2024-10-14"), ("2025", "2025-10-14")):
        base = ["--book", str(path), "--season", season]
        runner.invoke(main, [*base, "producer", "add", "BLYTHE", "Blythe Farms"])
        runner.invoke(
            main,
            [
                *base,
                "ticket",
                "weigh",
                f"HW-{season}",
                "BLYTHE",
                "3312",
                "38400",
                "17200",
                "--on",
                weighed,
            ],
        )
    result = runner.invoke(main, ["--book", str(path), "--season", "2025", "seasons"])
    assert result.exit_code == 0
    assert "2024/25" in result.output
    assert "* 2025/26" in result.output


def test_the_seasons_command_on_an_empty_book(runner, tmp_path):
    path = tmp_path / "season.sqlite3"
    runner.invoke(main, ["--book", str(path), "init"])
    result = runner.invoke(main, ["--book", str(path), "seasons"])
    assert "nothing in this book yet" in result.output
