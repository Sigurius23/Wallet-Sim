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
| **Four wallets** from the Wallet-corpus- archive (three M.A+, one Sruli Recht), recorded from retailer or reseller text and photographs only (status `photos-only`, nothing measured), each with a one-page summary: the **One Piece Wallet** (a spine plus three tight hairpins), the **One Piece Double Wallet** (four leaves, five folds) and the **MAV.R pig-leather origami** (its one hard datum is the seller's 18 mm closed depth) and the **Sruli Recht WHALET SR202** (2022 reissue, horse skin, the maker's 10 mm closed depth) | `walletsim wallet-report wallets/ma-one-piece-wallet` (also `ma-one-piece-double-wallet`, `ma-mavr-origami-wallet`, `sr-whalet-sr202-2022`), then `walletsim wallet-page wallets/<slug>` (one-page summary) and `walletsim wallet-viewer wallets/<slug>` (3D sketch of how it folds and opens); notes in `wallets/ma-*/notes.md` | model can only screen the tight hairpins; layouts are read from photographs; the closed thickness and the hairpin radii are what is needed |
| **First wallet record and per-wallet report**: a `wallet.yaml` with provenance on every number, run through the simulator into a report (inputs and sources, fold results, sensitivity, all 14 failure modes, what to measure first) with figures. The first record is a **generated design**, not a photographed wallet | `walletsim wallet-report wallets/slim-6card-design`; [`wallets/`](wallets/README.md) | pipeline works; nothing is measured yet |
| **Archive app (first build)**: Discover timeline, Artists, Years, search, and per-wallet Overview, Materials & Source and Behaviour, built from the records in `wallets/` as one HTML file; undated wallets and unrecorded fields are shown as such | `walletsim build-site` then open `site/index.html`; [`docs/UI.md`](docs/UI.md) | real CC0 animal models for cow, pig, horse and sheep (no free goat found); no photographs (rights); most records are undated; no leather swap (one material card) and no wear hot spots (no wear data). Full audit: [`docs/UI.md`](docs/UI.md) |
| **Overall wallet fold types**: bifold, trifold (letter fold) and z-fold (accordion): the stack each fold wraps, which fold wears first, types compared at the same contents | `walletsim wallet-types`; [`docs/WALLET_TYPES.md`](docs/WALLET_TYPES.md) | folds evaluated one at a time; assumptions stated | **current focus**; agrees with closed forms to 2-3 % where they apply |
| **Leather types and data**: hide classes from the anatomy library, leather cards with a source on every value, a coverage map, a strip-test calculator, and refusal to simulate plated or scaled hides | `walletsim.species`, `cards/`, the app's Lab; [`docs/MATERIALS.md`](docs/MATERIALS.md) section 0 | 3 cards, **10 of 90** property cells filled for sheet hides; no bending stiffness, grain-crack strain, direction or region effect for any leather; composite hides refused |
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
pytest                             # 143 tests, ~280 s
walletsim validate-fem             # the 180° bending benchmark
walletsim fold-styles              # compare fold constructions, about 15 s
walletsim gusset                   # accordion pleat, about 17 s
walletsim box-spine                # flat-walled spine against a round one, about 30 s
walletsim wallet-types             # bifold, trifold, z-fold at the same contents, about 40 s
walletsim wallet-report wallets/slim-6card-design   # a wallet record -> report, figures, stored inputs, about 1 min
walletsim wallet-page wallets/ma-one-piece-wallet     # the latest report of a wallet as one self-contained HTML page
walletsim lab-run                                    # store the simulator tools' output for the app's Lab (about 2 minutes)
walletsim wallet-styles wallets/<slug>               # the fold-style comparison for one wallet, stored for its Behaviour tab
walletsim build-site                                 # the archive app: every record in wallets/ as one HTML file, site/index.html
walletsim wallet-viewer wallets/ma-one-piece-double-wallet   # a 3D structural sketch of a one-sheet wallet's folds, opening and closing
```

## Layout
```
src/walletsim/     record.py + report.py (wallet.yaml -> report), wallet_types.py (bifold / trifold / z-fold), fold_screen.py (level 0), damage.py (cycle bookkeeping), fem/bending.py (CalculiX benchmark),
                   fem/fold.py + fold_styles.py (layered fold model and the styles), materials.py (cards)
docs/              ROADMAP, ARCHITECTURE, SCIENCE, FOLD_STYLES, CONSTRUCTIONS, WALLET_TYPES, CAPTURE, CAPTURE_FEASIBILITY, MATERIALS, FAILURE_MODES, UI, DATA_MODEL
wallets/           the archive: one folder per wallet (see docs/DATA_MODEL.md; template in wallets/_template/)
prior-research/    first exploratory research, kept for reference
tests/
```

## Open decisions
Listed at the top of [`docs/ROADMAP.md`](docs/ROADMAP.md). License is not chosen yet.
