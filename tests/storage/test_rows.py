import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import CentsPerPound, Money
from moteroom.core.weight import Weight
from moteroom.storage import rows as read


def row(**values: object) -> sqlite3.Row:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    connection.execute(f"CREATE TABLE thing ({', '.join(values)})")
    connection.execute(f"INSERT INTO thing ({names}) VALUES ({marks})", tuple(values.values()))
    made: sqlite3.Row = connection.execute("SELECT * FROM thing").fetchone()
    connection.close()
    return made


def test_text_and_number_read_back():
    made = row(name="BLYTHE", count=42)
    assert read.text(made, "name") == "BLYTHE"
    assert read.number(made, "count") == 42


def test_a_null_where_something_is_needed_is_refused():
    made = row(name=None)
    with pytest.raises(ValidationError) as caught:
        read.text(made, "name")
    assert caught.value.field == "name"


def test_money_and_a_rate_read_back_exactly():
    made = row(amount="1234.56", cents="52.34")
    assert read.money(made, "amount") == Money.parse("1234.56")
    assert read.rate(made, "cents") == CentsPerPound.of("52.34")


def test_money_that_is_not_money_names_the_column():
    made = row(amount="cotton")
    with pytest.raises(ValidationError) as caught:
        read.money(made, "amount")
    assert caught.value.field == "amount"
    with pytest.raises(ValidationError):
        read.rate(row(cents="cotton"), "cents")


def test_a_weight_reads_back_in_pounds():
    assert read.weight(row(net=515), "net") == Weight(515)


def test_a_date_reads_back_and_junk_is_refused():
    assert read.day(row(sold_on="2025-10-14"), "sold_on") == date(2025, 10, 14)
    with pytest.raises(ValidationError):
        read.day(row(sold_on="the fourteenth"), "sold_on")


def test_a_nullable_date_is_allowed_to_be_missing():
    assert read.maybe_day(row(sold_on=None), "sold_on") is None
    assert read.maybe_day(row(sold_on="2025-10-14"), "sold_on") == date(2025, 10, 14)


def test_nullable_money_and_a_nullable_rate():
    assert read.maybe_money(row(amount=None), "amount") is None
    assert read.maybe_money(row(amount="1.00"), "amount") == Money.parse("1.00")
    assert read.maybe_rate(row(cents=None), "cents") is None
    assert read.maybe_rate(row(cents="52.00"), "cents") == CentsPerPound.of("52.00")


def test_a_flag_reads_as_a_yes_or_a_no():
    assert read.flag(row(electronic=1), "electronic")
    assert not read.flag(row(electronic=0), "electronic")


def test_an_exact_decimal_survives_the_round_trip():
    assert read.money(row(amount="0.05"), "amount").amount == Decimal("0.05")
