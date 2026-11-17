# Wallet archive

One folder per wallet, named by a short slug. Format: `docs/DATA_MODEL.md`. Start a new entry by copying
`_template/`. Photos are never overwritten; derived files go in `measured/`.

## Run a wallet through the simulator
```
walletsim wallet-report wallets/<slug>          # about 1 min: report.md, result.json, figures and the exact inputs, in wallets/<slug>/sim/run-<hash>/
```
The report lists every input with where it came from (measured, reported, inferred, design, literature, assumed), the fold results, how much they depend on the least
certain number, all 14 failure modes (computed, flagged, not triggered, not modelled), and what to measure first. A number without a `source` is an error.

`walletsim wallet-page wallets/<slug>` turns the latest report into `page.html` next to it: one file with the chart, figures, inputs and failure modes.
`walletsim wallet-viewer wallets/<slug>` writes `viewer.html`: a 3D structural sketch of a one-sheet record's folds that opens and closes (one-sheet accordions and the origami; it loads Three.js from a CDN).

## What is here
| Wallet | What it is | Status |
|---|---|---|
| `ma-one-piece-wallet` | the **M.A+ One Piece Wallet** from the Wallet-corpus- archive: one 1 mm calf sheet folded with an outer spine and two tight loops | **photos-only**: text and product photographs, nothing measured; radii and stacks are inferences with ranges. `viewer.html` is a 3D sketch of its fold structure (generated from the record) |
| `ma-one-piece-double-wallet` | the **M.A+ One Piece Double Wallet** (corpus item map02): the same one-sheet construction with four inner leaves, so five modelled folds | **photos-only**: the four tight hairpins repeat the One Piece loop assumption, so they are not independent evidence; `viewer.html` is a 3D sketch |
| `ma-mavr-origami-wallet` | the **M.A+ MAV.R 1.0 origami wallet** (corpus item map04): a used, one-fold pig-leather wallet with pockets and gussets, from a resale listing | **photos-only**: its one real datum is the seller's 18 mm closed depth; the gusset crease is a placeholder; the leather stiffness is the calfskin placeholder; `viewer.html` sketches the flap hinge and a bill-pocket gusset |
| `sr-whalet-sr202-2022` | the **Sruli Recht WHALET SR202** (2022 EDITIONS reissue of a 2010 design, corpus item sr005): one laser-cut horse-skin sheet folded and riveted into a card wallet; the first record with a year, a first-party source and a maker-stated closed depth (10 mm) | **photos-only**: the sheet thickness is not stated and is assumed; which end is the flap hinge is my reading of one oblique photograph; `assembly.yaml` is a photograph-read reconstruction, and `viewer.html` is its functional twin: the flap opens and the four pockets fill with cards |
| `slim-6card-design` | a **generated design** (the leather-patterns kernel's `slim_6card` bifold), not a photographed wallet and not an MA+ wallet | design only: nothing measured; used to test the pipeline |

Corpus images are research documentation only, so records reference them by path and do not copy them. Replace or add records as real wallets are photographed and measured (`docs/CAPTURE.md`). The measurement that matters most: the closed wallet's thickness at the spine.
