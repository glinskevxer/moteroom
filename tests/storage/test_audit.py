from datetime import datetime

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.season import Season
from moteroom.storage.audit import AuditRepository
from moteroom.storage.book import Book

SEASON = Season(2025)
AT = datetime(2025, 10, 14, 18, 30, 15)


@pytest.fixture()
def trail():
    with Book.open() as book:
        yield AuditRepository(book.connection)


def test_an_entry_records_and_reads_back(trail):
    trail.record(SEASON, "weigh", "HW-004181", "ticket 1", AT)
    entries = trail.entries(SEASON)
    assert entries[0].action == "weigh"
    assert entries[0].subject == "HW-004181"
    assert entries[0].at == AT
    assert str(entries[0]).endswith("weigh HW-004181")


def test_entries_come_back_newest_first(trail):
    trail.record(SEASON, "weigh", "A", "one", AT)
    trail.record(SEASON, "press", "B", "two", AT)
    assert [entry.subject for entry in trail.entries(SEASON)] == ["B", "A"]


def test_the_limit_holds(trail):
    for number in range(5):
        trail.record(SEASON, "weigh", str(number), "", AT)
    assert len(trail.entries(SEASON, limit=2)) == 2
    with pytest.raises(ValidationError):
        trail.entries(SEASON, limit=0)


def test_one_subject_reads_oldest_first(trail):
    trail.record(SEASON, "weigh", "HW-004181", "one", AT)
    trail.record(SEASON, "correct", "HW-004181", "two", AT)
    assert [entry.action for entry in trail.for_subject("HW-004181")] == ["weigh", "correct"]
    assert trail.for_subject("HW-999999") == []


def test_a_blank_action_or_subject_is_refused(trail):
    with pytest.raises(ValidationError):
        trail.record(SEASON, "  ", "A", "", AT)
    with pytest.raises(ValidationError):
        trail.record(SEASON, "weigh", " ", "", AT)


def test_a_long_detail_is_refused(trail):
    with pytest.raises(ValidationError):
        trail.record(SEASON, "weigh", "A", "x" * 401, AT)


def test_actions_are_counted_most_used_first(trail):
    trail.record(SEASON, "weigh", "A", "", AT)
    trail.record(SEASON, "weigh", "B", "", AT)
    trail.record(SEASON, "press", "C", "", AT)
    assert trail.actions(SEASON) == {"weigh": 2, "press": 1}
    assert trail.count(SEASON) == 3


def test_seasons_are_kept_apart(trail):
    trail.record(SEASON, "weigh", "A", "", AT)
    trail.record(Season(2026), "weigh", "B", "", AT)
    assert trail.count(SEASON) == 1
    assert trail.count(Season(2026)) == 1
