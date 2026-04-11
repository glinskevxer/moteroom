from datetime import date
from pathlib import Path

import pytest

from moteroom.core.season import Season
from moteroom.service import doctor
from moteroom.storage.book import Book
from moteroom.storage.rates import default_terms
from moteroom.storage.registry import Repositories

SEASON = Season(2025)
AS_OF = date(2025, 12, 1)


@pytest.fixture()
def book():
    with Book.open() as opened:
        yield opened


def named(notes: list[doctor.Note]) -> dict[str, doctor.Note]:
    return {note.check: note for note in notes}


def test_a_fresh_book_is_sound_but_unfinished(book: Book) -> None:
    notes = doctor.look(book, SEASON, None, AS_OF)
    assert doctor.is_sound(notes)
    assert doctor.worst(notes) == doctor.MISSING
    assert named(notes)["schema"].is_fine


def test_the_settings_are_named_until_they_are_set(book: Book) -> None:
    repos = Repositories(book.connection)
    notes = named(doctor.look(book, SEASON, None, AS_OF))
    assert notes["settings"].state == doctor.MISSING
    assert "gin_code" in notes["settings"].detail
    for name, value in (
        ("gin_code", "41207"),
        ("classing_office", "MEMPHIS"),
        ("warehouse", "MW14"),
        ("base_loan_rate", "52.00"),
    ):
        repos.settings.set(name, value, date(2025, 8, 1))
    assert named(doctor.look(book, SEASON, None, AS_OF))["settings"].is_fine


def test_the_rates_are_named_until_they_are_posted(book: Book) -> None:
    notes = named(doctor.look(book, SEASON, None, AS_OF))
    assert notes["rates"].state == doctor.MISSING
    Repositories(book.connection).rates.post(SEASON, default_terms(), date(2025, 8, 1))
    assert named(doctor.look(book, SEASON, None, AS_OF))["rates"].is_fine


def test_an_empty_season_has_nothing_outstanding(book: Book) -> None:
    assert named(doctor.look(book, SEASON, None, AS_OF))["season"].is_fine
    assert named(doctor.look(book, SEASON, None, AS_OF))["bales"].is_fine


def test_the_file_is_looked_at_when_there_is_one(tmp_path: Path) -> None:
    path = tmp_path / "season.sqlite3"
    with Book.open(path) as opened:
        notes = named(doctor.look(opened, SEASON, path, AS_OF))
    assert notes["file"].is_fine
    assert "tables" in notes["file"].detail


def test_a_file_that_is_not_there_is_not_looked_at(book: Book, tmp_path: Path) -> None:
    notes = named(doctor.look(book, SEASON, tmp_path / "none.sqlite3", AS_OF))
    assert "file" not in notes


def test_an_old_schema_reads_as_wrong(book: Book) -> None:
    book.connection.execute("PRAGMA user_version = 1")
    notes = named(doctor.look(book, SEASON, None, AS_OF))
    assert notes["schema"].state == doctor.WRONG
    assert not doctor.is_sound(list(notes.values()))
    assert doctor.worst(list(notes.values())) == doctor.WRONG


def test_a_note_prints_its_line():
    assert str(doctor.Note("schema", doctor.FINE, "at 10")) == "fine    schema: at 10"


def test_everything_fine_reads_fine():
    notes = [doctor.Note("a", doctor.FINE, "ok"), doctor.Note("b", doctor.FINE, "ok")]
    assert doctor.worst(notes) == doctor.FINE
    assert doctor.is_sound(notes)


def test_the_store_is_looked_at_as_at_the_date(book: Book) -> None:
    from datetime import date as day
    from decimal import Decimal

    from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId
    from moteroom.core.weight import Weight
    from moteroom.ginning.run import GinRun
    from moteroom.press.bale import Bale
    from moteroom.receiving.party import Producer
    from moteroom.receiving.ticket import ModuleTicket
    from moteroom.warehouse.receipt import Receipt

    repos = Repositories(book.connection)
    lot = LotId(SEASON, 1)
    repos.producers.add(Producer("BLYTHE", "Blythe Farms"))
    repos.tickets.add(
        ModuleTicket(
            number=1,
            module=ModuleId("HW-004181"),
            producer="BLYTHE",
            farm="3312",
            weighed_on=day(2025, 10, 14),
            gross=Weight(38_400),
            tare=Weight(17_200),
            moisture=Decimal("9.4"),
        )
    )
    repos.lots.add(
        GinRun(
            lot=lot,
            ginned_on=day(2025, 10, 16),
            tickets=(1,),
            seed_cotton=Weight(21_200),
            lint=Weight(7_400),
            seed=Weight(11_800),
            motes=Weight(1_300),
        )
    )
    tag = BaleId.build(SEASON, GinCode("41207"), 1)
    repos.bales.add(
        Bale(
            bale_id=tag,
            lot=lot,
            pressed_on=day(2025, 10, 16),
            gross=Weight(538),
            tare=Weight(23),
            moisture=Decimal("6.4"),
        )
    )
    repos.receipts.issue(
        Receipt(
            number="MW00000001",
            warehouse="MW14",
            bale_id=tag,
            received_on=day(2025, 10, 20),
            net=Weight(515),
            holder="BLYTHE",
        )
    )
    assert "1 bales in store" in named(doctor.look(book, SEASON, None, AS_OF))["store"].detail
    early = named(doctor.look(book, SEASON, None, day(2025, 10, 1)))
    assert early["store"].detail == "nothing in store"


def test_an_empty_store_reads_as_nothing(book: Book) -> None:
    assert named(doctor.look(book, SEASON, None, AS_OF))["store"].detail == "nothing in store"
