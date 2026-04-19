"""Building a producer's settlement out of the book.

This is the one place that reads across every package, and it does it in one
direction: tickets to lots, lots to allocations, allocations to money. Nothing
below it knows a settlement exists.

The rate a producer is paid at is not the base rate. It is the average rate
their own lots' bales classed at, so a producer whose cotton came in clean is
paid for it and one whose lot carried bark is not carried by everybody else.
A lot with no cards back yet falls back to the base rate, and the settlement
says so rather than quietly pretending.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from moteroom.core.errors import ValidationError
from moteroom.core.ids import LotId
from moteroom.core.money import CentsPerPound, Money, total_money
from moteroom.core.season import Season
from moteroom.core.weight import Weight, total
from moteroom.ginning.byproduct import ByproductLedger
from moteroom.loan import pool
from moteroom.receiving.freight import FreightLedger
from moteroom.settlement.allocation import allocate, divide_count
from moteroom.settlement.charges import bill
from moteroom.settlement.seed import credit
from moteroom.settlement.statement import Statement
from moteroom.settlement.terms import Terms
from moteroom.storage.book import Book
from moteroom.storage.cards import CardRepository
from moteroom.storage.lots import BaleRepository, LotRepository
from moteroom.storage.settlement import AdvanceRepository
from moteroom.storage.tickets import TicketRepository


@dataclass(frozen=True)
class LotShare:
    """One producer's part of one lot."""

    lot: str
    seed_cotton: Weight
    lint: Weight
    seed: Weight
    bales: int
    modules: int
    rate: CentsPerPound
    classed: bool

    @property
    def proceeds(self) -> Money:
        return self.rate.on(self.lint)


class SettlementService:
    """Reads the book and works a producer's season out of it."""

    def __init__(self, book: Book, terms: Terms) -> None:
        self.book = book
        self.terms = terms
        self.tickets = TicketRepository(book.connection)
        self.lots = LotRepository(book.connection)
        self.bales = BaleRepository(book.connection)
        self.cards = CardRepository(book.connection)
        self.advances = AdvanceRepository(book.connection)

    def rate_for_lot(self, lot_number: int, season: Season) -> tuple[CentsPerPound, bool]:
        """What the bales off a lot actually classed at."""
        lot = LotId(season, lot_number)
        pairs = []
        for one in self.bales.for_lot(lot):
            if self.cards.has(one.bale_id):
                pairs.append((one, self.cards.get(one.bale_id)))
        if not pairs:
            return self.terms.base_rate, False
        priced = pool.build(pairs, self.terms.base_rate)
        if priced.bales == 0:
            return self.terms.base_rate, False
        return priced.average_rate, True

    def shares_for(self, season: Season, producer: str) -> list[LotShare]:
        """Every lot this producer had cotton in, and their part of it."""
        held = self.tickets.book(season)
        live = {ticket.number: ticket for ticket in held.live()}
        shares: list[LotShare] = []
        for run in self.lots.for_season(season):
            lot_tickets = [live[number] for number in run.tickets if number in live]
            if len(lot_tickets) != len(run.tickets):
                continue
            if producer not in {ticket.producer for ticket in lot_tickets}:
                continue
            split = allocate(run, lot_tickets)
            counts = divide_count(len(self.bales.for_lot(run.lot)), split.basis)
            mine = [ticket for ticket in lot_tickets if ticket.producer == producer]
            rate, classed = self.rate_for_lot(run.lot.number, season)
            shares.append(
                LotShare(
                    lot=str(run.lot),
                    seed_cotton=total([ticket.net for ticket in mine]),
                    lint=split.lint[producer],
                    seed=split.seed[producer],
                    bales=counts[producer],
                    modules=len(mine),
                    rate=rate,
                    classed=classed,
                )
            )
        return shares

    def build(
        self,
        season: Season,
        producer: str,
        freight: FreightLedger | None = None,
        byproducts: ByproductLedger | None = None,
    ) -> Statement:
        """Work the whole statement out, advances and all.

        Freight and byproducts are handed in rather than read, because both
        are the plant's own arrangements and a producer who hauled their own
        modules has no freight on their page at all.
        """
        shares = self.shares_for(season, producer)
        if not shares:
            raise ValidationError("producer", f"{producer} has no cotton in {season}")
        charges = bill(
            self.terms.charges,
            total([share.seed_cotton for share in shares]),
            bales=sum(share.bales for share in shares),
            modules=sum(share.modules for share in shares),
        )
        seed_credit = credit(total([share.seed for share in shares]), self.terms.seed)
        return Statement(
            producer=producer,
            season=season,
            bales=sum(share.bales for share in shares),
            lint=total([share.lint for share in shares]),
            lint_proceeds=total_money([share.proceeds for share in shares]),
            gin_charges=charges.total,
            seed_credit=seed_credit.net,
            freight=self._freight(season, producer, freight),
            byproduct_credit=self._byproducts(season, producer, byproducts),
            advances=self.advances.for_producer(season, producer),
        )

    def _freight(self, season: Season, producer: str, ledger: FreightLedger | None) -> Money:
        """What the hauling on this producer's own modules came to."""
        if ledger is None:
            return Money.zero()
        tickets = [
            one.number for one in self.tickets.book(season).live() if one.producer == producer
        ]
        return ledger.for_tickets(tickets)

    def _byproducts(
        self, season: Season, producer: str, ledger: ByproductLedger | None
    ) -> Money:
        """This producer's share of what the motes and gin trash made."""
        if ledger is None or not len(ledger):
            return Money.zero()
        held = self.tickets.book(season)
        volume = {code: held.net_for_producer(code) for code in held.producers()}
        if not volume:
            return Money.zero()
        return ledger.allocate(volume).get(producer, Money.zero())

    def settled_producers(self, season: Season) -> list[str]:
        """Producers with live tickets, which is who there is to settle."""
        return self.tickets.book(season).producers()

    def unclassed_lots(self, season: Season) -> list[str]:
        """Lots still on the base rate because no card has come back."""
        return [
            str(run.lot)
            for run in self.lots.for_season(season)
            if not self.rate_for_lot(run.lot.number, season)[1]
        ]

    def as_of(self) -> date:
        return date.today()
