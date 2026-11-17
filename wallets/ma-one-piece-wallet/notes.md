# ma-one-piece-wallet: notes

**What this is:** the M.A+ (Maurizio Amadei) One Piece Wallet, taken from the Wallet-corpus- research archive, item `map01_one_piece_wallet`
(`https://github.com/Sigurius23/Wallet-corpus-`, commit `bda0572`, `carpe_diem_research/wallet/designers/ma_plus/items/map01_one_piece_wallet/`).
**Everything here comes from the retailer's text and seven product photographs. Nothing has been measured on a physical wallet.**

**Rights:** the corpus says its images are research documentation only and that no licence is granted, so they are referenced by path and are not copied into this repository.

## What the sources state (tagged `design` in the record)
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
| at the opposite end, two tight hairpin folds, one over the other, each pinned by a thread tie | moderate |
| the void inside each loop looks about one leather thickness across | low |
| which face of the sheet is the grain; whether the folds are skived; the edge finish | not visible |
| any scale: none of the photographs has a ruler, so no radius or thickness can be measured from them | n/a |

The interior photographs (006, 009, 010, 011) show a flap with a silver cross, a pocket with a curved edge, and concertina pockets folded at the bottom; I have not
described the pockets in the record yet.

## What the report concludes (run `walletsim wallet-report wallets/ma-one-piece-wallet`)
See `sim/run-*/report.md`. In short: with the empty wallet's stacks the two loops are the folds that matter, not the spine, and the model can only screen them.

## To turn this into a real record
Measure a physical One Piece Wallet: closed thickness and layer count at the spine; each loop's inside radius or gap, edge-on next to a ruler; the sheet thickness at several points;
and ask the maker whether the folds are skived or dampened. The report's "What to measure first" list says the same in order.

## The 3D viewer (`viewer.html`)
A single page (it loads Three.js from a CDN) that folds one 1 mm strip with the structure read from the photographs: bottom panel, spine, top panel, loop, leaf A, left fold, leaf B, loop, leaf C.
It is a **structural sketch, not a scan or a simulation**: the flat cut pattern is unknown, so there are no pockets, flap or silver cross, panels can pass through each other, and the colours are the closed-form strain
at each fold scaled with the fold angle. Two sliders open the wallet like a book and open the pockets; a third sets the loop radius.

What building it showed: in this one-sheet layout the loops and the spine are **coupled**. The layers sit one loop-gap apart, so with the loops' 0.5 mm inside radius the spine wraps about 7 mm
(inside radius 3.5 mm, closed-form strain 12.5 %), not the 3 mm the record lists for the spine independently. If this layout is right, the record's spine stack should be derived from the loop radius.
That needs the topology confirmed first (the flat pattern, or photographs of the wallet unfolded).
