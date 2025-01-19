from datetime import date

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.season import Season


def test_a_season_opens_on_the_first_of_august():
    assert Season(2025).start == date(2025, 8, 1)
    assert Season(2025).end == date(2026, 7, 31)


def test_a_season_is_named_for_the_year_it_opens():
    assert Season(2025).label == "2025/26"
    assert str(Season(2029)) == "2029/30"


@pytest.mark.parametrize(
    ("day", "year"),
    [
        (date(2025, 8, 1), 2025),
        (date(2025, 10, 14), 2025),
        (date(2025, 12, 31), 2025),
        (date(2026, 1, 2), 2025),
        (date(2026, 7, 31), 2025),
        (date(2026, 8, 1), 2026),
        (date(2025, 7, 31), 2024),
    ],
)
def test_a_date_falls_in_the_crop_year_that_was_open(day, year):
    assert Season.for_date(day) == Season(year)


@pytest.mark.parametrize(
    ("text", "year"),
    [
        ("2025", 2025),
        (" 2025 ", 2025),
        ("2025/26", 2025),
        ("2025-26", 2025),
        ("2025/2026", 2025),
    ],
)
def test_parse_reads_a_season_either_way_round(text, year):
    assert Season.parse(text) == Season(year)


@pytest.mark.parametrize("text", ["", "cotton", "25", "2025/27", "2025/2027", "20255"])
def test_parse_refuses_junk(text):
    with pytest.raises(ValidationError):
        Season.parse(text)


@pytest.mark.parametrize("year", [1979, 2100])
def test_a_season_outside_the_book_is_refused(year):
    with pytest.raises(ValidationError):
        Season(year)


def test_a_season_is_not_a_bool():
    with pytest.raises(ValidationError):
        Season(True)


def test_contains_covers_the_whole_year_and_nothing_else():
    season = Season(2025)
    assert season.contains(date(2025, 8, 1))
    assert season.contains(date(2026, 7, 31))
    assert not season.contains(date(2025, 7, 31))
    assert not season.contains(date(2026, 8, 1))


def test_neighbours():
    assert Season(2025).next() == Season(2026)
    assert Season(2025).previous() == Season(2024)


def test_the_tag_digit_is_the_last_of_the_opening_year():
    assert Season(2025).digit == 5
    assert Season(2030).digit == 0


def test_seasons_sort():
    assert sorted([Season(2026), Season(2024)]) == [Season(2024), Season(2026)]
