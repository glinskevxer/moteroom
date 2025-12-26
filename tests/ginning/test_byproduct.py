from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from moteroom.core.errors import ValidationError
from moteroom.core.money import Money
from moteroom.core.weight import Weight
from moteroom.ginning.byproduct import MOTES, TRASH, ByproductLedger, Sale

DAY = date(2025, 11, 4)


def sale(**overrides: Any) -> Sale:
    fields: dict[str, Any] = {
        "kind": MOTES,
        "sold_on": DAY,
        "weight": Weight(24_000),
        "price_per_ton": Money.parse("180.00"),
        "buyer": "MILL",
    }
    fields.update(overrides)
    return Sale(**fields)


def test_a_load_is_priced_by_the_ton():
    assert sale().tons == Decimal("12.000")
    assert sale().proceeds == Money.parse("2160.00")
    assert not sale().is_disposal


def test_a_load_that_cost_money_to_shift():
    made = sale(kind=TRASH, price_per_ton=Money.parse("-22.50"))
    assert made.is_disposal
    assert made.proceeds == Money.parse("-270.00")
    assert "cost" in str(made)


@pytest.mark.parametrize("kind", ["", "lint", "MOTES"])
def test_a_kind_the_plant_does_not_sell(kind):
    with pytest.raises(ValidationError):
        sale(kind=kind)


def test_a_load_names_a_buyer_and_weighs_something():
    with pytest.raises(ValidationError):
        sale(buyer="  ")
    with pytest.raises(ValidationError):
        sale(weight=Weight.zero())


def test_the_ledger_totals_by_kind():
    ledger = ByproductLedger()
    ledger.extend([sale(), sale(kind=TRASH, price_per_ton=Money.parse("-22.50"))])
    assert ledger.weight() == Weight(48_000)
    assert ledger.weight(MOTES) == Weight(24_000)
    assert ledger.proceeds() == Money.parse("1890.00")
    assert ledger.by_kind() == {MOTES: Money.parse("2160.00"), TRASH: Money.parse("-270.00")}


def test_the_ledger_picks_out_what_cost_money():
    ledger = ByproductLedger()
    ledger.extend([sale(), sale(kind=TRASH, price_per_ton=Money.parse("-22.50"))])
    assert [one.kind for one in ledger.disposals()] == [TRASH]
    assert len(ledger) == 2


def test_sales_come_back_oldest_first():
    ledger = ByproductLedger()
    ledger.extend([sale(sold_on=date(2025, 12, 1)), sale(sold_on=DAY)])
    assert [one.sold_on for one in ledger.sales()] == [DAY, date(2025, 12, 1)]


def test_an_empty_ledger_totals_nothing():
    ledger = ByproductLedger()
    assert ledger.proceeds().is_zero
    assert ledger.weight().is_zero
    assert ledger.by_kind() == {}


def test_the_proceeds_share_out_on_ginned_volume():
    ledger = ByproductLedger()
    ledger.sell(sale())
    parts = ledger.allocate({"BLYTHE": Weight(42_400), "MERRITT": Weight(21_200)})
    assert parts["BLYTHE"] == Money.parse("1440.00")
    assert parts["MERRITT"] == Money.parse("720.00")


def test_a_disposal_shares_out_as_a_charge():
    ledger = ByproductLedger()
    ledger.sell(sale(kind=TRASH, price_per_ton=Money.parse("-22.50")))
    parts = ledger.allocate({"BLYTHE": Weight(1), "MERRITT": Weight(1)})
    assert parts["BLYTHE"].amount < 0


def test_allocating_with_nobody_ginning():
    ledger = ByproductLedger()
    ledger.sell(sale())
    with pytest.raises(ValidationError):
        ledger.allocate({})
    with pytest.raises(ValidationError):
        ledger.allocate({"BLYTHE": Weight.zero()})
