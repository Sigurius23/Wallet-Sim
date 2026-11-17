# Fold styles: simulating how a leather folds

Focus of the project, ahead of the UI: simulate different **bending styles**, and let the leather and its thickness be
swapped. This page says what exists, what it showed, how far to trust it, and what is missing.

```
walletsim fold-styles                      # 5 styles, 5-card stack, 1.2 mm leather, E = 72 MPa; about 12 s on 4 cores
walletsim fold-styles --cards 10 --t 1.6 --E 50 --lining-e-ratio 0.25
walletsim fold-styles --styles plain skived --radius 3
walletsim gusset                           # accordion pleat at four opening angles; about 17 s
walletsim gusset --expansion 0.25 0.5 0.75 0.9   # the same, by how far the gusset has opened
walletsim box-spine                        # flat-walled spine against a round one, same stack; about 30 s
walletsim edge-turn                        # the 180 deg turn of a turned edge (closed form)
```

## 1. What a "style" is here
A wallet fold is a strip with a **layup along its length**. One model covers every style by changing that layup
(`src/walletsim/fem/fold.py`, styles in `fold_styles.py`):

| Style | Layup | Parameters (all editable) |
|---|---|---|
| plain | one layer, constant thickness | thickness, E |
| skived | flesh side thinned over the fold, grain face stays flat | thickness left (default 0.5 t), width 6 mm + 3 mm tapers |
| lined | shell plus a glued lining | lining thickness (0.5 mm), **lining E / shell E (default 1, an assumption)** |
| skived + lined | both | as above |
| hinged | thinner, softer leather across the fold zone, bonded butt joint | hinge width 8 mm, thickness 0.6 t, E 0.5 x |
| turned edge (hem) | shell plus the folded-over lip of the same leather, glued flesh to flesh, where the spine fold crosses the hem | lip thickness 0.5 t |
| bound edge | shell with a binding strip folded over the edge, one layer on each face where the spine crosses it | binding 0.4 t per face, same leather |
| gusset (pleat) | V, S/Z and W/M gussets: two opposed folds of a strip with a skived crease groove, at several opening angles; its own command, section 4 | groove width 2 mm, tapers 1.5 mm, depth 0.5 t |
| box spine | stack with a flat end wall and two corners instead of a half-round; its own command, section 5 | corner radius, wall height |

A new style is a function that returns a tuple of `Layer`s (thickness profile along the strip, stiffness, optional stiffness zones);
it needs no change to the solver.

## 2. Two load cases, because they answer different questions
- **A. Free fold.** A 180 deg fold with nothing inside, 15 mm of strip each side of the fold centre. Moment-controlled: the strip
  finds its own shape, so it shows **where each construction bends** and how hard it resists.
- **B. Wrap.** The strip folds around a rigid rounded stack (cards and bills), frictionless contact. Radius-controlled, which is
  what the contents of a wallet impose: it shows **what the leather sees when the wallet is closed**. Run **loose** (the leather
  simply lies on the stack), **taut** (a pull of 0.1 N per mm on the panel), and against the **limit** (leather follows the stack
  exactly; a closed form, no solver). A real wallet lies between loose and the limit; the pull from the closed panels is unknown.

Both are symmetric halves of the fold (the symmetry plane is the fold centre). Plane strain: a wallet is wide compared with its
leather, so the width direction is held.

## 3. Results (1.2 mm leather, E = 72 MPa, 5 cards = inside radius 1.9 mm, R/t = 1.6)

**A. Free fold**

| Style | Closing moment [N mm per mm] | Tension face | Compression face | Share of the 180 deg in the central 8 mm |
|---|---|---|---|---|
| plain | 1.19 | 6.5 % | -6.1 % | 27 % (even) |
| skived | 0.42 | 9.5 % | -8.7 % | **70 %** |
| lined | 3.37 | 9.2 % | -8.6 % | 27 % |
| skived + lined | 1.93 | 12.9 % | -12.0 % | 54 % |
| hinged | 0.32 | 9.9 % | -9.0 % | **66 %** |
| turned edge (hem) | 4.00 | 9.8 % | -9.1 % | 27 % |
| bound edge | 6.88 | 11.8 % | -10.8 % | 27 % |

