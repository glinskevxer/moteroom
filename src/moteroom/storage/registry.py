"""Every repository over one connection.

Commands were opening the book and then building four or five repositories over
the same connection, one line each, in a slightly different order every time.
The set of repositories is not a decision a command gets to make, so it is made
once here and handed over whole.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from moteroom.storage.audit import AuditRepository
from moteroom.storage.cards import CardRepository
from moteroom.storage.cheques import ChequeRepository
from moteroom.storage.contracts import ContractRepository
from moteroom.storage.freight import ByproductRepository, FreightRepository
from moteroom.storage.lots import BaleRepository, LotRepository
from moteroom.storage.producers import FarmRepository, ProducerRepository
from moteroom.storage.rates import RatesRepository
from moteroom.storage.settings import SettingsRepository
from moteroom.storage.settlement import AdvanceRepository, StatementRepository
from moteroom.storage.tickets import TicketRepository
from moteroom.storage.warehouse import OrderRepository, ReceiptRepository


@dataclass
class Repositories:
    """One of each, all over the same connection."""

    connection: sqlite3.Connection
    producers: ProducerRepository = field(init=False)
    farms: FarmRepository = field(init=False)
    tickets: TicketRepository = field(init=False)
    lots: LotRepository = field(init=False)
    bales: BaleRepository = field(init=False)
    cards: CardRepository = field(init=False)
    receipts: ReceiptRepository = field(init=False)
    orders: OrderRepository = field(init=False)
    contracts: ContractRepository = field(init=False)
    statements: StatementRepository = field(init=False)
    advances: AdvanceRepository = field(init=False)
    settings: SettingsRepository = field(init=False)
    rates: RatesRepository = field(init=False)
    audit: AuditRepository = field(init=False)
    cheques: ChequeRepository = field(init=False)
    freight: FreightRepository = field(init=False)
    byproducts: ByproductRepository = field(init=False)

    def __post_init__(self) -> None:
        self.producers = ProducerRepository(self.connection)
        self.farms = FarmRepository(self.connection)
        self.tickets = TicketRepository(self.connection)
        self.lots = LotRepository(self.connection)
        self.bales = BaleRepository(self.connection)
        self.cards = CardRepository(self.connection)
        self.receipts = ReceiptRepository(self.connection)
        self.orders = OrderRepository(self.connection)
        self.contracts = ContractRepository(self.connection)
        self.statements = StatementRepository(self.connection)
        self.advances = AdvanceRepository(self.connection)
        self.settings = SettingsRepository(self.connection)
        self.rates = RatesRepository(self.connection)
        self.audit = AuditRepository(self.connection)
        self.cheques = ChequeRepository(self.connection)
        self.freight = FreightRepository(self.connection)
        self.byproducts = ByproductRepository(self.connection)

    def names(self) -> list[str]:
        """What the registry holds, which the wiring gate reads."""
        return sorted(
            name
            for name, value in vars(self).items()
            if name != "connection" and value is not None
        )
