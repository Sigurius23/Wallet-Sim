# Overall wallet fold types

`walletsim wallet-types`. A wallet type is a set of folds. In the closed wallet each fold wraps a different stack, and that stack sets its inside radius, so the
type decides how hard each fold works. This page covers bifold, trifold (letter fold) and z-fold (accordion), and which fold in each wears first. How the
individual folds are modelled is in [`FOLD_STYLES.md`](FOLD_STYLES.md); every construction and its status is in [`CONSTRUCTIONS.md`](CONSTRUCTIONS.md).

```
walletsim wallet-types                               # bifold, trifold, 3- and 4-panel z-fold; 8 cards; about 40 s
walletsim wallet-types --cards 12 --types bifold trifold:0.3 z-fold:5
walletsim wallet-types --layup lined --slot-leather 0.5      # pocket leather adds to the stack
walletsim wallet-types --spine box --corner 1.0              # flat-walled spines
walletsim wallet-types --cycles spine=2                      # a fold that opens twice per use
walletsim wallet-types --list                                # what is the same fold under another name
```

## 1. The types, and the stack each fold wraps
| Type | Panels | Folds | Stack wrapped by each fold | Grain |
|---|---|---|---|---|
| bifold | 2 | 1 (the spine) | all the contents | out |
| trifold (letter fold) | 3 | 2, nested | inner fold: its share of the contents (default half). Outer fold: **all the contents plus one folded-in panel** | out, out |
| z-fold (accordion), n panels | n | n - 1 | an equal share of the contents each | out, in, out, ... |

The same fold under another name (`--list`): a long (continental) wallet, a passport cover (the passport is contents: `--extra-mm`), a one-fold card holder, a slim sleeve,
a book-style bifold are all the bifold; a concertina card case is a z-fold. They differ in panel size and contents, not in the fold.

A fold's stack is the contents it wraps (cards 0.76 mm each, plus anything extra, plus pocket leather if you set it) and, for the outer fold of a trifold, one panel.
Its inside radius is half that, round spine by default (`--spine box` gives a flat wall with corners). Each fold is then run through the wrap model of `FOLD_STYLES.md`,
loose and lightly taut.

## 2. Results: 8 cards (6.08 mm of contents), plain 1.2 mm leather, E = 72 MPa, round spines
Tension-face strain; "limit" is the textbook value if the leather followed the stack exactly. Moment is at the fold centre, N mm per mm of width.

| Type | Fold | Grain | Stack | Radius (R/t) | Loose | Taut | Limit | Grain face (taut) | Moment |
|---|---|---|---|---|---|---|---|---|---|
| bifold | spine | out | 6.08 mm | 3.04 mm (2.5) | 14.1 % | 15.2 % | 16.5 % | +15.2 % | 2.79 |
| trifold | inner fold (M\|R) | out | 3.04 mm | 1.52 mm (1.3) | 18.3 % | 19.5 % | 28.3 % | +19.5 % | 3.48 |
| trifold | outer fold (L\|M) | out | 7.28 mm | 3.64 mm (3.0) | 12.9 % | 13.9 % | 14.2 % | +13.9 % | 2.57 |
| z-fold, 3 panels | fold 1 | out | 3.04 mm | 1.52 mm (1.3) | 18.3 % | 19.5 % | 28.3 % | +19.5 % | 3.48 |
| z-fold, 3 panels | fold 2 | in | 3.04 mm | 1.52 mm (1.3) | 18.3 % | 19.5 % | 28.3 % | **-16.8 %** | 3.48 |
| z-fold, 4 panels | folds 1 and 3 | out | 2.03 mm | 1.01 mm (0.8) | 20.1 % | 21.4 % | 37.2 % | +21.4 % | 3.77 |
| z-fold, 4 panels | fold 2 | in | 2.03 mm | 1.01 mm (0.8) | 20.1 % | 21.4 % | 37.2 % | -18.3 % | 3.77 |

| Type | Closed thickness | Worst fold (taut) | Damage rate of the worst fold vs the bifold's, m = 3 to 12 | Total moment |
|---|---|---|---|---|
| bifold | 8.5 mm | spine, 15.2 % | 1x | 2.79 |
| trifold | 9.7 mm | inner fold, 19.5 % | 2.1x to 20x | 6.04 |
| z-fold, 3 panels | 9.7 mm | folds 1 and 2 tied, 19.5 % | 2.1x to 20x | 6.95 |
| z-fold, 4 panels | 10.9 mm | all three folds tied, 21.4 % (above the 20 % screen) | 2.8x to 62x | 11.31 |

### What it says
1. **The more folds share the contents, the tighter each fold.** The bifold has one fold around everything and the largest radius, so the lowest strain (15.2 %).
   The z-fold with 4 panels splits the same cards three ways and every fold reaches 21.4 %. The damage rate is a ratio of strains to the power m, so the trifold's 28 % higher
   worst-fold strain (19.5 against 15.2 %) is 2.1x at m = 3 and 20x at m = 12, and the 4-panel z-fold's 41 % is 2.8x and 62x; the exponent is not known, so the range is the answer.