**B. Wrap around the stack** (tension-face strain; stand-off = how far the loose leather bridges the stack)

| Style | Loose | Taut | Limit (closed form) | Compression face (taut) | Stand-off, loose | Closing moment, taut [N mm per mm] |
|---|---|---|---|---|---|---|
| plain | 16.9 % | 17.9 % | 24.0 % | -15.6 % | 0.89 mm | 3.28 |
| skived | 12.7 % | 14.5 % | 13.6 % | -12.6 % | 0.24 mm | 0.63 |
| lined | 22.7 % | 23.2 % | 30.9 % | -20.8 % | 0.92 mm | 8.39 |
| skived + lined | 20.1 % | 20.6 % | 22.4 % | -18.1 % | 0.28 mm | 3.14 |
| hinged | 13.4 % | 16.4 % | 15.9 % | -13.9 % | 0.45 mm | 0.53 |
| turned edge (hem) | 24.0 % | 24.6 % | 32.1 % | -22.0 % | 0.82 mm | 9.80 |
| bound edge | 27.3 % | 27.7 % | 36.2 % | -24.9 % | 0.94 mm | 16.07 |

Moments are per mm of wallet width; multiply by the width in mm.

### What it says
1. **The ranking depends on the load case.** Skiving and a hinge *raise* the strain in a free fold (they gather the bend in the thin
   zone: +46 % and +52 % tension-face strain here) but *lower* it around a stack (skived -19 % taut, -25 % loose; hinged -8 % taut,
   -21 % loose), because the leather there is thinner. A claim like "skiving reduces strain" holds only when the radius is imposed.
   Both cut the closing moment in either case: 3 to 4 times in a free fold (1.19 against 0.42 and 0.32) and 5 to 6 times around the
   stack (taut: 3.28 against 0.63 and 0.53).
2. **A lining on the inside of the fold costs the shell.** It moves the shell farther from the neutral axis: +30 % tension-face strain
   (taut; +34 % loose) and 2.6 times the closing moment, at equal stiffness. This is a geometric effect, not a leather property.
3. **The lining's stiffness decides how much.** The lining/shell stiffness ratio is an assumption, and it moves the answer by a factor
   of 1.6: lined, taut tension face 18.7 % at ratio 0.25, 23.2 % at 1, **30.7 % at 4** (closing moment 4.9, 8.4, 13.6). If the lining
   is the stiffer layer, the shell takes the hit, so the lining's stiffness is worth measuring.
4. **Skiving the shell under a lining recovers part of it** (20.6 % taut against 23.2 % lined, moment 3.1 against 8.4).
5. **A tight stack is not fully hugged.** At R/t = 1.6 the textbook value `t/(2R+t)` is 24 %, while the loose FEM gives 17 %, because the
   leather bridges the stack. The closed form is an upper bound there; it is accurate when the leather does hug it (stacks of
   10 cards, R/t = 3.2: loose 12.7 %, taut 14.0 %, closed form 13.6 %).
6. **Hinge: lowest closing effort, strain between plain and skived.** Its taut strain exceeds its own closed-form limit by 3 % at
   5 cards and 20 % at 10 cards. I suspect strain collects where the thick panel meets the thin soft zone, but I have not tested that,
   and I have not varied the hinge width (8 mm here), which probably matters.

### Different stack sizes (taut tension face / limit)

| Style | 2 cards, R = 0.76 mm (R/t 0.6) | 5 cards, R = 1.9 mm | 10 cards, R = 3.8 mm |
|---|---|---|---|
| plain | 22.3 % / 44.1 % | 17.9 % / 24.0 % | 14.0 % / 13.6 % |
| skived | 17.1 % / 28.3 % | 14.5 % / 13.6 % | 9.8 % / 10.3 % |
| lined | 28.7 % / 52.8 % | 23.2 % / 30.9 % | 17.8 % / 18.3 % |
| skived + lined | 24.4 % / 42.0 % | 20.6 % / 22.4 % | 14.8 % / 15.7 % |
| hinged | 20.6 % / 32.1 % | 16.4 % / 15.9 % | 11.3 % / 9.4 % |
| turned edge (hem) | 29.9 % / 54.2 % | 24.6 % / 32.1 % | 18.2 % / 19.1 % |
| bound edge | 33.3 % / 58.7 % | 27.7 % / 36.2 % | 21.0 % / 22.1 % |

