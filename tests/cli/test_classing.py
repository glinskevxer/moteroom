from pathlib import Path

import pytest

from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from tests.conftest import Run

GIN = GinCode("41207")
SEASON = Season(2025)


def tag(number: int) -> str:
    return str(BaleId.build(SEASON, GIN, number))


def line(bale: str, tail: str = "        ") -> str:
    return f"{bale}20251022MEMPHIS 04336294812313042{tail}"


def transfer(*body: str) -> str:
    head = f"HDRMEMPHIS 20251022{len(body):06d}"
    return "\n".join([head, *body, f"TRL{len(body):06d}"])


@pytest.fixture()
def classed(run: Run, tmp_path: Path) -> Run:
    run("setting", "set", "gin_code", "41207")
    run("producer", "add", "BLYTHE", "Blythe Farms")
    run(
        "ticket", "weigh", "HW-004181", "BLYTHE", "3312", "38400", "17200", "--on", "2025-10-14"
    )
    run("lot", "gin", "1", "--lint", "7400", "--seed", "11800", "--motes", "1300")
    for gross in ("538", "548"):
        run("bale", "press", "1", gross, "--on", "2025-10-16")
    return run


def write(tmp_path: Path, text: str, name: str = "transfer.txt") -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_a_transfer_loads(classed, tmp_path):
    path = write(tmp_path, transfer(line(tag(1)), line(tag(2))))
    result = classed("card", "load", path)
    assert result.exit_code == 0
    assert "loaded 2 of 2" in result.output
    assert "MEMPHIS" in result.output


def test_a_bad_line_is_reported_and_the_rest_loads(classed, tmp_path):
    path = write(tmp_path, transfer(line(tag(1)), "junk"))
    result = classed("card", "load", path)
    assert "loaded 1 of 2" in result.output
    assert "rejected line 3" in result.output


def test_a_card_for_a_bale_from_another_gin_is_skipped(classed, tmp_path):
    other = str(BaleId.build(SEASON, GinCode("41208"), 1))
    path = write(tmp_path, transfer(line(other)))
    result = classed("card", "load", path)
    assert "no such bale here" in result.output


def test_loading_the_same_card_twice_skips_it(classed, tmp_path):
    path = write(tmp_path, transfer(line(tag(1))))
    classed("card", "load", path)
    result = classed("card", "load", path)
    assert "already classed" in result.output


def test_a_file_that_is_not_there(classed, tmp_path):
    assert classed("card", "load", str(tmp_path / "missing.txt")).exit_code != 0


def test_a_file_with_no_header(classed, tmp_path):
    path = write(tmp_path, line(tag(1)))
    assert classed("card", "load", path).exit_code != 0


def test_a_card_shows_what_the_office_said(classed, tmp_path):
    classed("card", "load", write(tmp_path, transfer(line(tag(1)))))
    shown = classed("card", "show", tag(1))
    assert "middling white" in shown.output
    assert "1.13 in" in shown.output
    assert "findings    none" in shown.output


def test_a_card_nobody_filed(classed):
    assert classed("card", "show", tag(1)).exit_code != 0


def test_the_list_shows_the_grades(classed, tmp_path):
    classed("card", "load", write(tmp_path, transfer(line(tag(1), "B2      "))))
    listed = classed("card", "list")
    assert "31" in listed.output
    assert "B2" in listed.output


def test_waiting_counts_the_bales_with_no_card(classed, tmp_path):
    assert "2 waiting" in classed("card", "waiting").output
    classed("card", "load", write(tmp_path, transfer(line(tag(1)))))
    assert "1 waiting" in classed("card", "waiting").output


def test_a_correction_replaces_a_card(classed, tmp_path):
    classed("card", "load", write(tmp_path, transfer(line(tag(1)))))
    fixed = line(tag(1)).replace("313042", "415042", 1)
    result = classed("card", "correct", write(tmp_path, transfer(fixed), "fix.txt"))
    assert result.exit_code == 0
    assert "replaced 1" in result.output
    assert "41" in classed("card", "show", tag(1)).output


