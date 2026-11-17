# Every way a fold, gusset or edge can be built, and what the simulator does with it

The list of constructions is the point of this page: it shows what exists, what does not, and where each one stands, so nothing is silently missing.
Results and numbers are in [`FOLD_STYLES.md`](FOLD_STYLES.md). The list is mine, drawn from your `prior-research/reference/construction.md` and from general leatherwork; if a
construction you use is missing, say so and it goes here.

**Status words**
- **simulated**: a CalculiX model, checked against a closed form where one exists.
- **closed form**: a formula only; the solver cannot represent it.
- **= other row**: mechanically identical to another construction in the model.
- **flagged**: no mechanics; named as a failure mode to watch (`FAILURE_MODES.md`).
- **not modelled**: nothing yet.

## 1. How the spine meets the contents
| Construction | What it is | Status | How |
|---|---|---|---|
| Round (U) spine | the leather wraps the end of the stack, a half-round | simulated | `fold-styles` (wrap) |
| Box spine | flat end wall, two corners | simulated | `box-spine` |
| Empty fold | nothing inside, the strip finds its own shape | simulated | `fold-styles` (free fold) |
| Unequal stacks (a trifold: each fold has its own stack) | each fold wraps a different thickness | simulated, one fold at a time | run `fold-styles --cards N` for each; the folds are not coupled |

## 2. The layup at the fold
| Construction | What it is | Status | How |
|---|---|---|---|
| Plain | one layer | simulated | `plain` |
| Skived | flesh side thinned over the fold | simulated | `skived` |
| Lined | shell + glued lining | simulated | `lined`; the lining stiffness ratio is an assumption you vary |
| Skived + lined | both | simulated | `skived+lined` |
| Hinged | thinner, softer leather across the fold | simulated | `hinged`; a bonded butt joint, no seam |
| Grain in (folded the other way) | the grain face on the inside | simulated in the solver, **not yet in the comparison table** | `flat_face="inner"`; used by the second fold of the pleat |
| Stitched hinge or seam at the fold | a seam across the fold | not modelled | needs a 3D model |

## 3. Gussets
| Construction | What it is | Status | How |
|---|---|---|---|
| V gusset | one fold, inward | simulated | one crease of `gusset` |
| S / Z accordion | two opposed folds | simulated | `gusset` (fold 1 and fold 2) |
| W / M accordion | three folds | simulated | the same two creases, one of them twice |
| n-fold zigzag | n folds | simulated | ceil(n/2) creases like fold 1, floor(n/2) like fold 2 |
| Round (U) gusset | no crease, the strip wraps the contents | simulated | `fold-styles --radius` with half the depth |
| Box gusset | flat walls, two corners | simulated | `box-spine` |
| Gusset strip sewn between two panels | in your notes, a strip as wide as the depth and as long as the stitch line | = V or U gusset | the crease or wrap is simulated; the stitch line and the corners of the opening are not |
| Gusset in a different leather | softer or thinner leather in the gusset | simulated | use the `hinged` or `lined` layups, or `--E` and `--t` |
| Pressed (set) crease | a crease pressed into permanent shape | not modelled | needs permanent set and flex data; real creases are sharper than the model's |

How the number of folds enters: for an equal-segment zigzag, the fold angle for a given opening is `2 x acos(opened fraction)` and does not depend on the number of
segments. More creases therefore share the same strain, not a lower one; each flexes whenever the gusset moves.

## 4. Edges (what the finish adds where the spine fold crosses them)
| Construction | At the spine fold | Status | How |
|---|---|---|---|
| Raw or burnished | one layer | = plain | `plain` |
| Painted | one layer plus a coat | = plain; chipping is **flagged** | `plain`, `FAILURE_MODES.md` |
| Turned (folded-over) edge, the hem | shell + the folded lip | simulated | `turned edge` |
| Turned edge, the 180 deg turn itself | leather folded around a core | closed form | `edge-turn` |
| Bound edge | a layer on each face | simulated | `bound edge` |
| Lining sewn in and turned through | shell + lining | = lined | `lined` |
| Rolled or corded edge | leather rolled around a cord | not modelled | needs a set model and a 3D edge |
| Stitched edge | stitch line near the edge | not modelled | needs a 3D model |

## 5. Which entries a wallet type uses
This is my reading of `construction.md` section 3, not a set of results.

| Wallet | Folds in it | Entries |
|---|---|---|
| Bifold | the spine around the stack; card-slot edges | sections 1 and 2; edges (4) at the top and bottom of the spine |
| Trifold | two spine folds with different stacks | section 1, one fold at a time |
| Card holder (one panel, two T-slots folded up) | thin folds around one or two cards | section 1 with a small `--cards` |
| Gusseted pouch, coin pocket, accordion card case | creases or wraps that open as it fills | section 3 |
| Turned-edge sleeve (panel + lining) | the lining edge | sections 2 and 4 |

## 6. Not covered anywhere yet
So that nothing is missing silently: zips, snaps and hardware; perforations and punched holes; wet-forming and its shrinkage; card-slot edges tearing on a card pull
(`FAILURE_MODES.md`, phase 4); anything three-dimensional (corners, stitching, the 3D shape of a gusset opening); drops (phase 5).

## 7. Commands
```
walletsim fold-styles [--cards N | --radius R] [--styles ...]   plain, skived, lined, skived+lined, hinged, turned edge, bound edge
walletsim box-spine   [--style plain] [--corners ...]            flat-walled spine against a round one
walletsim gusset      [--angles ... | --expansion ...]           V / S / W creases at several openings
walletsim edge-turn                                              the 180 deg turn of a turned edge
```