The hem is a bonded double layer, so it behaves like the lined row with a thicker lip, and the bound edge, which adds a layer on each face, is the most strained and stiffest construction here. At 2 cards the geometry is below the project's R/t = 1 floor (`fold_screen`): the grain relies on the finish, and the numbers are
kinematic, not a prediction of the leather.

### Damage rate per fold, relative to plain
`rate = (strain / strain_plain)^m`. No leather-specific exponent m is known, so both ends of the plausible range are printed, and
the answer is the range. Example (5 cards, wrap, taut, m = 3 to 12): skived 0.53x to 0.08x, lined 2.2x to 23x, skived + lined 1.5x to 5.5x,
hinged 0.77x to 0.36x. These are **relative** and uncalibrated; they say which construction is gentler, not how many folds anything lasts.
Absolute cycles come only from `walletsim fit-law` on flex-test data from the same leather.

## 4. Gusset: the accordion pleat
`walletsim gusset`. I read "gusset" as the pleat that lets a wallet expand: a strip folded into an S, two opposed folds, opening as the
wallet fills. (A box-shaped gusseted spine, a flat wall between two corner bends, is a different construction and is not built yet.)
Each fold is a **free fold at the pleat's opening angle** (180 deg = collapsed, smaller = open), with a skived crease groove that localises
the bend. Fold 1 has the grain outside; fold 2, the mirror fold of the S, has it inside (the layers reversed and the grain face kept flat
on the inside). Shell 1.2 mm, E = 72 MPa, flesh side skived to 0.5 t over a 2 mm groove with 1.5 mm tapers:

| Fold angle | Closing moment [N mm per mm] | Crease radius | Fold 1 grain face (tension) | Fold 2 grain face (compression) | Fold 2 back face (tension) |
|---|---|---|---|---|---|
| 180 deg (collapsed) | 0.70 | 2.0 mm | 16.0 % | -14.0 % | 16.0 % |
| 135 deg | 0.52 | 2.7 mm | 11.8 % | -10.6 % | 11.8 % |
| 90 deg | 0.35 | 4.0 mm | 7.7 % | -7.2 % | 7.7 % |
| 45 deg | 0.18 | 8.1 mm | 3.8 % | -3.7 % | 3.8 % |

What it says:
1. **The groove is what makes a pleat.** An unskived strip folded 180 deg forms a wide U (neutral radius 9.7 mm, 20 % of the bend in the central
   6 mm, grain strain 6.5 %); the 2 mm groove puts 53 % of the bend there, with a 2.0 mm radius, 2.5 times the grain strain and 0.6 times the moment.
2. **Strain follows the opening angle** (16.0, 7.7, 3.8 % at 180, 90, 45 deg). What repeats each time the pleat opens and closes is the swing:
   8.3 points on the fold 1 grain face between collapsed and half open (6.7 on fold 2).
3. **Groove width trades crease sharpness against strain.** At 180 deg:

   | Groove width (thinnest part) | 1 mm | 2 mm | 4 mm | 6 mm |
   |---|---|---|---|---|
   | Fold 1 grain strain | 15.9 % (+-1 point) | 16.0 % | 12.4 % | 10.1 % |
   | Crease radius | 2.0 mm | 2.0 mm | 2.6 mm | 3.2 mm |
   | Closing moment | 0.81 | 0.70 | 0.55 | 0.45 |
   | Swing, 180 to 90 deg | 8.3 points | 8.3 | 6.3 | 5.1 |

   Wider grooves lower the strain, the swing and the push-back but make a blunter crease. Below about 2 mm the strain stops rising: the
   softened zone (thin part plus tapers) matters, not the thin part alone.
4. **Both faces get loaded.** The S loads the grain in tension at one crease and in compression at the other, and the flesh (back) face reaches the same
   16 % in tension at fold 2 that the grain reaches at fold 1. Which side is the more vulnerable is a leather property that is not known here.
