from datetime import date
from typing import Any

import pytest

from moteroom.core.errors import MoteroomError, ValidationError
from moteroom.core.ids import BaleId, GinCode
from moteroom.core.season import Season
from moteroom.core.weight import Weight
from moteroom.warehouse.ewr import (
    Acknowledgement,
    parse_acknowledgement,
    render_transfer,
    transfer_weight,
)
from moteroom.warehouse.receipt import Receipt

GIN = GinCode("41207")
SEASON = Season(2025)
DAY = date(2026, 1, 12)


def receipt(number: int, **overrides: Any) -> Receipt:
    fields: dict[str, Any] = {
        "number": f"MW{number:08d}",
        "warehouse": "MW14",
        "bale_id": BaleId.build(SEASON, GIN, number),
        "received_on": date(2025, 10, 20),
        "net": Weight(515),
        "holder": "BLYTHE",
    }
    fields.update(overrides)
    return Receipt(**fields)


def answer(*body: str) -> str:
    head = f"EWRHDR{'EWRCO ':<6}20260112{len(body):06d}"
    return "\n".join([head, *body, f"EWRTRL{len(body):06d}"])


def test_a_transfer_lays_out_a_line_per_receipt():
    text = render_transfer([receipt(1), receipt(2)], "EWRCO", DAY, "CALCOT")
    lines = text.splitlines()
    assert lines[0].startswith("EWRHDR")
    assert lines[0].endswith("000002")
    assert len(lines[1]) == 53
    assert lines[1][:10] == "MW00000001"
    assert lines[1][30:40] == "CALCOT    "
    assert lines[1][40:45] == "00515"
    assert lines[-1] == "EWRTRL000002"


def test_a_transfer_has_to_move_something():
    with pytest.raises(ValidationError):
        render_transfer([], "EWRCO", DAY, "CALCOT")


@pytest.mark.parametrize("provider", ["", "   ", "TOOLONGCODE"])
def test_a_provider_code_has_a_shape(provider):
    with pytest.raises(ValidationError):
        render_transfer([receipt(1)], provider, DAY, "CALCOT")


def test_a_transfer_names_who_it_goes_to():
    with pytest.raises(ValidationError):
        render_transfer([receipt(1)], "EWRCO", DAY, "  ")


def test_a_released_receipt_cannot_transfer():
    released = receipt(1).release(date(2025, 12, 1), "CALCOT")
    with pytest.raises(ValidationError):
        render_transfer([released], "EWRCO", DAY, "CALCOT")


def test_paper_cannot_transfer():
    with pytest.raises(ValidationError) as caught:
        render_transfer([receipt(1, electronic=False)], "EWRCO", DAY, "CALCOT")
    assert "paper" in caught.value.message


def test_a_transfer_weighs_what_it_moves():
    assert transfer_weight([receipt(1), receipt(2)]) == Weight(1_030)
    assert transfer_weight([]).is_zero


def test_an_acknowledgement_reads_back():
    read = parse_acknowledgement(answer("MW00000001A", "MW00000002A"))
    assert read.provider == "EWRCO"
    assert read.answered_on == DAY
    assert read.accepted == ("MW00000001", "MW00000002")
    assert read.is_clean
    assert read.took("MW00000001")


def test_a_rejection_comes_back_with_its_reason():
    read = parse_acknowledgement(answer("MW00000001A", "MW00000002Rholder unknown"))
    assert read.rejected == (("MW00000002", "holder unknown"),)
    assert not read.is_clean
    assert str(read) == "1 accepted, 1 rejected"


def test_a_rejection_with_no_reason_still_says_something():
    read = parse_acknowledgement(answer("MW00000002R"))
    assert read.rejected[0][1] == "no reason given"


def test_a_receipt_the_answer_never_mentions_is_found():
    read = parse_acknowledgement(answer("MW00000001A"))
    assert read.missing(["MW00000001", "MW00000002"]) == ("MW00000002",)
    assert read.missing(["MW00000001"]) == ()


@pytest.mark.parametrize(
    "text",
    ["", "MW00000001A", "EWRHDREWRCO 20260112000001\nMW00000001A"],
)
def test_an_acknowledgement_without_its_wrapper_is_refused(text):
    with pytest.raises(MoteroomError):
        parse_acknowledgement(text)


def test_a_header_that_will_not_read():
    with pytest.raises(MoteroomError):
        parse_acknowledgement("EWRHDREWRCO 2026xx12000000\nEWRTRL000000")


def test_an_answer_nobody_understands():
    with pytest.raises(MoteroomError):
        parse_acknowledgement(answer("MW00000001X"))


def test_a_line_with_no_receipt_number():
    with pytest.raises(MoteroomError):
        parse_acknowledgement(answer("          A"))


def test_a_count_that_disagrees_with_the_lines():
    text = "EWRHDREWRCO 20260112000004\nMW00000001A\nEWRTRL000004"
    with pytest.raises(MoteroomError):
        parse_acknowledgement(text)


def test_an_acknowledgement_compares_by_value():
    made = Acknowledgement("EWRCO", DAY, ("MW00000001",), ())
    assert made == Acknowledgement("EWRCO", DAY, ("MW00000001",), ())
