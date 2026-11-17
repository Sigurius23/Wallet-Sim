# Wallet-Sim

A digital archive of leather wallets, with a simulator that shows how each design folds, where it is strained,
and where it is likely to wear first.

The idea: photograph a real wallet, rebuild it digitally (its panels, folds, seams and card pockets), then run it
through fold cycles, card pulls and drops, and compare designs side by side.

## Status: foundation (v0.1)
Nothing here simulates a full wallet yet. What exists and is tested:

| What | Where | State |
|---|---|---|
| FEM backend check: a strip bent 180° in CalculiX vs closed form (Poisson 0) | `walletsim validate-fem` | **strain +1.0 %, bending moment -0.2 % vs theory**, same on two mesh densities; 8 s on 4 CPU cores |
| Thickness sweep at a fixed fold radius: strain and bending moment per thickness | `walletsim sweep` | works; stiffness is a placeholder until measured |
| Material cards with provenance, aged states as measured data | `walletsim.materials` | structure only; one literature card (calfskin upper, 72 MPa tensile, CV 29 %) |
| **Fold styles**: plain, skived, lined, skived + lined, hinged, turned-edge and bound-edge folds in a free fold and wrapped around a card stack; **gussets** (V, S, W pleats at several openings) and a **box-shaped spine**; the turned-edge turn (closed form). Every construction and its status: [`docs/CONSTRUCTIONS.md`](docs/CONSTRUCTIONS.md) | `walletsim fold-styles`, `gusset`, `box-spine`, `edge-turn`; [`docs/FOLD_STYLES.md`](docs/FOLD_STYLES.md) |
| **Overall wallet fold types**: bifold, trifold (letter fold) and z-fold (accordion): the stack each fold wraps, which fold wears first, types compared at the same contents | `walletsim wallet-types`; [`docs/WALLET_TYPES.md`](docs/WALLET_TYPES.md) | folds evaluated one at a time; assumptions stated | **current focus**; agrees with closed forms to 2-3 % where they apply |
| Level-0 fold screen: `eps = t/(2R+t)` with screening flags | `walletsim screen --t 1.0 --radius 2.0` | done |
| "x folds" bookkeeping: rank locations by cycles per use x strain^m across a range of exponents, and fit a cycles-to-crack law to **your own** flex-test data | `walletsim fit-law`, `walletsim.damage` | done, refuses uncalibrated absolute life |
| Docs: architecture, claims policy, capture protocol, **capture feasibility research**, **materials and ageing**, data model, roadmap | `docs/` | draft for review |
| UI outline: museum-style timeline archive with material, source and treatment views, from your sketches | `docs/UI.md`, `docs/ui/` | rough draft, your input needed |
| Failure-mode catalogue: what the report will say about each wallet, and what is flagged or not modelled | `docs/FAILURE_MODES.md` | draft for review |
| Earlier research: durability review, species anatomy, tanning-to-finishing treatments and property matrix, pattern kernel, photo-to-pattern prototype | `prior-research/` | reference only, not a dependency |

## What this will and will not claim
Read [`docs/SCIENCE.md`](docs/SCIENCE.md). In short: the simulator can show **where** strain concentrates, **which
design** is gentler on its leather, and **which location** wears first. It will give **cycles to crack only after
calibration** against flex tests on the same leather, and it will not quote a service life from an uncalibrated model.
No validated leather fatigue law exists; the leather-specific research codes (Fraunhofer ITWM, Simucal) are not open.

## Quick start
```bash
pip install -e ".[dev]"            # numpy only; the FEM check also needs CalculiX
sudo apt-get install calculix-ccx  # Debian/Ubuntu
pytest                             # 75 tests, ~170 s
walletsim validate-fem             # the 180° bending benchmark
walletsim fold-styles              # compare fold constructions, about 15 s
walletsim gusset                   # accordion pleat, about 17 s
walletsim box-spine                # flat-walled spine against a round one, about 30 s
walletsim wallet-types             # bifold, trifold, z-fold at the same contents, about 40 s
```

## Layout
```
src/walletsim/     wallet_types.py (bifold / trifold / z-fold), fold_screen.py (level 0), damage.py (cycle bookkeeping), fem/bending.py (CalculiX benchmark),
                   fem/fold.py + fold_styles.py (layered fold model and the styles), materials.py (cards)
docs/              ROADMAP, ARCHITECTURE, SCIENCE, FOLD_STYLES, CONSTRUCTIONS, WALLET_TYPES, CAPTURE, CAPTURE_FEASIBILITY, MATERIALS, FAILURE_MODES, UI, DATA_MODEL
wallets/           the archive: one folder per wallet (see docs/DATA_MODEL.md; template in wallets/_template/)
prior-research/    first exploratory research, kept for reference
tests/
```

## Open decisions
Listed at the top of [`docs/ROADMAP.md`](docs/ROADMAP.md). License is not chosen yet.