5. **A lining stiffens the pleat 3.7 times at 180 deg** (moment 2.58 against 0.70), blunts the crease (radius 3.3 mm, grain 15.5 %) and, in fold 2, sits on the
   outside where it takes the highest tension (16.3 %).

**By how far the gusset has opened.** The fold angle of every crease of an equal-segment zigzag is set by how much of its unfolded length the gusset has opened
(`walletsim gusset --expansion`): extension = length x cos(fold angle / 2). The grooved layup:

| Opened by | Fold angle | Crease radius | Fold 1 grain (tension) | Fold 2 grain (compression) | Closing moment |
|---|---|---|---|---|---|
| 25 % | 151 deg | 2.4 mm | 13.3 % | -11.8 % | 0.59 |
| 50 % | 120 deg | 3.0 mm | 10.4 % | -9.5 % | 0.47 |
| 75 % | 83 deg | 4.4 mm | 7.1 % | -6.7 % | 0.32 |
| 90 % | 52 deg | 7.1 mm | 4.4 % | -4.2 % | 0.20 |

**Kinds of gusset.** The same two creases build all the zigzag kinds: a **V** gusset (one fold) has one crease, an **S/Z** accordion two (one grain out, one grain in), a **W/M**
three (two and one), and an n-fold zigzag has ceil(n/2) of one kind and floor(n/2) of the other. Because the fold angle for a given opening does not depend on the number of
segments, **more creases do not lower the strain per crease: they put the same strain on more creases**, each of which flexes every time the gusset moves. A **round (U)
gusset** has no crease (the strip wraps the contents: `fold-styles --radius` with half the depth), and a **box gusset** has flat walls and two corners: section 5.

Limits specific to the pleat: a real pleat is usually pressed into a sharper crease, which needs permanent set that this model does not have, so
real creases are tighter and more strained than these. Contact between the two legs and with the contents is not modelled; the model only checks that
the inner face stays on its own side of the symmetry plane (it does in every case reported). The stitching along the gusset edges, which is a 3D feature, is not modelled either.

## 5. Box-shaped spine (flat end wall)
`walletsim box-spine`. The same stack as before (5 cards, half thickness 1.9 mm), but its end is a flat wall with two corners instead of a half-round. Plain layup,
shell 1.2 mm, E = 72 MPa. The tension-face strain is at the corner:

| Corner radius | Flat wall | Loose | Taut | Limit (follows the corner exactly) | Compression face (taut) | Stand-off, loose |
|---|---|---|---|---|---|---|
| 1.9 mm | none (round) | 16.9 % | 17.9 % | 24.0 % | -15.6 % | 0.89 mm |
| 1.5 mm | 0.8 mm | 17.7 % | 18.8 % | 28.6 % | -16.0 % | 0.71 mm |
| 1.0 mm | 1.8 mm | 18.8 % | 19.8 % | 37.5 % | -16.6 % | 0.72 mm |
| 0.5 mm | 2.8 mm | 20.1 % | 21.1 % | 54.5 % | -17.5 % | 0.61 mm |

- **A flat wall costs strain**, but less than the closed form suggests: halving the corner radius from 1.0 to 0.5 mm raises the textbook value from 38 % to 55 % and the
  model's loose value from 18.8 % to 20.1 %. The leather bridges the corner (stand-off 0.6 to 0.7 mm), so it never turns as tight as the corner.
  A real corner is pressed and set, so the true strain is probably between the model and the limit.
- **Layups change the size, not the trend:** skived 12.7 % (round) to 17.8 % (0.5 mm corners), lined 22.7 % to 25.6 % (loose, same stack).
- No closing moment is given: the solver measures it at the fold centre, the middle of the flat wall, so it cannot be compared with the round spine's.
- Check: at a gentle corner (R = 8 mm) the model matches the closed form within 1 %, for walls of 2 mm and 5 mm half-height; a box with no wall reproduces the round spine exactly.

## 6. Edges: turned, bound, and the rest
Which way the cut edge is finished matters here only through what it adds to the strip where the spine fold crosses it.

