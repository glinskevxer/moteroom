from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.ids import ModuleId
from moteroom.core.weight import Weight
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.storage.book import Book
from moteroom.storage.maintenance import compact, measure, table_sizes
from moteroom.storage.registry import Repositories


def filled(path: Path, tickets: int) -> Book:
    book = Book.open(path)
    repos = Repositories(book.connection)
    repos.producers.add(Producer("BLYTHE", "Blythe Farms"))
    for number in range(1, tickets + 1):
        repos.tickets.add(
            ModuleTicket(
                number=number,
                module=ModuleId(f"HW-{number:06d}"),
                producer="BLYTHE",
                farm="3312",
                weighed_on=date(2025, 10, 14),
                gross=Weight(38_400),
                tare=Weight(17_200),
                moisture=Decimal("9.4"),
            )
        )
    book.connection.commit()
    return book


def test_a_book_reports_its_size(tmp_path):
    path = tmp_path / "season.sqlite3"
    book = filled(path, 20)
    size = measure(book, path)
    assert size.bytes > 0
    assert size.pages > 0
    assert size.page_size in (512, 1024, 2048, 4096, 8192, 16384, 32768, 65536)
    assert str(size).endswith("pages free")
    book.close()


def test_a_size_reads_the_way_somebody_says_it(tmp_path):
    path = tmp_path / "season.sqlite3"
    book = filled(path, 1)
    size = measure(book, path)
    assert size.reads().endswith(("bytes", "kB", "MB"))
    book.close()


def test_measuring_a_book_that_is_not_there(tmp_path):
    path = tmp_path / "season.sqlite3"
    book = filled(path, 1)
    with pytest.raises(ValidationError):
        measure(book, tmp_path / "none.sqlite3")
    book.close()


def test_a_fresh_book_is_not_worth_compacting(tmp_path):
    path = tmp_path / "season.sqlite3"
    book = filled(path, 5)
    assert not measure(book, path).worth_compacting
    book.close()


def test_compacting_hands_the_free_pages_back(tmp_path):
    path = tmp_path / "season.sqlite3"
    book = filled(path, 400)
    book.connection.execute("DELETE FROM tickets")
    book.connection.commit()
    before = measure(book, path)
    assert before.worth_compacting
    _, after = compact(book, path)
    assert after.free_pages == 0
    assert after.bytes <= before.bytes
    book.close()


def test_compacting_keeps_the_rows_that_are_left(tmp_path):
    path = tmp_path / "season.sqlite3"
    book = filled(path, 40)
    compact(book, path)
    assert book.count("tickets") == 40
    book.close()


def test_the_tables_report_biggest_first(tmp_path):
    path = tmp_path / "season.sqlite3"
    book = filled(path, 12)
    sizes = table_sizes(book)
    assert list(sizes)[0] == "tickets"
    assert sizes["tickets"] == 12
    assert sizes["bales"] == 0
    book.close()