2. **In a trifold the inner fold wears first, and the outer fold is the gentlest fold in the table.** The outer fold wraps the whole pack plus a folded-in panel
   (7.28 mm against the bifold's 6.08 mm), so its strain (13.9 %) is below the bifold spine's (15.2 %). That is a result of the nesting, and it needs the 3D arrangement to be what I
   assumed (R folded onto M, then L over the pack).
3. **In a z-fold, tension is tied but grain cracking is not.** Every fold has the same tension-face strain, but at the grain-in folds the tension face is the back
   (flesh side) of the leather and the grain is in compression (-16.8 %). Finish cracking is a grain-face tension risk, so only the grain-out folds count for it; the
   report prints both rankings. Which side tolerates tension better is a leather property that is not known here.
4. **The type matters less with a square spine.** With a box spine of 1 mm corners the worst fold is 19.3 % (bifold), 20.2 % (trifold, 3-panel z-fold) and
   21.2 % (4-panel z-fold): within 2 points, against 6 points with round spines.
5. **Less in the wallet is not gentler.** Strain falls as the stack grows (a bigger radius):

| Worst fold, loose / taut | 4 cards (3.04 mm) | 8 cards (6.08 mm) | 12 cards (9.12 mm) | 8 cards + 0.5 mm pocket leather each (10.08 mm) |
|---|---|---|---|---|
| bifold | 18.3 / 19.5 % | 14.1 / 15.2 % | 11.5 / 12.4 % | 10.9 / 11.3 % |
| trifold | 21.1 / 22.3 % | 18.3 / 19.5 % | 16.0 / 17.1 % | 15.3 / 16.4 % |
| z-fold, 3 panels | 21.1 / 22.3 % | 18.3 / 19.5 % | 16.0 / 17.1 % | 15.3 / 16.4 % |
| z-fold, 4 panels | 22.2 / 23.5 % | 20.1 / 21.4 % | 18.3 / 19.5 % | 17.6 / 18.6 % |

   A near-empty trifold or z-fold is above the 20 % screening threshold; the order of the types does not change. Pocket leather matters: 0.5 mm per card grows the 8-card
   stack by two thirds and lowers the bifold's strain from 15.2 % to 11.3 %. Set `--slot-leather` to your real pockets.
6. **The layup changes the size, not the order, with one exception.** At 8 cards (worst fold, taut): lined 19.7 / 25.1 / 25.1 / 27.4 %
   (bifold / trifold / z3 / z4), skived 11.0 / 15.2 / 16.0 / 17.6 %. With a skived layup the grain-in folds of the z-fold come out worst (the other layups tie); I suspect it is because the thinned
   flesh side is then the face in tension, but I have not tested that.
7. **Thickness and push-back add up.** Closed thickness is 8.5, 9.7, 9.7 and 10.9 mm for the same cards, and the total closing moment (the sum over the folds) is 2.8 for the bifold and 11.3 for
   the 4-panel z-fold. Moments are only given for round spines.

## 3. How the ranking is made
`damage.rank_locations` over the folds, with the strain of each fold and its cycles per use, for exponents m = 3, 5, 8, 12. With equal cycles the order does not depend on m, and folds whose
strains are within 0.5 point are reported as **tied** rather than ordered by the solver's last digit. If you give a fold more cycles (`--cycles spine=2`), the order can depend on m;
the report then says so instead of picking one. Two bases are printed: the tension face of the whole layup, and the grain face only (finish cracking).

## 4. Limits: read before using a number
- **Cycles per use are an assumption**: every fold opens and closes once per use. A trifold, a z-fold and a bifold are not opened the same way; give `--cycles` your own counts.
- **Amplitude is closed to flat.** Wallets are opened part-way, and sit closed most of the time, which is creep and set, not modelled.
- **Folds are evaluated one at a time**, each with its own stack. How the folds interact (the panels bending against each other, the wallet's 3D shape, bulging of the pack, the pockets and card-slot
  edges) is not modelled. The trifold nesting is a hand-derived rule, not a simulated assembly.
- **The stack is contents plus panels as stated.** Real pockets, cards at an angle, and a spine that is not a half-round change it; use `--slot-leather` and `--spine box` to see how much.
- All the limits of the fold model apply (isotropic neo-Hookean leather, no permanent set or finish cracking, frictionless rigid stack, perfectly bonded layers, E a number you supply).
- Not covered: zip-around and gusseted wallets as a whole (the gusset is in `FOLD_STYLES.md` section 4), money clips, and anything with hardware.

## 5. Next steps
1. Your wallet's type and real contents: the stack at each fold and the pocket leather, from the capture photos.
2. Real cycles per use per fold, from how the wallet is opened.
3. A simulated assembly of the folds (kinematic fold, phase 2 of the roadmap), which would replace the nesting rule and show part-way opening.
4. Calibrated cycles to crack, from flex tests on the leather, which turn these relative rates into numbers.