| Edge | At the spine fold | Status |
|---|---|---|
| raw or burnished | one layer, as plain | = `plain` |
| painted | one layer plus a coat | = `plain`; the coat is not modelled, only its chipping is a known failure (`FAILURE_MODES.md`, flagged) |
| turned (folded over) | the hem: shell + folded lip | simulated (`turned edge`); the 180 deg turn itself is closed form only |
| bound | a layer on each face | simulated (`bound edge`) |
| bag-out (lining sewn in and turned through) | shell + lining | = `lined` |

### Turned edge
Two different things happen at a turned edge, and only one can be simulated here.

**The hem where the spine fold crosses it (simulated).** The strip there is the shell plus the folded-over lip, a double layer; that is the 'turned edge (hem)'
row in section 3. Compared with a plain spine it takes **+37 % tension-face strain (taut; +42 % loose) and 3.0 times the closing moment**, and the
effect is similar at other stack sizes (+34 % at 2 cards, +30 % at 10). So the edge zone of the spine is where the strain is highest. The lip is
assumed to be the same leather as the shell, skived to 0.5 t, perfectly bonded. This is mechanically a lining of the same leather, which is why it resembles the lined row.

**Bound edge.** A binding strip folded over the edge leaves a layer on each face, so the strip at the spine is three layers and about 80 % thicker (1.2 mm becomes 2.16 mm
with a 0.48 mm binding on each face, same leather, perfectly bonded: assumptions you can change). Around the 5-card stack its tension face takes 27.7 % (taut), **+55 %
against a plain spine, with 4.9 times the closing moment**, and 21.0 % even at 10 cards. This is the highest-strain construction in the table, and it is flagged above the 20 % screening threshold.

**The 180 deg turn itself (closed form only).** `walletsim edge-turn` gives the strain the leather would see if it followed the core exactly:

| Leather at the turn (1.2 mm leather, skive ratio) | Core 0.6 mm | Core 0.3 mm | Core 0.1 mm |
|---|---|---|---|
| 1.2 mm (1.0) | 67 % | 80 % | 92 % |
| 0.6 mm (0.5) | 50 % | 67 % | 86 % |
| 0.42 mm (0.35) | 41 % | 58 % | 81 % |
| 0.3 mm (0.25) | 33 % | 50 % | 75 % |

Every entry is far above the 20 % screening threshold: to stay at 20 % the leather at the turn would have to be 0.15 mm thick around a 0.6 mm core and
0.075 mm around a 0.3 mm core. Strains like these are not elastic, so a real turn must rely on permanent deformation, thinning and the glue. The model has
none of those, so it **cannot say whether a turn survives**; it can only show that skiving lowers the kinematic strain. An elastic FEM of this turn was
tried and rejected: around a 0.3 to 0.6 mm core the leather simply bridges the gap (10 to 22 % against 41 to 80 % kinematic), because nothing in the model presses and
glues it down. To simulate the turn, we need a permanent-set model and measured crease or flex data, plus the maker's skive depth at the turn and the core used.

## 7. Swapping the leather
What changes with the leather, and what does not:

| Input | Effect | Evidence in this repo |
|---|---|---|
| Stiffness E (single layer) | closing moment scales with E; **strain does not** | E = 36 / 72 / 144 MPa: moment 0.60 / 1.19 / 2.38 N mm per mm, free-fold strains identical (6.5 %), loose wrap strain identical (16.9 %). The taut case varies a little (18.8 / 17.9 / 17.4 %) because the pull is a fixed force |
| Thickness t | strain and stiffness both change | `walletsim sweep`, see `MATERIALS.md` |
| Stiffness **ratio** between layers or zones | changes strain, not only moment | lining ratio 0.25 / 1 / 4 above |
| Strain the leather survives | decides whether a strain is safe | **unknown until flex tests exist** (`fit-law`) |
| Ageing | a different stiffness and strain limit | measured aged states only (`MATERIALS.md`); nothing here predicts it |

So *which style is gentler* is mostly geometry and layer-stiffness ratios, and it carries over between leathers. *Whether a given
leather survives it* needs that leather's measured behaviour. Right now only one cited number exists (calfskin upper, tensile
72 N/mm2, CV 29 %; see `MATERIALS.md`), so each leather beyond that is a number you supply with `--E` and `--t`.

