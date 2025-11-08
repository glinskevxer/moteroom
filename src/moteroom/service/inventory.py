"""Where every bale actually is.

The press says it made a bale. The warehouse says it holds one. A contract
says one was delivered. Those three lists are kept by three different people
and they disagree, and the disagreements are what this walks: a bale pressed
and never receipted is sitting on the yard, a bale delivered while its receipt
is still outstanding is a receipt somebody forgot to release, and a receipt
against a bale the press never made is a keying error somewhere.
"""

from __future__ import annotations

from dataclasses import dataclass

from moteroom.core.ids import BaleId
from moteroom.core.season import Season
from moteroom.core.weight import Weight, total
from moteroom.storage.book import Book
from moteroom.storage.contracts import ContractRepository
from moteroom.storage.lots import BaleRepository
from moteroom.storage.warehouse import ReceiptRepository

AT_THE_GIN = "at the gin"
IN_STORE = "in store"
SHIPPED = "shipped"
DELIVERED = "delivered"


@dataclass(frozen=True)
class Placement:
    """Where one bale is, and what says so."""

    bale_id: BaleId
    net: Weight
    where: str
    detail: str

    def __str__(self) -> str:
        return f"{self.bale_id} {self.where}, {self.detail}"


@dataclass(frozen=True)
class Inventory:
    """Every bale placed, and the things that do not add up."""

    placements: tuple[Placement, ...]
    orphans: tuple[tuple[str, str], ...]

    def where(self, where: str) -> list[Placement]:
        return [one for one in self.placements if one.where == where]

    def weight_at(self, where: str) -> Weight:
        return total([one.net for one in self.where(where)])

    @property
    def bales(self) -> int:
        return len(self.placements)

    @property
    def net(self) -> Weight:
        return total([one.net for one in self.placements])

    @property
    def balances(self) -> bool:
        return not self.orphans

    def counts(self) -> dict[str, int]:
        tallied = {AT_THE_GIN: 0, IN_STORE: 0, SHIPPED: 0, DELIVERED: 0}
        for one in self.placements:
            tallied[one.where] += 1
        return tallied

    def __str__(self) -> str:
        counted = self.counts()
        parts = ", ".join(f"{count} {where}" for where, count in counted.items() if count)
        return parts or "nothing pressed"


def take(book: Book, season: Season) -> Inventory:
    """Walk the press, the warehouse and the contracts against each other."""
    bales = BaleRepository(book.connection)
    receipts = ReceiptRepository(book.connection)
    contracts = ContractRepository(book.connection)

    pressed = {str(one.bale_id): one for one in bales.for_season(season)}
    placements: list[Placement] = []
    orphans: list[tuple[str, str]] = []

    for key, one in pressed.items():
        receipt = receipts.for_bale(one.bale_id)
        contract = contracts.contract_for(one.bale_id)
        if contract is not None:
            where, detail = DELIVERED, f"against {contract}"
            if receipt is not None:
                orphans.append((key, f"delivered but receipt {receipt.number} is outstanding"))
        elif receipt is not None:
            where, detail = IN_STORE, f"receipt {receipt.number} at {receipt.warehouse}"
        else:
            released = _released(receipts, key)
            if released is not None:
                where, detail = SHIPPED, f"receipt {released} released"
            else:
                where, detail = AT_THE_GIN, "no receipt"
        placements.append(Placement(one.bale_id, one.net, where, detail))

    for receipt in receipts.outstanding():
        if str(receipt.bale_id) not in pressed:
            orphans.append(
                (receipt.number, "is a receipt against a bale this gin never pressed")
            )
    return Inventory(tuple(placements), tuple(orphans))


def _released(receipts: ReceiptRepository, bale_id: str) -> str | None:
    for receipt in receipts.rows(
        "SELECT number FROM receipts WHERE bale_id = ? AND released_on IS NOT NULL "
        "ORDER BY released_on DESC",
        (bale_id,),
    ):
        return str(receipt["number"])
    return None
