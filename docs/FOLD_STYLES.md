# Fold styles: simulating how a leather folds

Focus of the project, ahead of the UI: simulate different **bending styles**, and let the leather and its thickness be
swapped. This page says what exists, what it showed, how far to trust it, and what is missing.

```
walletsim fold-styles                      # 5 styles, 5-card stack, 1.2 mm leather, E = 72 MPa; about 12 s on 4 cores
walletsim fold-styles --cards 10 --t 1.6 --E 50 --lining-e-ratio 0.25
walletsim fold-styles --styles plain skived --radius 3
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

**B. Wrap around the stack** (tension-face strain; stand-off = how far the loose leather bridges the stack)

| Style | Loose | Taut | Limit (closed form) | Compression face (taut) | Stand-off, loose | Closing moment, taut [N mm per mm] |
|---|---|---|---|---|---|---|
| plain | 16.9 % | 17.9 % | 24.0 % | -15.6 % | 0.89 mm | 3.28 |
| skived | 12.7 % | 14.5 % | 13.6 % | -12.6 % | 0.24 mm | 0.63 |
| lined | 22.7 % | 23.2 % | 30.9 % | -20.8 % | 0.92 mm | 8.39 |
| skived + lined | 20.1 % | 20.6 % | 22.4 % | -18.1 % | 0.28 mm | 3.14 |
| hinged | 13.4 % | 16.4 % | 15.9 % | -13.9 % | 0.45 mm | 0.53 |

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

At 2 cards the geometry is below the project's R/t = 1 floor (`fold_screen`): the grain relies on the finish, and the numbers are
kinematic, not a prediction of the leather.

### Damage rate per fold, relative to plain
`rate = (strain / strain_plain)^m`. No leather-specific exponent m is known, so both ends of the plausible range are printed, and
the answer is the range. Example (5 cards, wrap, taut, m = 3 to 12): skived 0.53x to 0.08x, lined 2.2x to 23x, skived + lined 1.5x to 5.5x,
hinged 0.77x to 0.36x. These are **relative** and uncalibrated; they say which construction is gentler, not how many folds anything lasts.
Absolute cycles come only from `walletsim fit-law` on flex-test data from the same leather.

## 4. Swapping the leather
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

## 5. Validation
| Check | Result |
|---|---|
| Free fold vs composite-beam closed form (Poisson 0, t = 1.4 mm): plain / skived / lined | moment ratio 0.994 / 0.981 / 0.988 (lining E/3: 1.003); tension-face strain within 3 % of the peak; the share of the fold in the thin zone agrees (0.78 vs 0.77) |
| Wrap vs taut closed form at a gentle radius (R = 8 mm, t = 1.4 mm, Poisson 0): plain / lined | 8.21 % vs 8.05 % / 11.36 % vs 11.11 % (+2 %); the lined case also checks the neutral-axis shift |
| Mesh: element length 0.5 mm against 0.25 mm | peak strains differ by 0.5 points or less, moments by under 6 % |
| Contact | deepest penetration of the leather into the stack over all 30 wrap runs in the tables: 0.005 mm or less, except one run (skived, 10 cards, loose) at 0.083 mm (7 % of t) at the first node of the bend, outside the strain window |
| Stiffness scaling | exact (see section 4) |

Tests: `tests/test_fold.py` (17), including the closed forms without a solver.

## 6. Limits: read before using a number
- The leather is **isotropic, homogeneous, neo-Hookean**, with E and Poisson 0.3 (assumed; the 0.6 measured by hand in the cited paper
  is a lateral-contraction figure, not a bulk value). Real leather is fibrous, layered, anisotropic and viscoelastic.
- **Not modelled:** permanent set and creep, finish-film cracking, grain-in folds of skived or lined layups, glue-line shear and
  delamination (layers are perfectly bonded, no adhesive thickness), stitching and edges, friction, the effect of moisture, ageing.
  Skiving is also modelled as a smooth taper with a flat grain face; real skiving leaves a rougher, weaker flesh side.
- Above about 20 % strain the numbers are kinematic: the neo-Hookean model is not validated there, and the table marks those cases.
- **Stand-off is the least converged output**: halving the element length moved it from 0.73 to 0.89 mm for plain at 5 cards. Strains
  and moments are stable; use stand-off to see *that* leather bridges the stack, not how far.
- **Taut is a stated pull**, not a measured one. If the real tension in a closed wallet is different, the truth moves between
  loose and the limit.
- The wallet is treated as wide (plane strain). Narrow parts (straps, edges) need a 3D model.
- The defaults for lining stiffness ratio (1), hinge thickness and stiffness ratios (0.6, 0.5) are assumptions chosen to be neutral
  or illustrative, not leather properties. The card thickness 0.76 mm is the nominal ISO/IEC 7810 ID-1 value.

## 7. Next steps, in order of value
1. **Your wallet's real fold:** measure the inside radius and layup from the capture photos, then run it as a style.
2. **Measured leather cards** (offcut strips: thickness, a bend test for stiffness, along/across the backbone); lining stiffness first,
   since it moves the result most.
3. **More styles:** accordion / gusset (two opposed folds), turned (double) edge, grain-in folds, a stitched hinge with a seam.
4. **Permanent set and wear:** needs flex data from your leathers; this is what turns the relative damage rate into cycles.
5. **A full-wallet model** that uses these fold results per spine, then card pulls and drops (phases 3 to 5 of the roadmap).
