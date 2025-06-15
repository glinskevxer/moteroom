from datetime import date

import pytest

from moteroom.core.errors import NotFoundError, ValidationError
from moteroom.core.ids import GinCode
from moteroom.core.money import CentsPerPound
from moteroom.storage.book import Book
from moteroom.storage.settings import (
    BASE_LOAN_RATE,
    CLASSING_OFFICE,
    GIN_CODE,
    WAREHOUSE,
    SettingsRepository,
)

DAY = date(2025, 8, 4)


@pytest.fixture()
def settings():
    with Book.open() as book:
        yield SettingsRepository(book.connection)


def test_a_setting_writes_and_reads_back(settings):
    settings.set(GIN_CODE, "41207", DAY)
    assert settings.get(GIN_CODE) == "41207"
    assert settings.gin_code() == GinCode("41207")


def test_a_setting_can_be_written_again(settings):
    settings.set(GIN_CODE, "41207", DAY)
    settings.set(GIN_CODE, "41208", DAY)
    assert settings.get(GIN_CODE) == "41208"
    assert len(settings.all()) == 1


def test_a_name_nobody_knows_is_refused(settings):
    with pytest.raises(ValidationError):
        settings.set("colour", "blue", DAY)


def test_a_setting_nobody_wrote(settings):
    with pytest.raises(NotFoundError):
        settings.get(GIN_CODE)
    assert settings.get_or(GIN_CODE, "none") == "none"


@pytest.mark.parametrize("value", ["4120", "abcde", ""])
def test_a_gin_code_is_checked_on_the_way_in(settings, value):
    with pytest.raises(ValidationError):
        settings.set(GIN_CODE, value, DAY)


@pytest.mark.parametrize("value", ["me", "MEMPHIS1", ""])
def test_an_office_name_is_checked(settings, value):
    with pytest.raises(ValidationError):
        settings.set(CLASSING_OFFICE, value, DAY)


def test_an_office_name_is_upper_cased(settings):
    assert settings.set(CLASSING_OFFICE, " memphis ", DAY) == "MEMPHIS"


@pytest.mark.parametrize("value", ["MW1", "MW14MW14M", "MW 14"])
def test_a_warehouse_code_is_checked(settings, value):
    with pytest.raises(ValidationError):
        settings.set(WAREHOUSE, value, DAY)


def test_a_loan_rate_is_checked_and_normalised(settings):
    assert settings.set(BASE_LOAN_RATE, "52.00c", DAY) == "52.00"
    assert settings.base_rate() == CentsPerPound.of("52.00")
    with pytest.raises(ValidationError):
        settings.set(BASE_LOAN_RATE, "52.001", DAY)


def test_the_missing_list_shrinks_as_settings_are_written(settings):
    assert settings.missing() == sorted([BASE_LOAN_RATE, CLASSING_OFFICE, GIN_CODE, WAREHOUSE])
    settings.set(GIN_CODE, "41207", DAY)
    assert GIN_CODE not in settings.missing()
