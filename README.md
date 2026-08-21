# moteroom

Lot accounting for a cotton gin. Seed cotton in at the scale, lint and seed out
the other end, classing back from the office, receipts at the warehouse and a
settlement for the producer.

Everything lives in one sqlite file, the book, and every command works against
it. There is no server and nothing to configure beyond the plant's own numbers.

## Install

    pip install -e ".[dev]"

That puts a `moteroom` command on the path. Without installing it,
`python -m moteroom` does the same thing from a checkout.

## What it covers

- **Receiving** module tickets, moisture, the yard's running order
- **Ginning** lots, turnout, plant time and stoppages, motes and gin trash
- **Press** bale numbering with a check digit, tare, moisture restoration
- **Classing** the office's fixed width transfer, colour, leaf, staple and mike
- **Loan** the premium and discount schedule, pool value, redemption
- **Warehouse** receipts, storage charges, shipping orders, electronic transfers
- **Settlement** lint allocation on dry weight, seed credit, gin charges, equity

## A worked example

One producer, one module, one lot, one bale. Every line below is what the
command actually prints, and a test replays the whole thing to keep it that way.

    $ moteroom init
    created season.sqlite3 at schema 13

    $ moteroom setting set gin_code 41207
    gin_code is 41207

    $ moteroom producer add BLYTHE "Blythe Farms"
    added BLYTHE

    $ moteroom ticket weigh HW-004181 BLYTHE 3312 38400 17200 --moisture 9.4 --on 2025-10-14
    ticket 1 HW-004181 21,200 lb

    $ moteroom lot gin 1 --lint 7400 --seed 11800 --motes 1300 --on 2025-10-16
    lot 2025-0001 ginned 21,200 lb into 7,400 lb of lint

    $ moteroom bale press 1 538 --on 2025-10-16
    bale 5-41207-00001-8 515 lb

    $ moteroom report daily --on 2025-10-16
    gin sheet for 2025-10-16
    ========================
    lot        modules  seed cotton  lint   seed  motes  turnout  bales
    ---------  -------  -----------  ----  -----  -----  -------  -----
    2025-0001        1        21200  7400  11800   1300    34.91      1

    1 lots, 21,200 lb in, 7,400 lb of lint, 1 bales
    turnout 34.91%
    average bale 515 lb

The lot is still on the press at that point, which is why one bale sits under a
lot sheet claiming seven thousand pounds of lint. `moteroom lot show 1` prints
the drift between the two, and it closes up as the rest of the bales come off.

## Layout

    src/moteroom/core/        units, money, identifiers, the crop year
    src/moteroom/receiving/   tickets, parties, the yard, the scales
    src/moteroom/ginning/     lots, turnout, plant time, byproducts
    src/moteroom/press/       bales, the press counter, moisture restoration
    src/moteroom/classing/    instrument readings, colour, the office transfer
    src/moteroom/loan/        the schedule, pool value, redemption
    src/moteroom/warehouse/   receipts, storage, shipping, electronic transfer
    src/moteroom/settlement/  charges, seed, allocation, contracts, equity
    src/moteroom/storage/     the sqlite book, migrations, repositories
    src/moteroom/service/     settlement, inventory and closing over the book
    src/moteroom/reporting/   the reports, as data rather than as text
    src/moteroom/cli/         the command tree
    src/moteroom/tools/       the gates CI runs against the repository itself
    docs/GLOSSARY.md          the gin's own words, generated from the code
    docs/ARCHITECTURE.md      the layers, generated from the rules that enforce them
    docs/COMMANDS.md          every command, generated from the command tree
    tests/                    the test suite

## Running the checks

    ruff check . && ruff format --check .
    mypy
    python -m moteroom.tools.check_migrations
    pytest

The gates in `src/moteroom/tools/` are run as their own CI steps and again from
the test suite, so `pytest` alone is enough on a working machine. Three of them
generate a document under `docs/` and check it has not drifted; run them with
`--write` after changing what they read.