## 8. Validation
| Check | Result |
|---|---|
| Free fold vs composite-beam closed form (Poisson 0, t = 1.4 mm): plain / skived / lined | moment ratio 0.994 / 0.981 / 0.988 (lining E/3: 1.003); tension-face strain within 3 % of the peak; the share of the fold in the thin zone agrees (0.78 vs 0.77) |
| Wrap vs taut closed form at a gentle radius (R = 8 mm, t = 1.4 mm, Poisson 0): plain / lined | 8.21 % vs 8.05 % / 11.36 % vs 11.11 % (+2 %); the lined case also checks the neutral-axis shift |
| Mesh: element length 0.5 mm against 0.25 mm | peak strains differ by 0.5 points or less, moments by under 6 % |
| Contact | deepest penetration of the leather into the stack over all 30 wrap runs in the tables: 0.005 mm or less, except one run (skived, 10 cards, loose) at 0.083 mm (7 % of t) at the first node of the bend, outside the strain window |
| Stiffness scaling | exact (see section 7) |
| Box-ended stack vs closed form, R = 8 mm, walls of 2 and 5 mm | within 1 %; no wall reproduces the round spine exactly |
| Grain-in fold (reversed layers, grain face kept flat on the inside) vs composite-beam closed form | lined layup: moment within 4 %, tension-face strain within 4 % |
| Pleat mesh convergence (element 0.5, 0.25, 0.125 mm) | closing moment and crease radius within 1 %; grain strain within 0.2 points for grooves of 2 mm and wider, about +-1 point for a 1 mm groove |

Tests: `tests/test_fold.py` (30), including the closed forms without a solver.

## 9. Limits: read before using a number
- The leather is **isotropic, homogeneous, neo-Hookean**, with E and Poisson 0.3 (assumed; the 0.6 measured by hand in the cited paper
  is a lateral-contraction figure, not a bulk value). Real leather is fibrous, layered, anisotropic and viscoelastic.
- **Not modelled:** permanent set and creep, finish-film cracking, glue-line shear and
  delamination (layers are perfectly bonded, no adhesive thickness), stitching and edges, friction, the effect of moisture, ageing.
  The pleat and the hem add: no leg-to-leg contact, no pressed crease, and no model of the turn itself (section 6).
  Skiving is also modelled as a smooth taper with a flat grain face; real skiving leaves a rougher, weaker flesh side.
- Above about 20 % strain the numbers are kinematic: the neo-Hookean model is not validated there, and the table marks those cases.
- **Stand-off is the least converged output**: halving the element length moved it from 0.73 to 0.89 mm for plain at 5 cards. Strains
  and moments are stable; use stand-off to see *that* leather bridges the stack, not how far.
- **Taut is a stated pull**, not a measured one. If the real tension in a closed wallet is different, the truth moves between
  loose and the limit.
- The wallet is treated as wide (plane strain). Narrow parts (straps, edges) need a 3D model.
- The defaults for lining stiffness ratio (1), hinge thickness and stiffness ratios (0.6, 0.5) are assumptions chosen to be neutral
  or illustrative, not leather properties. The card thickness 0.76 mm is the nominal ISO/IEC 7810 ID-1 value.

## 10. Next steps, in order of value
1. **Your wallet's real fold:** measure the inside radius and layup from the capture photos, then run it as a style.
2. **Measured leather cards** (offcut strips: thickness, a bend test for stiffness, along/across the backbone); lining stiffness first,
   since it moves the result most.
3. **More styles:** a stitched hinge with a seam, grain-in wraps around a stack (the solver supports them, `flat_face="inner"`; they are not in the comparison table yet),
   the width of the hem lip and of the binding, and rolled or corded edges. The catalogue of what exists and what does not is `CONSTRUCTIONS.md`.
4. **Permanent set and wear:** needs flex data from your leathers; this is what turns the relative damage rate into cycles, and it is what
   a pressed pleat crease and a turned-edge turn depend on.
5. **A full-wallet model** that uses these fold results per spine, then card pulls and drops (phases 3 to 5 of the roadmap).
