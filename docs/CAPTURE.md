# Capturing a wallet

Goal: enough to rebuild the wallet digitally **and** to check the rebuilt model against the real one. Leather thickness
and layer order cannot be read from a photo, so some of this is measuring, not photographing.

## Photos (per wallet)
Use a plain matte background, soft even light (no direct flash), the camera straight above for flat shots, and a scale
in every frame. The earlier prototype used a 300 x 250 mm mat with four ArUco markers (`DICT_4X4_50`); an ISO bank card
(85.6 x 53.98 mm) beside the wallet also works as a scale.

| # | Shot | Why |
|---|---|---|
| 1 | Open, flat, outside, straight down | panel outline, stitch lines, fold lines |
| 2 | Open, flat, inside, straight down | pocket layout, slot order, lining |
| 3 | Closed, both faces | closed footprint, how the folds meet |
| 4 | Edge-on: spine, top, side, each with a ruler or card edge | stack thickness, bulge, layer count |
| 5 | Each pocket with one card half-inserted | slot depth, reveal, how a card sits |
| 6 | Close-ups: stitch line with a ruler, a corner, an edge finish, any skived area | stitch pitch, corner radius, edge treatment |
| 7 | Anything unusual: thumb notches, gussets, hardware, tabs | construction that the flat shots hide |
| 8 | **If the wallet has been used: wear shots** — spine crease, pocket mouths, corners, edges, lining, finish cracking | the validation set (see `SCIENCE.md`) |
| 9 | *Optional:* 40-80 photos orbiting the closed wallet, overlapping, matte background | photogrammetry check |

## Measurements (calipers and a scale)
- Thickness of each leather layer at 3+ points: outer, pocket leather, lining, any reinforcement.
- Total closed thickness at the spine and at the middle, empty and with N cards.
- Weight. Outer dimensions open and closed.
- Number of cards each slot holds comfortably, and whether a banknote compartment exists.
- What is known: leather type and tannage, finish (aniline, pigmented, wax, burnished), thread, pricking-iron pitch,
  maker, age.
- Usage history if worn: months of use, how it is carried (back pocket, jacket), typical card count.

## Optional physical tests (turn a relative index into a calibrated one)
From an offcut or a spare wallet of the same leather: a few 10 x 60 mm strips, folded to 3-4 mandrel radii for as many
cycles as it takes to see the first grain crack. Record radius and cycles. `walletsim fit-law` fits the law and states
the range it is valid for. Condition the strips first (same temperature and humidity, a day or more).

## Bending test and spare cross-section (Tier 2, see `CAPTURE_FEASIBILITY.md`)
- **Bending-length test:** cut 2-3 strips (about 20 x 100 mm) from an offcut, along and across the backbone if known. Slide a
  strip over the edge of a table until its tip drops to a 41.5 degree line (or photograph the overhang and measure it with the
  scale). Record the overhang length, strip width and thickness. Folds are bending-dominated, so this is the most useful
  single material measurement.
- **Spare cross-section:** if you have a second copy of a wallet, cut it across the spine and across a pocket, sand or slice
  cleanly, and photograph the cut edge with a ruler. It shows the true layer stack and glue lines.

## What happens next
Photos and numbers go into `wallets/<slug>/` as described in `DATA_MODEL.md`. I propose the construction record from the
photos; every inferred field is listed for you to confirm or correct before any simulation is run on it.
