# ma-one-piece-wallet: notes

**What this is:** the M.A+ (Maurizio Amadei) One Piece Wallet, taken from the Wallet-corpus- research archive, item `map01_one_piece_wallet`
(`https://github.com/Sigurius23/Wallet-corpus-`, commit `bda0572`, `carpe_diem_research/wallet/designers/ma_plus/items/map01_one_piece_wallet/`).
**Everything here comes from the retailer's text and seven product photographs. Nothing has been measured on a physical wallet.**

**Rights:** the corpus says its images are research documentation only and that no licence is granted, so they are referenced by path and are not copied into this repository.

## What the sources state (tagged `reported` in the record: stated by the seller, not checked)
| fact | source |
|---|---|
| one piece of 1 mm thick calf leather, red or black | retailer page, corpus source `MAP03` (Lucentement) |
| "folding technique and minimal usage of seams"; silver cross detail; handmade in Italy; made to order | same |
| sizes S 11.5 x 7.5 cm, M 13 x 9 cm, L 15 x 10 cm | same |
| composition: calf leather 100 % | same |
| no date: the earliest retailer record is 2022-01-06, which is not a design date | corpus `README` and `TIMELINE` |

The sizes look like the **closed** footprint: the closed wallet in the photographs has a width to height ratio of about 0.70, and the three sizes give 0.65, 0.69 and 0.67. That is an inference from the pictures, not a statement in the source.

## What I read from the photographs (tagged `inferred` or `assumed`), with my confidence
Edge-on photographs of the closed wallet (corpus images 005 black and 008 red), enlarged:
| observation | confidence |
|---|---|
| the outer sheet wraps one end, the spine, and continues as the bottom panel | moderate |
| three thin inner leaves lie inside the wrap, each with a thread tie near the spine end | moderate |
| at the opposite end, two tight hairpin folds, one over the other, each pinned by a thread tie; with the left fold between leaves A and B that makes **three** tight hairpins in the record | moderate |
| the void inside each loop looks about one leather thickness across | low |
| which face of the sheet is the grain; whether the folds are skived; the edge finish | not visible |
| any scale: none of the photographs has a ruler, so no radius or thickness can be measured from them | n/a |

The interior photographs (006, 009, 010, 011) show a flap with a silver cross, a pocket with a curved edge, and concertina pockets folded at the bottom; I have not
described the pockets in the record yet.

## What the report concludes (run `walletsim wallet-report wallets/ma-one-piece-wallet`)
See `sim/run-*/report.md` (and `page.html`, the same results as one page). In short: with the empty wallet's stacks the **three tight hairpins** (two loops and the left fold) are the folds that matter, not the spine, and the model can only screen them: 19 to 21 % in the simulation, which bridges the stack, against 50 % in the closed form (range 20 to 67 %). The spine is 11 to 13 % (closed form 12.5 %, range 5 to 17 %).

**Correction, 2026-11:** the first version of this record listed only the two right-end loops, left out the left fold between leaves A and B, and gave loop 2 the wrong grain direction (in; both right-end loops turn grain out, the left fold turns grain in). The record, tests and report were redone; the earlier run was discarded.

## To turn this into a real record
Measure a physical One Piece Wallet: closed thickness and layer count at the spine; each loop's inside radius or gap, edge-on next to a ruler; the sheet thickness at several points;
and ask the maker whether the folds are skived or dampened. The report's "What to measure first" list says the same in order.

## The 3D viewer (`viewer.html`)
Generated from this record by `walletsim wallet-viewer wallets/ma-one-piece-wallet` (the same generator draws the Double Wallet and the origami), so its leaves, sizes, loop range and sheet thickness are the record's.
A single page (it loads Three.js from a CDN) that folds one 1 mm strip with the structure read from the photographs: bottom panel, spine, top panel, loop, leaf A, left fold, leaf B, loop, leaf C.
It is a **structural sketch, not a scan or a simulation**: the flat cut pattern is unknown, so there are no pockets, flap or silver cross, panels can pass through each other, and the colours are the closed-form strain
at each fold scaled with the fold angle. Two sliders open the wallet like a book and open the pockets; a third sets the loop radius.

What building it showed, and what changed because of it: in this one-sheet layout the loops and the spine are **coupled**. The layers sit one loop-gap apart, so the spine wraps
`leaves x t + (leaves + 1) x gap` = 3 x 1 + 4 x 1 = 7 mm at the loops' recorded 0.5 mm inside radius (inside radius 3.5 mm, closed-form strain 12.5 %). The record used to list the spine at 3 mm
independently, which this layout contradicts. **The record now derives the spine stack from the loop** (`stack_from_loops` in `wallet.yaml`), so it is 7 mm with a range of 5 to 19 mm that follows the
loops' range, tagged `assumed` because the loop radius it comes from is assumed. The layout itself is still an inference from the edge-on photographs: confirm it with the flat pattern or photographs of the wallet unfolded.
