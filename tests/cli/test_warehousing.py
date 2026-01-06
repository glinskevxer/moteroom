import pytest
from click.testing import Result

from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from tests.conftest import Run

GIN = GinCode("41207")
SEASON = Season(2025)


def tag(number: int) -> str:
    return str(BaleId.build(SEASON, GIN, number))


@pytest.fixture()
def stored(run: Run) -> Run:
    run("setting", "set", "gin_code", "41207")
    run("setting", "set", "warehouse", "MW14")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    for gross in ("538", "548", "528"):
        run("bale", "press", "1", gross, "--on", "2025-10-16")
    return run


def issue(run: Run, number: int, **kwargs: str) -> Result:
    args = ["receipt", "issue", tag(number), f"MW{number:08d}", "--holder", "BLYTHE"]
    for name, value in kwargs.items():
        args.extend([f"--{name}", value])
    return run(*args)


def test_a_receipt_issues_against_a_bale(stored):
    result = issue(stored, 1, on="2025-10-20")
    assert result.exit_code == 0
    assert "MW00000001" in result.output
    assert "MW14" in result.output


def test_a_receipt_for_a_bale_nobody_pressed(stored):
    assert stored("receipt", "issue", tag(9), "MW00000009", "--holder", "BLYTHE").exit_code != 0


def test_a_second_receipt_on_the_same_bale_is_refused(stored):
    issue(stored, 1, on="2025-10-20")
    assert stored("receipt", "issue", tag(1), "MW00000099", "--holder", "BLYTHE").exit_code != 0


def test_issuing_without_a_warehouse_setting(run: Run) -> None:
    run("setting", "set", "gin_code", "41207")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    run("bale", "press", "1", "538", "--on", "2025-10-16")
    assert run("receipt", "issue", tag(1), "MW00000001", "--holder", "BLYTHE").exit_code != 0


def test_a_receipt_releases_once(stored):
    issue(stored, 1, on="2025-10-20")
    released = stored("receipt", "release", "MW00000001", "calcot", "--on", "2026-01-12")
    assert released.exit_code == 0
    assert "CALCOT" in released.output
    assert stored("receipt", "release", "MW00000001", "CALCOT").exit_code != 0


def test_releasing_a_receipt_nobody_issued(stored):
    assert stored("receipt", "release", "MW00000099", "CALCOT").exit_code != 0


def test_the_list_totals_what_is_in_store(stored):
    issue(stored, 1, on="2025-10-20")
    issue(stored, 2, on="2025-10-20")
    listed = stored("receipt", "list")
    assert "2 outstanding" in listed.output
    assert "1,040 lb" in listed.output


def test_the_list_drops_a_released_receipt(stored):
    issue(stored, 1, on="2025-10-20")
    stored("receipt", "release", "MW00000001", "CALCOT", "--on", "2026-01-12")
    assert "(nothing)" in stored("receipt", "list").output


def test_a_paper_receipt_is_flagged(stored):
    stored("receipt", "issue", tag(1), "MW00000001", "--holder", "BLYTHE", "--paper")
    assert "paper" in stored("receipt", "list").output


def test_an_order_writes_against_outstanding_receipts(stored):
    issue(stored, 1, on="2025-10-20")
    issue(stored, 2, on="2025-10-20")
    written = stored(
        "order", "write", "so000141", "calcot", "MW00000001", "MW00000002", "--on", "2026-01-12"
    )
    assert written.exit_code == 0
    assert "2 bales in 1 loads" in written.output


def test_an_order_naming_a_receipt_nobody_issued(stored):
    assert stored("order", "write", "SO000141", "CALCOT", "MW00000009").exit_code != 0


def test_an_order_naming_nothing(stored):
    assert stored("order", "write", "SO000141", "CALCOT").exit_code != 0


def test_an_order_naming_a_released_receipt(stored):
    issue(stored, 1, on="2025-10-20")
    stored("receipt", "release", "MW00000001", "CALCOT", "--on", "2026-01-12")
    assert stored("order", "write", "SO000141", "CALCOT", "MW00000001").exit_code != 0


