from datetime import date, time

import click
import pytest
from click.testing import CliRunner

from moteroom.cli.options import as_of_option, csv_option, on_option, read_date, read_time
from moteroom.core.errors import ValidationError


def test_a_date_falls_back_to_the_day_given():
    assert read_date(None, date(2025, 8, 1)) == date(2025, 8, 1)
    assert read_date("", date(2025, 8, 1)) == date(2025, 8, 1)
    assert read_date("2025-10-14", date(2025, 8, 1)) == date(2025, 10, 14)


@pytest.mark.parametrize("text", ["14/10/2025", "2025-13-01", "tuesday"])
def test_a_date_that_will_not_read(text):
    with pytest.raises(ValidationError):
        read_date(text, date(2025, 8, 1))


def test_a_clock_time_reads_back():
    assert read_time(" 07:00 ") == time(7, 0)
    assert read_time("19:30") == time(19, 30)


@pytest.mark.parametrize("text", ["7", "25:00", "seven"])
def test_a_time_that_will_not_read(text):
    with pytest.raises(ValidationError):
        read_time(text)


def test_the_on_option_is_worded_the_same_way_everywhere():
    @click.command()
    @on_option("Gin date")
    def command(on_text: str | None) -> None:
        click.echo(str(on_text))

    help_text = CliRunner().invoke(command, ["--help"]).output
    assert "Gin date, Y-m-d." in help_text


def test_the_as_of_option_takes_a_value():
    @click.command()
    @as_of_option("Position date")
    def command(as_of: str | None) -> None:
        click.echo(str(as_of))

    result = CliRunner().invoke(command, ["--as-of", "2025-12-01"])
    assert result.output.strip() == "2025-12-01"


def test_the_csv_flag_is_off_unless_it_is_given():
    @click.command()
    @csv_option
    def command(csv_out: bool) -> None:
        click.echo(str(csv_out))

    assert CliRunner().invoke(command, []).output.strip() == "False"
    assert CliRunner().invoke(command, ["--csv"]).output.strip() == "True"
