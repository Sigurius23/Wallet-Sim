# Roadmap

## Decisions needed from you
1. **First wallet.** Which one, and does it have wear history? A used wallet gives us validation data from day one.
2. **Physical flex tests.** Are you willing to cut strips and fold them to failure? Without them, "x folds" stays a
   relative index. This is the biggest lever on how far the simulator can be trusted.
3. **GPU, and when.** Not needed for phases 1-3. Needed when we want design sweeps, many drops, or differentiable
   parameter fitting. Moving to a GPU machine is a switch of environment, not a rewrite.
4. **Licence.** None yet. CalculiX is GPL but called as an external program; if we later link a GPL Python library
   (for example FElupe), the repo licence is affected.
5. **Viewer.** A static browser viewer (works anywhere, shareable) or local desktop tools only.
6. **Which leathers first, and which ageing conditions?** Offcuts you can cut strips from decide how real the material cards are.
7. **Drop test: what does failure mean?** Cards ejected, a corner crushed, a seam torn? The answer decides the model.

## Phases (each ends with something you can look at)

| # | Phase | Ends with | Needs |
|---|---|---|---|
| 0 | **Foundation** (this commit) | repo, validated FEM benchmark, strain screen, calibration hook, docs | - |
| 1 | **Capture to record** for wallet #1 | `wallets/<slug>/wallet.yaml` plus rectified outlines, every inferred field confirmed by you | photos + measurements (`CAPTURE.md`) |
| 1b | **Capture pilots** (`CAPTURE_FEASIBILITY.md`) | answers to: how good is photo-only inference, scan accuracy on leather, stiffness spread in one offcut, whether CT separates the layers | a spare wallet, a bend test, optionally a CT service |
| 2 | **Assembly and kinematic fold** | a 3D model that opens and closes in the viewer, with stack thickness, bulge, interference and level-0 strain per fold; checked against the edge-on photos | phase 1 |
| 2b | **Material library** (`MATERIALS.md`) | cards for your first leathers: measured thickness, bending stiffness along/across, flex-to-crack; aged states from strips aged under stated conditions | offcuts, a bend test, a few weeks of ageing strips |
| 3 | **FEM fold cycle** | strain and contact-pressure maps for one fold cycle with contents, CalculiX backend; compared with level 0 at each fold | phase 2 |
| 4 | **Wear** | hot-spot maps, location ranking, card-pull wear (Archard), predicted vs photographed wear on used wallets; calibrated cycles to crack if flex data exist | phase 3, wear photos, optional flex tests |
| 5 | **Drop test** | defined after decision 6 | phase 3 |
| 6 | **Archive and viewer** | browse wallets, replay folds, compare designs side by side | several wallets |

Research items with no model yet (see `FAILURE_MODES.md`): permanent set under repeated flexing, finish crazing and delamination, wet and salt flex.

Wallet #2 and #3 come before any new physics: a simulator tuned on one wallet proves nothing.

## Not planned
Absolute service-life predictions from an uncalibrated model; moisture-coupled behaviour; fibre-level models.
