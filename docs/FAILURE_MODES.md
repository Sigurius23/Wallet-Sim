# Failure modes: what the simulator will report, and what it cannot

"Strengths and weaknesses of each wallet" means a list of the ways it can fail, in order. This catalogue is built from
the earlier research (`prior-research/reference/durability.md`, `treatments/`), whose confidence tags (checked or
single-source) are carried over; I have not independently re-verified them except where a source is linked in `MATERIALS.md`.

Legend: **computed** = a number comes out of the simulator; **flagged** = a geometric or material rule raises a warning;
**not modelled** = out of reach today, and the report says so for every wallet.

| # | Failure mode | Where in a wallet | Mechanism | Decided by | In walletsim |
|---|---|---|---|---|---|
| 1 | **Grain crack at the hinge** | spine fold | outer-fibre tension, `t/(2R+t)`, rising as radius falls | thickness, fold radius, temper | **computed** (strain, FEM); cycles only after flex-test calibration |
| 2 | **Permanent set**: a soft, floppy crease that no longer returns flat, plus grain coarsening | spine fold | fibrils stop sliding inside the bundle after repeated flexing; the usual *first* visible sign, before any crack | fatliquor, hydration, retan | **not modelled** (needs a cyclic viscoplastic model). Measure it: fold strips N times, record the angle they return to |
| 3 | **Finish crazing or delamination** | surface of any fold | stiff film on a soft substrate wrinkles or creases at 2-12 % strain, well below the bulk strain; or the film peels | finishing window, adhesion | **not modelled**. Diagnose by looking: crazing without lifting means a well-bonded film, lifting or flaking means an adhesion fault |
| 4 | **Stress at stitch holes** | stitch runs near the hinge | a hole removes ~90 % of the section over its diameter; stress mid-stitch up to 4-5x the ends of a run (FEA of stitched leather) | stitch layout | **flagged** when a run crosses a high-curvature zone; local refined model later |
| 5 | **Skive-line or thickness step** | folded edges, layered stacks | a thickness step is a stiffness discontinuity, the same place cracks start | skiving | **flagged** from the thickness map |
| 6 | **Edge paint chipping** | edges at a flex | paint is a consumable and chips where the edge flexes | edge treatment | **flagged**: painted edge at a fold. Hand-burnished edges (vegetable tanned) are far more durable |
| 7 | **Pocket-mouth and corner abrasion** | card slots, corners | sliding contact on every card pull; wear ~ pressure x sliding distance | finish, slot geometry | **computed relative** from the card-pull scenario (phase 4); calibrate against wear photos |
| 8 | **Perforation tear line** | any pierced line | a row of holes across the bend is a tear-initiation line | design | **flagged** when holes cross a fold |
| 9 | **Layer delamination** | backed or doubled panels | adhesive or backing separates | construction | **not modelled** |
| 10 | **Cold embrittlement** | whole wallet | flex life drops sharply with temperature: ~4x between 23 C and -10 C in one automotive comparison (a single comparison, not a law) | tannage, fat | scenario parameter, **needs a cold flex test**; no built-in factor |
| 11 | **Wet and salt flex** | whole wallet | wet flex is a harsher regime; salt accelerates it | finish, tannage | **not modelled** (needs wet flex test) |
| 12 | **Over-drying** | whole wallet | low hydration raises strength but kills elongation: the hinge stops bending before it stops pulling | conditioning, ageing | **material state** with measured stiffness and strain to crack |
| 13 | **Long-term chemical ageing** | whole wallet | iron-mordanted blacks embrittle over decades (a 5-10 year expected life is the craft guidance); vegetable-tanned leather acidifies and de-tans as it degrades; aldehyde tannages yellow in UV | tannage, dye, storage | **material states** from measured aged strips; no time-axis prediction |
| 14 | **Colour, patina, water spotting** | surface | appearance only | tannage, finish | **not modelled** (patina is not a measurable property) |

## How a wallet's report will read
For each wallet the report lists the modes in order of **how early they are expected to act**, shows which ones were
computed, flagged or not modelled, and states the material inputs behind every number (measured, literature or assumed). A
mode that is "not modelled" is never silently omitted: leaving out permanent set, for instance, would hide the most common
way a real hinge starts to fail.

## Order of work
1, 4, 5, 6, 8 come with the first assembled wallet (phases 2-3). 7 follows with the card-pull scenario (phase 4). 2, 3, 9 and
11 need models that do not exist yet and are listed in `ROADMAP.md` as research items.
