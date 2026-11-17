# Wallet archive

One folder per wallet, named by a short slug. Format: `docs/DATA_MODEL.md`. Start a new entry by copying
`_template/`. Photos are never overwritten; derived files go in `measured/`.

## Run a wallet through the simulator
```
walletsim wallet-report wallets/<slug>          # about 1 min: report.md, result.json, figures and the exact inputs, in wallets/<slug>/sim/run-<hash>/
```
The report lists every input with where it came from (measured, inferred, design, literature, assumed), the fold results, how much they depend on the least
certain number, all 14 failure modes (computed, flagged, not triggered, not modelled), and what to measure first. A number without a `source` is an error.

## What is here
| Wallet | What it is | Status |
|---|---|---|
| `slim-6card-design` | a **generated design** (the leather-patterns kernel's `slim_6card` bifold), not a photographed wallet and not an MA+ wallet | design only: nothing measured; used to test the pipeline |

Replace or add records as real wallets are photographed and measured (`docs/CAPTURE.md`). The measurement that matters most: the closed wallet's thickness at the spine.
