# Architecture

Generated from the layer rules the build enforces. Run
`python -m moteroom.tools.check_architecture --write` after changing them.

| package | modules | may import | what is in it |
| --- | --- | --- | --- |
| `classing` | 9 | `core`, `ginning`, `loan`, `press`, `receiving`, `settlement`, `warehouse` | instrument readings, colour, the office transfer, sampling |
| `cli` | 16 | `classing`, `core`, `ginning`, `loan`, `press`, `receiving`, `reporting`, `service`, `settlement`, `storage`, `warehouse` | the command tree |
| `core` | 7 | nothing | units, money, identifiers, the crop year |
| `ginning` | 7 | `classing`, `core`, `loan`, `press`, `receiving`, `settlement`, `warehouse` | lots, turnout, plant time, drying, byproducts |
| `loan` | 4 | `classing`, `core`, `ginning`, `press`, `receiving`, `settlement`, `warehouse` | the premium and discount schedule, pool value, redemption |
| `press` | 4 | `classing`, `core`, `ginning`, `loan`, `receiving`, `settlement`, `warehouse` | bales, the counter, moisture restoration, bagging and ties |
| `receiving` | 6 | `classing`, `core`, `ginning`, `loan`, `press`, `settlement`, `warehouse` | tickets, parties, the yard, the scales, the freight |
| `reporting` | 12 | `classing`, `core`, `ginning`, `loan`, `press`, `receiving`, `settlement`, `warehouse` | reports, as data rather than as text |
| `service` | 6 | `classing`, `core`, `ginning`, `loan`, `press`, `receiving`, `reporting`, `settlement`, `storage`, `warehouse` | the work that needs the book and the domain at once |
| `settlement` | 10 | `classing`, `core`, `ginning`, `loan`, `press`, `receiving`, `warehouse` | charges, seed, allocation, contracts, equity, cheques |
| `storage` | 20 | `classing`, `core`, `ginning`, `loan`, `press`, `receiving`, `settlement`, `warehouse` | the sqlite book, its migrations and the repositories over it |
| `tools` | 17 | `classing`, `cli`, `core`, `ginning`, `loan`, `press`, `receiving`, `reporting`, `service`, `settlement`, `storage`, `warehouse` | the gates the build runs against itself |
| `warehouse` | 7 | `classing`, `core`, `ginning`, `loan`, `press`, `receiving`, `settlement` | receipts, storage, shipping, transfers, insurance |

Reading the table: a package may import itself and the packages named,
and nothing else in this codebase. `core` sits at the bottom and knows
nothing about anything. `cli` sits at the top and is allowed to know the
rest, because that is its job.
