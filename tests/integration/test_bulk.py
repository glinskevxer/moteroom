"""A file the size the office actually sends.

Every other test loads two cards. The office sends four hundred at a time, and
the things that break at four hundred are not the things that break at two:
one statement per row, a transaction held open across the whole file, a lookup
inside the loop that walks the table again for every line.

The bales are pressed straight into the book rather than through the command
line, because three hundred command invocations is a test that measures the
test harness.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from moteroom.core.ids import BaleId, GinCode, LotId, ModuleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.ginning.run import GinRun
from moteroom.press.bale import Bale
from moteroom.receiving.party import Producer
from moteroom.receiving.ticket import ModuleTicket
from moteroom.storage.book import Book
from moteroom.storage.registry import Repositories
from tests.conftest import Run

GIN = GinCode("41207")
SEASON = Season(2025)
LOT = LotId(SEASON, 1)
COUNT = 300


def tag(number: int) -> str:
    return str(BaleId.build(SEASON, GIN, number))


def card_line(bale: str) -> str:
    return f"{bale}20251022MEMPHIS 04336294812313042        "


def transfer(count: int) -> str:
    body = [card_line(tag(number)) for number in range(1, count + 1)]
    return "\n".join([f"HDRMEMPHIS 20251022{count:06d}", *body, f"TRL{count:06d}"])


def part(count: int, extra: list[str]) -> str:
    body = [card_line(tag(number)) for number in range(1, count + 1)] + extra
    return "\n".join([f"HDRMEMPHIS 20251022{len(body):06d}", *body, f"TRL{len(body):06d}"])


@pytest.fixture()
def pressed(run: Run, book: str) -> Run:
    with Book.open(book) as opened:
        repos = Repositories(opened.connection)
        repos.settings.set("gin_code", "41207", date(2025, 8, 1))
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
        for number in range(1, COUNT + 1):
            repos.bales.add(
                Bale(
                    bale_id=BaleId.build(SEASON, GIN, number),
                    lot=LOT,
                    pressed_on=date(2025, 10, 16),
                    gross=Weight(538),
                    tare=Weight(23),
                    moisture=Decimal("6.4"),
                )
            )
        opened.connection.commit()
    return run


def written(tmp_path: Path, text: str, name: str = "transfer.txt") -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_three_hundred_bales_are_in_the_book(pressed: Run) -> None:
    listed = pressed("bale", "list")
    assert f"{COUNT} bales" in listed.output
    assert tag(COUNT) in listed.output


def test_a_three_hundred_card_transfer_loads_in_one_pass(pressed: Run, tmp_path: Path) -> None:
    made = pressed("card", "load", written(tmp_path, transfer(COUNT)))
    assert made.exit_code == 0
    assert f"loaded {COUNT} of {COUNT}" in made.output
    assert "0 waiting" in pressed("card", "waiting").output


def test_a_file_that_fails_partway_files_none_of_it(pressed: Run, tmp_path: Path) -> None:
    made = pressed("card", "load", written(tmp_path, part(5, [card_line(tag(1))]), "twice.txt"))
    assert made.exit_code != 0
    assert f"{COUNT} waiting" in pressed("card", "waiting").output


def test_the_pool_prices_three_hundred_bales(pressed: Run, tmp_path: Path) -> None:
    pressed("card", "load", written(tmp_path, transfer(COUNT)))
    priced = pressed("loan", "pool")
    assert f"bales         {COUNT}" in priced.output
    assert "average rate" in priced.output


def test_the_reports_still_read_at_that_size(pressed: Run, tmp_path: Path) -> None:
    pressed("card", "load", written(tmp_path, transfer(COUNT)))
    assert f"{COUNT} cards" in pressed("report", "quality", "--kind", "averages").output
    assert f"{COUNT} at the gin" in pressed("report", "inventory").output


def test_the_whole_file_is_one_line_in_the_trail(pressed: Run, tmp_path: Path) -> None:
    pressed("card", "load", written(tmp_path, transfer(COUNT)))
    assert "(nothing)" in pressed("audit", "list").output


def test_the_book_stays_one_file_and_verifies(pressed: Run, tmp_path: Path, book: str) -> None:
    pressed("card", "load", written(tmp_path, transfer(COUNT)))
    assert "is sound" in pressed("verify").output
    connection = sqlite3.connect(book)
    try:
        rows = connection.execute("SELECT count(*) FROM cards").fetchone()
    finally:
        connection.close()
    assert rows[0] == COUNT
