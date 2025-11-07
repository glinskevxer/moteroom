"""A whole season walked end to end through the command line.

Every other test proves one thing about one module. This one proves the
pieces still fit: that the lint the plant made is the lint the producers were
paid on, that a bale delivered against a contract is the same bale the
warehouse receipted, and that the totals on the last page came from the
tickets on the first.
"""

from pathlib import Path

import pytest

from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from tests.conftest import Run

GIN = GinCode("41207")
SEASON = Season(2025)

PRODUCERS = (("BLYTHE", "Blythe Farms"), ("MERRITT", "Merritt Land"))
MODULES = (
    ("HW-004181", "BLYTHE", "38400", "17200", "7.5"),
    ("HW-004182", "BLYTHE", "39100", "17200", "8.2"),
    ("HW-004183", "MERRITT", "37600", "17200", "12.4"),
    ("HW-004184", "MERRITT", "38900", "17200", "9.1"),
)


def tag(number: int) -> str:
    return str(BaleId.build(SEASON, GIN, number))


def card_line(bale: str, colour: str = "31", leaf: str = "3", tail: str = "        ") -> str:
    return f"{bale}20251022MEMPHIS 04336294812{colour}{leaf}042{tail}"


def transfer(*body: str) -> str:
    head = f"HDRMEMPHIS 20251022{len(body):06d}"
    return "\n".join([head, *body, f"TRL{len(body):06d}"])


@pytest.fixture()
def season(run: Run, tmp_path: Path) -> Run:
    run("init")
    for name, value in (
        ("gin_code", "41207"),
        ("classing_office", "MEMPHIS"),
        ("warehouse", "MW14"),
        ("base_loan_rate", "52.00"),
    ):
        run("setting", "set", name, value)
    for code, name in PRODUCERS:
        run("producer", "add", code, name)
        run("producer", "farm", code, "3312", "1140", "284.50")
    for module, producer, gross, tare, moisture in MODULES:
        run(
            "ticket",
            "weigh",
            module,
            producer,
            "3312",
            gross,
            tare,
            "--moisture",
            moisture,
            "--on",
            "2025-10-14",
        )
    return run


def test_the_yard_puts_the_wet_module_first(season):
    listed = season("ticket", "yard", "--as-of", "2025-10-15")
    assert listed.output.index("HW-004183") < listed.output.index("HW-004181")
    assert "wet" in listed.output


def test_the_season_walks_from_the_scale_to_the_settlement(season, tmp_path):
    ginned = season(
        "lot",
        "gin",
        "1,2,3,4",
        "--lint",
        "29800",
        "--seed",
        "47200",
        "--motes",
        "5200",
        "--on",
        "2025-10-16",
    )
    assert ginned.exit_code == 0
    assert "85,200 lb" in ginned.output

    for _ in range(58):
        assert season("bale", "press", "1", "538", "--on", "2025-10-16").exit_code == 0
    season("lot", "close", "1")

    sheet = season("report", "daily", "--on", "2025-10-16")
    assert "58 bales" in sheet.output

    lines = [card_line(tag(number)) for number in range(1, 59)]
    path = tmp_path / "transfer.txt"
    path.write_text(transfer(*lines), encoding="utf-8")
    loaded = season("card", "load", str(path))
    assert "loaded 58 of 58" in loaded.output
    assert "0 waiting" in season("card", "waiting").output

    priced = season("loan", "pool")
    assert "bales         58" in priced.output

    season("settle", "rates")
    first = season("settle", "run", "BLYTHE", "--on", "2026-02-03")
    second = season("settle", "run", "MERRITT", "--on", "2026-02-03")
    assert first.exit_code == 0
    assert second.exit_code == 0
    summary = season("report", "settlements")
    assert "2 producers" in summary.output
    assert "58 bales" in summary.output
    assert "0 of 2" in season("report", "outstanding").output


def test_the_lint_paid_on_is_the_lint_the_plant_made(season):
    season(
        "lot",
        "gin",
        "1,2",
        "--lint",
        "14900",
        "--seed",
        "23600",
        "--motes",
        "2600",
        "--on",
        "2025-10-16",
    )
    season(
        "lot",
        "gin",
        "3,4",
        "--lint",
        "14900",
        "--seed",
        "23600",
        "--motes",
        "2600",
        "--on",
        "2025-10-17",
    )
    for lot in ("1", "2"):
        for _ in range(29):
            season("bale", "press", lot, "538", "--on", "2025-10-17")
    season("settle", "rates")
    season("settle", "run", "BLYTHE", "--on", "2026-02-03")
    season("settle", "run", "MERRITT", "--on", "2026-02-03")
    summary = season("report", "settlements", "--csv")
    rows = [line.split(",") for line in summary.output.splitlines()[1:] if line.strip()]
    assert sum(int(row[2]) for row in rows) == 29_800
    assert sum(int(row[1]) for row in rows) == 58


def test_a_bale_moves_from_the_press_to_a_receipt_to_a_contract(season, tmp_path):
    season(
        "lot",
        "gin",
        "1,2,3,4",
        "--lint",
        "29800",
        "--seed",
        "47200",
        "--motes",
        "5200",
        "--on",
        "2025-10-16",
    )
    season("bale", "press", "1", "538", "--on", "2025-10-16")
    path = tmp_path / "transfer.txt"
    path.write_text(transfer(card_line(tag(1))), encoding="utf-8")
    season("card", "load", str(path))

    season("receipt", "issue", tag(1), "MW00000001", "--holder", "BLYTHE", "--on", "2025-10-20")
    assert "1 outstanding" in season("receipt", "list").output

    season(
        "contract",
        "write",
        "C000141",
        "CALCOT",
        "1",
        "--price",
        "68.50",
        "--signed",
        "2025-08-02",
        "--opens",
        "2025-11-01",
        "--closes",
        "2026-01-31",
    )
    delivered = season("contract", "deliver", "C000141", tag(1), "--on", "2025-12-01")
    assert delivered.exit_code == 0
    assert "C000141" in season("contract", "list").output

    season("order", "write", "SO000141", "CALCOT", "MW00000001", "--on", "2026-01-12")
    shown = season("order", "show", "SO000141")
    assert "515 lb" in shown.output

    season("receipt", "release", "MW00000001", "CALCOT", "--on", "2026-01-13")
    assert "(nothing)" in season("receipt", "list").output


def test_a_correction_at_the_scale_carries_all_the_way_through(season):
    season("ticket", "correct", "1", "39000", "17200")
    listed = season("ticket", "list")
    assert listed.output.count("HW-004181") == 1
    ginned = season(
        "lot",
        "gin",
        "2,3,4,5",
        "--lint",
        "29800",
        "--seed",
        "47200",
        "--motes",
        "5200",
        "--on",
        "2025-10-16",
    )
    assert ginned.exit_code == 0
    assert "85,800 lb" in ginned.output
    assert season("lot", "gin", "1", "--lint", "7000", "--seed", "11000").exit_code != 0


def test_the_book_survives_being_closed_and_reopened(season):
    season(
        "lot",
        "gin",
        "1,2",
        "--lint",
        "14900",
        "--seed",
        "23600",
        "--motes",
        "2600",
        "--on",
        "2025-10-16",
    )
    season("bale", "press", "1", "538", "--on", "2025-10-16")
    about = season("about")
    assert "tickets" in about.output
    assert "bales" in about.output
    reopened = season("lot", "show", "1")
    assert "2025-0001" in reopened.output
    assert "1" in reopened.output
