from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.press.bale import Bale
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.service.export import reports, write
from moteroom.storage.book import Book
from moteroom.storage.registry import Repositories

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 1)
AS_OF = date(2026, 2, 3)


@pytest.fixture()
def book():
    with Book.open() as opened:
        repos = Repositories(opened.connection)
        repos.producers.add(Producer("BLYTHE", "Blythe Farms"))
        repos.tickets.add(
            ModuleTicket(
                number=1,
                module=ModuleId("HW-004181"),
                producer="BLYTHE",
                farm="3312",
                weighed_on=date(2025, 10, 14),
                gross=Weight(38_400),
                tare=Weight(17_200),
                moisture=Decimal("9.4"),
            )
        )
        repos.lots.add(
            GinRun(
                lot=LOT,
                ginned_on=date(2025, 10, 16),
                tickets=(1,),
                seed_cotton=Weight(21_200),
                lint=Weight(7_400),
                seed=Weight(11_800),
                motes=Weight(1_300),
            )
        )
        repos.bales.add(
            Bale(
                bale_id=BaleId.build(SEASON, GIN, 1),
                lot=LOT,
                pressed_on=date(2025, 10, 16),
                gross=Weight(538),
                tare=Weight(23),
                moisture=Decimal("6.4"),
            )
        )
        yield opened


def test_the_reports_cover_what_the_season_holds(book: Book) -> None:
    made = reports(book, SEASON, AS_OF)
    assert "colour" in made
    assert "settlements" in made
    assert "gin-sheet-2025-10-16" in made


def test_an_export_writes_a_folder_named_for_the_season(book: Book, tmp_path: Path) -> None:
    made = write(book, SEASON, tmp_path, AS_OF)
    assert made.folder.name == "moteroom-2025"
    assert made.count > 8
    assert "colour.csv" in made.files
    assert "season.txt" in made.files
    assert str(made).endswith("moteroom-2025")


def test_every_file_written_reads_back_as_csv(book: Book, tmp_path: Path) -> None:
    made = write(book, SEASON, tmp_path, AS_OF)
    for name in made.files:
        text = (made.folder / name).read_text(encoding="utf-8")
        assert text.strip()
        if name.endswith(".csv"):
            assert "," in text.splitlines()[0]


def test_the_summary_carries_the_season_totals(book: Book, tmp_path: Path) -> None:
    made = write(book, SEASON, tmp_path, AS_OF)
    text = (made.folder / "season.txt").read_text(encoding="utf-8")
    assert "moteroom export for 2025/26" in text
    assert "seed cotton  21,200 lb" in text
    assert "bales        1" in text


def test_an_export_will_not_write_over_another(book: Book, tmp_path: Path) -> None:
    write(book, SEASON, tmp_path, AS_OF)
    with pytest.raises(ValidationError):
        write(book, SEASON, tmp_path, AS_OF)


def test_two_seasons_export_side_by_side(book: Book, tmp_path: Path) -> None:
    first = write(book, SEASON, tmp_path, AS_OF)
    second = write(book, Season(2026), tmp_path, AS_OF)
    assert first.folder != second.folder
    assert second.folder.exists()


def test_a_statement_gets_its_own_page(book: Book, tmp_path: Path) -> None:
    from moteroom.core.money import Money
    from moteroom.settlement.statement import Statement

    Repositories(book.connection).statements.save(
        Statement(
            producer="BLYTHE",
            season=SEASON,
            bales=1,
            lint=Weight(515),
            lint_proceeds=Money.parse("267.80"),
            gin_charges=Money.parse("100.00"),
            seed_credit=Money.parse("50.00"),
        ),
        AS_OF,
    )
    made = write(book, SEASON, tmp_path, AS_OF)
    assert "statement-blythe.csv" in made.files
