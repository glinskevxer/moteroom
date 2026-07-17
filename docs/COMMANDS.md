# Commands

Generated from the command tree. Run
`python -m moteroom.tools.check_commands --write` after adding one.

## Groups

| group | what it covers |
| --- | --- |
| `audit` | The trail of everything that wrote to the book. |
| `bale` | Pressing and tagging bales. |
| `card` | Classing cards back from the office. |
| `contract` | Forward contracts against the season's bales. |
| `loan` | Bales under loan. |
| `lot` | Running lots through the plant. |
| `order` | Shipping orders against receipts in store. |
| `producer` | Growers and the farms they gin off. |
| `receipt` | Warehouse receipts, in and out of store. |
| `report` | Reports off the book. |
| `setting` | Values that belong to the plant rather than to a season. |
| `settle` | Paying producers what the season came to. |
| `ticket` | Weighing modules in at the scale. |

## Commands

| command | what it does |
| --- | --- |
| `moteroom about` | Say which book this is and what is in it. |
| `moteroom audit actions` | How often each action has been run this season. |
| `moteroom audit list` | The most recent things done, newest first. |
| `moteroom audit subject` | Everything ever done to one ticket, lot or bale. |
| `moteroom backup` | Copy the book somewhere safe, through sqlite rather than the filesystem. |
| `moteroom bale list` | Bales pressed this season. |
| `moteroom bale press` | Press one bale off a lot. |
| `moteroom bale restore` | Work out what restoring moisture does to a press weight. |
| `moteroom bale show` | One bale off its tag. |
| `moteroom bale wrap` | Say whether the bagging and ties will see the season out. |
| `moteroom card calibrate` | Check the classing line against a standard and say whether it is out. |
| `moteroom card correct` | Take a corrected transfer over cards already on file. |
| `moteroom card list` | Every card back this season. |
| `moteroom card load` | Load a classing transfer file. |
| `moteroom card reclass` | Ask the office to look at a bale again. |
| `moteroom card sample` | Cut both samples off a bale for the office. |
| `moteroom card show` | One card, as the office sent it. |
| `moteroom card waiting` | Bales pressed with no card back yet. |
| `moteroom close` | Say whether the season is finished with, and what is left if not. |
| `moteroom compact` | Hand back the pages a season's deletions left behind. |
| `moteroom contract deliver` | Deliver one classed bale against a contract. |
| `moteroom contract fill` | How much of a contract is still to go. |
| `moteroom contract list` | Every contract this season and how much of it is left. |
| `moteroom contract price` | What one classed bale is paid against a contract. |
| `moteroom contract write` | Put a contract on the book. |
| `moteroom doctor` | Look over the book and say whether anything is wrong. |
| `moteroom export` | Write the whole season out as files. |
| `moteroom init` | Make the book if it is not there and bring it up to date. |
| `moteroom loan pool` | The whole season priced at loan. |
| `moteroom loan redeem` | What it costs to take a bale back out of loan. |
| `moteroom loan value` | What one classed bale loans for, line by line. |
| `moteroom lot byproduct` | Price a load of motes or gin trash and share it out. |
| `moteroom lot close` | Say a lot is off the press. |
| `moteroom lot driers` | Check the drier settings against the cotton coming in. |
| `moteroom lot energy` | Work out what a day at the plant cost in power and gas. |
| `moteroom lot gin` | Gin a set of tickets as one lot. |
| `moteroom lot list` | Every lot this season with its turnout. |
| `moteroom lot shift` | Work out what a shift ran at, given its stoppages. |
| `moteroom lot show` | One lot, with its turnout and how the press compared. |
| `moteroom order show` | One order and the loads it makes. |
| `moteroom order write` | Write an order against receipts that are still outstanding. |
| `moteroom producer add` | Put a grower on the book. |
| `moteroom producer farm` | Add a farm and tract to a grower. |
| `moteroom producer list` | Every grower on the book. |
| `moteroom producer season` | One grower's whole season, and how it sits against the plant. |
| `moteroom producer show` | One grower, with their farms and acres. |
| `moteroom receipt acknowledge` | Read the provider's answer and release what it accepted. |
| `moteroom receipt cover` | Work out the gap between what is in store and what a policy would pay. |
| `moteroom receipt issue` | Take a bale into store. |
| `moteroom receipt list` | Receipts still outstanding. |
| `moteroom receipt move` | Move a bale to another warehouse, which is two receipts and a gap. |
| `moteroom receipt release` | Release a receipt to whoever takes the bale. |
| `moteroom receipt transfer` | Write an electronic transfer for receipts still in store. |
| `moteroom report aging` | How long the bales in store have been sitting. |
| `moteroom report cash` | What the gin owes and what it is owed. |
| `moteroom report daily` | What ran on one day. |
| `moteroom report exceptions` | Everything that needs somebody to do something about it. |
| `moteroom report freight` | What the hauling came to. |
| `moteroom report inventory` | Where every bale pressed this season actually is. |
| `moteroom report ladder` | Where the season's bales sat on the schedule. |
| `moteroom report outstanding` | Producers with cotton in and no settlement written. |
| `moteroom report position` | Where the bales are. |
| `moteroom report producers` | Every producer at a glance, most cotton first. |
| `moteroom report quality` | How the season classed. |
| `moteroom report season` | The whole season on one page. |
| `moteroom report settlements` | Every settlement written this season. |
| `moteroom report statement` | One producer's page, off the settlement already written. |
| `moteroom report storage` | What the warehouse will bill. |
| `moteroom seasons` | Every season this book holds and how much of each. |
| `moteroom setting get` | Read one setting. |
| `moteroom setting list` | Every setting, and what is still missing. |
| `moteroom setting set` | Write one setting. |
| `moteroom settle advance` | Record money paid out before the settlement. |
| `moteroom settle cheque` | Write a cheque against a settlement already run. |
| `moteroom settle cheques` | Every cheque written this season. |
| `moteroom settle cleared` | Mark a cheque cleared, or void it. |
| `moteroom settle defer` | Agree to hold a producer's money until a day in the next year. |
| `moteroom settle equity` | Allocate the season's margin back to the members on ginned volume. |
| `moteroom settle list` | Every settlement written this season. |
| `moteroom settle owing` | Price what a producer owes the gin, interest and all. |
| `moteroom settle preview` | Work a producer's settlement out without writing it down. |
| `moteroom settle rates` | Post this season's rates, or read the posted ones back. |
| `moteroom settle run` | Settle a producer and write it down. |
| `moteroom size` | How big the book is and which tables it went into. |
| `moteroom ticket correct` | Void a ticket by writing the corrected one. |
| `moteroom ticket export` | Write this season's live tickets back out as a csv. |
| `moteroom ticket freight` | Price a truckload of modules and share it over them. |
| `moteroom ticket import` | Load scale tickets out of the weighbridge export. |
| `moteroom ticket list` | Every live ticket this season. |
| `moteroom ticket scale` | Check a scale certificate and what it does to a weight. |
| `moteroom ticket show` | One ticket, with what it weighed and whether it still counts. |
| `moteroom ticket weigh` | Write a scale ticket for one module. |
| `moteroom ticket yard` | What is still in the yard, worst first. |
| `moteroom verify` | Ask sqlite whether a book is intact. |