def test_an_order_shows_its_loads(stored):
    issue(stored, 1, on="2025-10-20")
    stored("order", "write", "SO000141", "CALCOT", "MW00000001", "--on", "2026-01-12")
    shown = stored("order", "show", "so000141")
    assert "loads    1" in shown.output
    assert "515 lb" in shown.output


def test_an_order_nobody_wrote(stored):
    assert stored("order", "show", "SO000141").exit_code != 0


def test_a_transfer_writes_every_outstanding_receipt(stored, tmp_path):
    issue(stored, 1, on="2025-10-20")
    issue(stored, 2, on="2025-10-20")
    made = stored("receipt", "transfer", "calcot", "--on", "2026-01-12")
    assert made.exit_code == 0
    assert made.output.splitlines()[0].startswith("EWRHDR")
    assert "MW00000002" in made.output


def test_a_transfer_can_name_the_receipts_and_a_file(stored, tmp_path):
    issue(stored, 1, on="2025-10-20")
    issue(stored, 2, on="2025-10-20")
    out = tmp_path / "transfer.txt"
    made = stored(
        "receipt", "transfer", "CALCOT", "MW00000001", "--out", str(out), "--on", "2026-01-12"
    )
    assert "1 receipts" in made.output
    assert "MW00000002" not in out.read_text()


def test_a_transfer_with_nothing_in_store(stored):
    assert stored("receipt", "transfer", "CALCOT").exit_code != 0


def test_a_transfer_naming_a_receipt_nobody_issued(stored):
    assert stored("receipt", "transfer", "CALCOT", "MW00000009").exit_code != 0


def test_an_acknowledgement_releases_what_it_accepted(stored, tmp_path):
    issue(stored, 1, on="2025-10-20")
    issue(stored, 2, on="2025-10-20")
    answer = tmp_path / "ack.txt"
    answer.write_text(
        "EWRHDREWRCO 20260112000002\nMW00000001A\nMW00000002Rholder unknown\nEWRTRL000002\n",
        encoding="utf-8",
    )
    made = stored("receipt", "acknowledge", str(answer), "--to", "calcot", "--on", "2026-01-12")
    assert "1 accepted, 1 rejected" in made.output
    assert "holder unknown" in made.output
    assert "MW00000001" not in stored("receipt", "list").output
    assert "MW00000002" in stored("receipt", "list").output


def test_an_acknowledgement_can_be_read_without_releasing(stored, tmp_path):
    issue(stored, 1, on="2025-10-20")
    answer = tmp_path / "ack.txt"
    answer.write_text(
        "EWRHDREWRCO 20260112000001\nMW00000001A\nEWRTRL000001\n", encoding="utf-8"
    )
    stored("receipt", "acknowledge", str(answer))
    assert "MW00000001" in stored("receipt", "list").output


def test_an_acknowledgement_that_will_not_read(stored, tmp_path):
    answer = tmp_path / "ack.txt"
    answer.write_text("nonsense\n", encoding="utf-8")
    assert stored("receipt", "acknowledge", str(answer)).exit_code != 0


def test_a_bale_moves_between_houses(stored):
    issue(stored, 1, on="2025-10-20")
    made = stored("receipt", "move", "MW00000001", "MW15", "MX00000001", "--on", "2026-01-12")
    assert made.exit_code == 0
    assert "in transit" in made.output
    assert "(nothing)" in stored("receipt", "list").output


def test_a_bale_that_arrives_gets_the_second_receipt(stored):
    issue(stored, 1, on="2025-10-20")
    made = stored(
        "receipt",
        "move",
        "MW00000001",
        "MW15",
        "MX00000001",
        "--on",
        "2026-01-12",
        "--arrived",
        "2026-01-14",
    )
    assert "moved MW14 to MW15" in made.output
    listed = stored("receipt", "list")
    assert "MX00000001" in listed.output
    assert "MW15" in listed.output


def test_moving_a_receipt_nobody_issued(stored):
    assert stored("receipt", "move", "MW00000009", "MW15", "MX00000001").exit_code != 0


def test_a_bale_does_not_move_to_the_house_it_is_in(stored):
    issue(stored, 1, on="2025-10-20")
    assert (
        stored(
            "receipt", "move", "MW00000001", "MW14", "MX00000001", "--on", "2026-01-12"
        ).exit_code
        != 0
    )
