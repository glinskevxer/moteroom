# Glossary

Generated from the classes that define these words. Run
`python -m moteroom.tools.check_glossary --write` after changing one.

| term | where | what it is |
| --- | --- | --- |
| `Acknowledgement` | `warehouse.ewr` | What the provider said about a transfer. |
| `Advance` | `settlement.statement` | Money paid out before the settlement, which comes back off it. |
| `Allocation` | `settlement.allocation` | What each producer put in and what they get out. |
| `Allocation` | `settlement.equity` | A season's margin split across the members who ginned in it. |
| `Answer` | `classing.reclass` | The old card and the new one, and which way it went. |
| `Bale` | `press.bale` | One pressed bale as the tag reads it. |
| `BaleId` | `core.ids` | A twelve character bale id with its check digit already verified. |
| `BalePress` | `press.run` | The counter at the press, and the bales it has already stamped. |
| `Band` | `loan.schedule` | One row of a table: a closed range and what it does to the rate. |
| `BandTable` | `loan.schedule` | A column of the schedule, checked for gaps when it is built. |
| `ByproductLedger` | `ginning.byproduct` | Every load sold this season. |
| `CalibrationLog` | `classing.calibration` | Every check run on the line. |
| `CentsPerPound` | `core.money` | A price in cents per pound, carried to a hundredth of a cent. |
| `Certificate` | `receiving.scale` | One certification of one scale, by whoever tested it. |
| `Charge` | `receiving.freight` | What a load came to, and which of the three rates decided it. |
| `Charge` | `warehouse.storage` | What one bale owes the warehouse, split the way the invoice prints. |
| `ChargeSchedule` | `settlement.charges` | The plant's posted charges for a season. |
| `Check` | `classing.calibration` | One run of the standard through the line. |
| `Cheque` | `settlement.cheque` | One cheque as the register holds it. |
| `ClassingBook` | `classing.book` | Every card back this season, keyed by bale. |
| `ClassingFile` | `classing.transfer` | What one transfer from the office contained. |
| `ClassingRecord` | `classing.record` | What the office said about one bale. |
| `ColorGrade` | `classing.color` | A two digit colour code, held as the digits rather than as a number. |
| `ConflictError` | `core.errors` | A write would contradict something the book already holds. |
| `Contract` | `settlement.contract` | One promise to deliver bales inside a window. |
| `Deferral` | `settlement.deferred` | One agreement to hold a producer's money until a named day. |
| `DeferralBook` | `settlement.deferred` | Every deferral the gin has agreed to. |
| `Delivery` | `press.tare` | One lot of wrap arriving at the plant. |
| `EquityLedger` | `settlement.equity` | Equity by member and by year, and the fund that revolves it out. |
| `Exposure` | `warehouse.insurance` | What is in store, what it is worth, and what the policy would pay. |
| `Extraneous` | `classing.defect` | One finding: what it was and how much of it. |
| `Farm` | `receiving.party` | An FSA farm and tract, which is how acreage is reported. |
| `Fill` | `settlement.contract` | How much of a contract has been delivered. |
| `FreightLedger` | `receiving.freight` | Every load hauled in this season. |
| `GinBill` | `settlement.charges` | The charges on one producer's cotton, kept as the lines that print. |
| `GinCode` | `core.ids` | The five digit code the plant gins under. |
| `GinRun` | `ginning.run` | One lot: what went in, what came out and what the mote room caught. |
| `Haul` | `receiving.freight` | One truckload of modules. |
| `Holding` | `settlement.equity` | Equity allocated in one season and still standing. |
| `IneligibleError` | `loan.value` | A bale the loan will not take at any rate. |
| `LeafGrade` | `classing.defect` | A leaf grade of one through seven, or eight for below grade. |
| `Level` | `classing.defect` | How much of it there is, which is all the classer records. |
| `LotId` | `core.ids` | A gin lot, which is a season and a running number inside it. |
| `MatchReport` | `classing.book` | Where the cards and the press disagree. |
| `Matter` | `classing.defect` | What the classer found that should not be in a bale of cotton. |
| `Micronaire` | `classing.measure` | Fineness and maturity together, which is what mike actually measures. |
| `ModuleId` | `core.ids` | What the module tag says, normalised to upper case. |
| `ModuleTicket` | `receiving.ticket` | One weighed module, as the scale house wrote it down. |
| `ModuleYard` | `receiving.yard` | What is in the yard and what order it should go through the plant. |
| `Money` | `core.money` | Dollars and cents. May be negative, since deductions are money too. |
| `MoteroomError` | `core.errors` | Base class for everything this package raises on purpose. |
| `Movement` | `warehouse.movement` | One bale leaving one house for another. |
| `NotFoundError` | `core.errors` | A record was asked for by key and the book does not hold it. |
| `Pair` | `classing.sample` | Both cuts off one bale, and what they say about each other. |
| `Patronage` | `settlement.equity` | One member's share of a season's margin. |
| `Policy` | `warehouse.insurance` | One policy over bales in store. |
| `Pool` | `loan.pool` | Every bale that could be priced, and the ones that could not. |
| `PoolLine` | `loan.pool` | One bale in the pool, priced. |
| `Producer` | `receiving.party` | A grower the gin writes cheques to. |
| `Rate` | `receiving.freight` | What one hauler charges. |
| `RateBreakdown` | `loan.value` | Every line that moved the rate, in the order the office reads them. |
| `Receipt` | `warehouse.receipt` | One bale in store, and who holds the paper on it. |
| `ReceiptRegister` | `warehouse.register` | Every receipt this house has issued, outstanding or not. |
| `Reconciliation` | `ginning.reconcile` | What the lot sheet and the press each said, and by how much they differ. |
| `Redemption` | `loan.redemption` | What it costs to take one bale back out of loan. |
| `Register` | `settlement.cheque` | Every cheque written, in number order. |
| `Reject` | `classing.transfer` | A line that did not read, kept with the reason and where it was. |
| `Request` | `classing.reclass` | One bale sent back to the office. |
| `Restoration` | `press.restoration` | One press worth of restoration, in and out. |
| `Sale` | `ginning.byproduct` | One load of something that is not lint or seed. |
| `Sample` | `classing.sample` | One cut off one side of a bale. |
| `ScaleBook` | `receiving.scale` | Every certificate the plant holds, by scale. |
| `Season` | `core.season` | One crop year, named for the calendar year it opens in. |
| `SeedCredit` | `settlement.seed` | What the seed off one producer's cotton came to. |
| `SeedTerms` | `settlement.seed` | What the ginning agreement says about the seed. |
| `Setting` | `ginning.drying` | What the two stages are actually set to, against what came in. |
| `ShareSplit` | `receiving.party` | How a farm's cotton divides, in whole shares rather than percentages. |
| `Shift` | `ginning.plant` | One run of the plant, with what stopped it. |
| `ShiftLog` | `ginning.plant` | Every shift run this season. |
| `ShippingOrder` | `warehouse.shipping` | One order to move a set of bales out of a warehouse. |
| `Standard` | `classing.calibration` | One box of standard cotton and the values assigned to it. |
| `Staple` | `classing.measure` | Fibre length in thirty seconds of an inch, the way it is traded. |
| `Statement` | `settlement.statement` | What one producer is owed, or owes. |
| `Stoppage` | `ginning.plant` | One thing that stopped the plant, and for how long. |
| `Strength` | `classing.measure` | Grams per tex, which is what breaks in the spinning mill. |
| `TareStore` | `press.tare` | What wrap is on hand, and whether it will see the season out. |
| `Tariff` | `warehouse.storage` | The warehouse's published rates for a season. |
| `Terms` | `settlement.terms` | Everything a season is settled against. |
| `TicketBook` | `receiving.book` | Every ticket written this season, and which of them still count. |
| `Trash` | `classing.measure` | Surface trash by area, which the instrument reports as a percentage. |
| `TurnoutSummary` | `ginning.turnout` | Everything the daily sheet says about one lot. |
| `Uniformity` | `classing.measure` | Length uniformity as a percentage of the mean length. |
| `ValidationError` | `core.errors` | A value was rejected before it ever reached storage. |
| `Waiting` | `receiving.yard` | One module in the yard, with why it sits where it does. |
| `Weight` | `core.weight` | A whole number of pounds, never negative. |
