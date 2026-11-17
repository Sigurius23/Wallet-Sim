# ma-one-piece-double-wallet: notes

**What this is:** the M.A+ (Maurizio Amadei) One Piece **Double** Wallet (W7D / W9D / W10D), from the Wallet-corpus- research archive, item `map02_one_piece_double_wallet`
(`https://github.com/Sigurius23/Wallet-corpus-`, commit `bda0572`, `carpe_diem_research/wallet/designers/ma_plus/items/map02_one_piece_double_wallet/`).
**Everything here comes from the retailer's text and ten product photographs. Nothing has been measured on a physical wallet.**

**Rights:** the corpus says its images are research documentation only and that no licence is granted, so they are referenced by path and are not copied into this repository.

## What the sources state (tagged `reported`: stated by the seller, not checked)
| fact | source |
|---|---|
| one piece of 1 mm thick calf leather; soft black; silver cross | retailer page, corpus source `MAP04` (Lucentement) |
| sizes S 11 x 7 cm, L 14.5 x 9 cm, XL 17.5 x 11 cm; the XL is sold as a clutch | same |
| composition: calf leather 100 % | same |
| no date: the earliest retailer record is 2022-01-06, which is not a design date | corpus `README` and `TIMELINE` |

## What I read from the photographs (tagged `inferred` or `assumed`), with my confidence
Edge-on photographs of the closed wallet (corpus images 017, and 012 with two sizes side by side), enlarged:
| observation | confidence |
|---|---|
| the outer sheet wraps one end, the spine, and continues as the bottom panel | moderate |
| **four** thin inner leaves, each with a thread tie near the spine end (four ties at that end) | moderate |
| two tied rounded loops at the opposite end, one over the other | moderate |
| the same one-sheet accordion as the One Piece Wallet with one more leaf: top, loop 1, leaf A, left fold 1, leaf B, loop 2, leaf C, left fold 2, leaf D; the loops turn grain out, the left folds grain in | inferred layout |
| opened (images 013, 014) it shows a row of fan-shaped pockets, which a cross-section cannot represent | not modelled |
| which face is the grain; whether the folds are skived; the edge finish; any scale | not visible |

## What the report concludes (run `walletsim wallet-report wallets/ma-one-piece-double-wallet`)
See `sim/run-*/report.md` and `page.html`. The record has five folds. The spine, which wraps the four leaves, is 9 mm of stack at the assumed loop void (inside radius 4.5 mm, closed-form strain 10 %,
range 4 to 13 % for the stack range 6.5 to 24 mm). The four tight hairpins (two loops, two left folds) are the same assumption as in the One Piece Wallet, so they give the same numbers: 19 to 21 % in the simulation,
which bridges the stack, against 50 % in the closed form. **That repetition is not evidence about this wallet.** The loop void is read from enlarged photographs with no scale and then copied; only a ruler in the photograph can change it.

One thing the layout does predict: more leaves make a **larger** spine radius (9 mm of stack here against 7 mm in the One Piece Wallet), so the spine strains **less** (10 % against 12.5 %). That follows from the inferred layout, not from a measurement.

## To turn this into a real record
Measure a physical One Piece Double Wallet: closed thickness and layer count at the spine; the loops' and left folds' inside radius edge-on next to a ruler; the sheet thickness; and ask the maker whether the folds are skived or dampened.
The flat pattern would confirm or correct the layout above.

## Not done
No 3D viewer for this wallet yet: the One Piece Wallet's viewer is written for three leaves and would need its fold list made data-driven (four leaves, five hinges).