def test_a_correction_for_a_card_nobody_filed(classed, tmp_path):
    path = write(tmp_path, transfer(line(tag(1))))
    assert classed("card", "correct", path).exit_code != 0


def test_a_correction_file_has_to_read_cleanly(classed, tmp_path):
    classed("card", "load", write(tmp_path, transfer(line(tag(1)))))
    path = write(tmp_path, transfer(line(tag(1)), "junk"), "fix.txt")
    assert classed("card", "correct", path).exit_code != 0


def test_a_reclass_writes_the_office_a_request(classed, tmp_path):
    classed("card", "load", write(tmp_path, transfer(line(tag(1)))))
    made = classed(
        "card",
        "reclass",
        tag(1),
        "--reason",
        "producer disputes the leaf",
        "--by",
        "BLYTHE",
        "--on",
        "2025-11-03",
    )
    assert made.exit_code == 0
    assert made.output.splitlines()[0].startswith("RCLHDR")
    assert "disputes" in made.output


def test_a_reclass_can_be_written_to_a_file(classed, tmp_path):
    classed("card", "load", write(tmp_path, transfer(line(tag(1)))))
    out = tmp_path / "requests.txt"
    made = classed(
        "card",
        "reclass",
        tag(1),
        "--reason",
        "leaf",
        "--by",
        "BLYTHE",
        "--out",
        str(out),
        "--on",
        "2025-11-03",
    )
    assert "1 bales back to" in made.output
    assert str(tag(1)) in out.read_text()


def test_a_reclass_of_a_bale_with_no_card(classed):
    assert (
        classed("card", "reclass", tag(1), "--reason", "leaf", "--by", "BLYTHE").exit_code != 0
    )


def test_a_reclass_naming_nothing(classed):
    assert classed("card", "reclass", "--reason", "leaf", "--by", "BLYTHE").exit_code != 0


ASSIGNED = "micronaire=4.3,strength=29.4,uniformity=81.2,length=1.1"


def test_a_calibration_check_reads_off_the_standard(classed):
    made = classed(
        "card", "calibrate", "sc-114", ASSIGNED, "--assigned", ASSIGNED, "--on", "2025-10-14"
    )
    assert made.exit_code == 0
    assert "passed" in made.output
    assert "+0.0" in made.output


def test_a_line_outside_tolerance_says_which_measure(classed):
    readings = "micronaire=4.6,strength=29.4,uniformity=81.2,length=1.1"
    made = classed(
        "card", "calibrate", "SC-114", readings, "--assigned", ASSIGNED, "--on", "2025-10-14"
    )
    assert "out on micronaire" in made.output
    assert "out" in made.output


def test_a_reading_that_will_not_read(classed):
    readings = "micronaire=high,strength=29.4,uniformity=81.2,length=1.1"
    assert (
        classed("card", "calibrate", "SC-114", readings, "--assigned", ASSIGNED).exit_code != 0
    )


def test_a_pair_that_is_not_a_pair(classed):
    assert (
        classed("card", "calibrate", "SC-114", "micronaire", "--assigned", ASSIGNED).exit_code
        != 0
    )


def test_a_standard_missing_a_measure(classed):
    assert (
        classed(
            "card", "calibrate", "SC-114", ASSIGNED, "--assigned", "micronaire=4.3"
        ).exit_code
        != 0
    )


def test_a_bale_is_sampled_both_sides(classed):
    made = classed("card", "sample", tag(1), "--by", "talley", "--on", "2025-10-18")
    assert made.exit_code == 0
    assert "side a  100g" in made.output
    assert "enough  yes" in made.output


def test_a_bale_nobody_pressed_cannot_be_sampled(classed):
    assert classed("card", "sample", tag(9), "--by", "TALLEY").exit_code != 0


def test_a_cut_off_the_scale_is_refused(classed):
    assert classed("card", "sample", tag(1), "--by", "TALLEY", "--grams", "20").exit_code != 0
