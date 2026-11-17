# Agent handoff: Wallet-Sim

Paste everything below into the next agent session. State as of commit `abb9906` on `main` (working tree clean, 122 tests pass in about 5.5 minutes).

## Mission
Wallet-Sim is a digital archive of leather wallets with a simulator: how each wallet folds, where its leather is strained, which fold wears first. The owner wants the archive app to match the UI sketches (`docs/ui/`, `docs/UI.md`) and the README feature list **1:1 in functionality**, built only from evidence the records can state. You are continuing that work.

## Where things are
- Repo: https://github.com/Sigurius23/wallet-sim (push straight to `main`, as the owner does; no PRs unless asked). Local `/home/user/wallet-sim`.
- Corpus (read-only, research documentation only, never show or copy its images): https://github.com/Sigurius23/Wallet-corpus- at commit `bda0572`, local `/home/user/wallet-corpus-/carpe_diem_research/wallet/designers/{ma_plus,isaac_sellam,sruli_recht}`. Re-clone and `git pull` it: new items may have been added.
- Setup: `pip install -e ".[dev]"`; CalculiX `ccx` 2.21 (`apt-get install calculix-ccx`, at `/usr/bin/ccx`); `node` for the twin geometry tests; Playwright is preinstalled for screenshots (use `--use-gl=swiftshader --enable-unsafe-swiftshader`; route the jsdelivr three.js r128 scripts to local copies).
- This container's environment setup script failed at build once (`/root/.claude/environment-manager/setup-script-failed`). Check whether it still does; if so propose a fix with `update_environment`.
- Commands: `walletsim wallet-report|wallet-page|wallet-viewer|wallet-styles wallets/<id>`, `walletsim lab-run`, `walletsim build-site` (writes `site/index.html`), plus the older `screen, validate-fem, sweep, fold-styles, gusset, box-spine, edge-turn, wallet-types, fit-law`.
- Generated and **gitignored**: `site/`, `wallets/*/sim/run-*/page.html`. Generated and **committed**: each wallet's `viewer.html`, `sim/styles.json`, `sim/run-<hash>/` (the hash is of `wallet.yaml`, so an edited record needs a new run and the old run directory deleted), and `lab/results.json`. After changing any template, geometry or record, regenerate these, run the tests, update the README test count, rebuild the site.

## Wallets in the archive (all `photos-only`: nothing measured)
`ma-one-piece-wallet` (spine + 3 hairpins), `ma-one-piece-double-wallet` (4 leaves, 5 folds), `ma-mavr-origami-wallet` (pig leather, seller's 18 mm closed depth), `sr-whalet-sr202-2022` (horse skin, maker's 85 x 100 x 10 mm, 2022 reissue of a 2010 design; the only **functional twin**, via `assembly.yaml`). `slim-6card-design` is a generated test design, hidden from the app.

## Published artifacts (private; republish with `url` to keep the link)
App https://claude.ai/artifact/Kgo4K1tcbVzmxCTqW8xt7R. Report pages: One Piece T5T4qVaPjenHnKvZTPjV6m, Double 4g5h1pHLiYMPgF47URS2cw, origami R77qEFBMha2Z3cR2EBEfv2, WHALET Ff7Xhc34qaAgnfKqRSBQ6k. 3D viewers: One Piece CwM5dxUiwMBB9dfVA58imT, Double 16LJsT5rdZk7MhFTQFwfSF, origami 668nPpcg9BNhtRt7hfqEcK, WHALET twin 3opuvEVzJ1NQBfKxwsBhzK. The One Piece and Double viewers were last published before the shared `geometry.js` refactor: regenerate and republish them.

## Rules that must not be broken
1. Every number carries provenance: `measured`, `reported` (a seller or maker said it; not measured), `inferred`, `design`, `literature`, `assumed`. A derived value is never stronger than its weakest input.
2. No invented material values. No absolute service life from an uncalibrated model. Ageing only as measured states. Tight hairpins the elastic model cannot follow are ranked by the closed form and say so.
3. Say plainly when a layout is read from photographs. Never present a sketch or twin as a scan or a leather simulation. Disclose corrections (the One Piece record was corrected once: it had omitted the left fold).
4. Corpus images are rights-limited: reference by path, do not embed. Biographies and portraits need permission.
5. Write plainly. Report what failed and what you skipped. Confirm outward-facing or hard-to-reverse actions first.
6. Commit with the attribution lines your own session gives you. Do not create PRs unless asked.

## Open items

### A. Verify what was never verified
1. Open the published app in the Claude artifact viewer. Check the nested 3D frame in Behaviour (iframe `srcdoc`, `sandbox="allow-scripts"`, Three.js from jsdelivr): it was only tested in Playwright. The app prints a note after 6 s if the frame stays silent. If the host blocks it, inline the viewer or link to the standalone artifacts.
2. Check Lab, the animals, the thickness slider and the styles table on a 400 px phone and in dark mode (only horizontal overflow was checked for Behaviour).
3. There are no automated browser tests; the Playwright scripts lived in the last session's scratchpad. Add a smoke test: every route loads without page errors or horizontal overflow at 400 px; a multi-year synthetic timeline activates, pages and responds to keys and the wheel; animals mount; the slider updates the table.

### B. Functional twins (the "1:1" thread)
4. Build twins for the origami (flap, bill pocket with V gussets, 4 medium pockets, 4 card slots, 145 x 95 x 18 mm reported), the One Piece Wallet and the Double Wallet (Z-chain accordion; photos 013 and 014 show fan-shaped pockets a strip cannot draw). Each needs an `assembly.yaml` with provenance. `buildTwin` in `src/walletsim/geometry.js` handles "back panel + flap hinge + stepped walls"; the accordion needs a more general panels-and-hinges builder. Done when each twin's empty closed depth is compared with the reported depth and the page says what fits.
5. WHALET twin refinements: how the walls join the back panel; the maker names 3 slots but image 035 shows 4 layers; the flap hole and the stud disagree by about 20 mm between images 035 and 036 (I aligned them); the left end fold is not drawn; no snap, friction, bulge or leather stretch.
6. Reconcile the WHALET record and report with the twin: the twin shows 7.1 mm empty at 1.0 mm sheet, so either the sheet is about 1.5 mm or the 10 mm was taken loaded. The report's 8 mm stack is an upper bound. Derive the stack from the twin's layer count, then rerun the report.

### C. UI gaps (full audit in `docs/UI.md`)
7. Leather swap: needs material cards from measured data (only calfskin, literature, exists).
8. Wear hot spots beside real wear photographs: needs a wear model (roadmap phase 4) and photographs. The origami's photo 04 shows light wear and is unanalysed.
9. Sketch 4's Overview | Wallet | Desktop frame; side-by-side 3D compare (currently a table); a multi-leather record to exercise the multi-part mapping lines; a glTF build step.
10. Goat: no CC0 model exists. The one free goat is CC-BY-SA 3.0, `.blend` only (https://opengameart.org/node/65419). Needs the owner's decision on the licence, then a Blender conversion.
11. Cut zones: `inZone` in `site_template.html` uses rough fractions of each model's bounding box. Refine per species (horse neck, sheep) and define a real hide-region schema once a record names a region. No record does.
12. Rights-cleared hero photographs, designer biographies, and design years (every M.A+ record is undated) all depend on the owner.

### D. Corpus items not yet recorded
13. `ma_plus`: map03 silver chain wallet (map02 body plus a chain), map05 small zipped wallet (zip case, 11 x 11 cm; tests a record with no folds), map06 silver pendant (adjacent, not leather: probably exclude).
14. `isaac_sellam`: is01 to is06 and `_catalogue_only` (articulated alligator or crocodile wallets with staple seams, a metal spine, cord; is06 is spiral-bound). Needs a new construction type and reptile models.
15. `sruli_recht`: sr001 Nile perch 2009, sr002 Minke Dork 2009, sr003 horse 2010 (same geometry as the recorded sr005: try its twin), sr004 Ghostly c.2010, sr006 and sr007 FOALD clutches (adjacent). Fish skin has no free model.
16. For each new wallet: `wallet.yaml`, `notes.md`, report run, `wallet-styles`, viewer or `assembly.yaml`, page; update `wallets/README.md` and the README rows. `tests/test_site.py` hard-codes the wallet list: make it data-driven.

### E. Simulator and science backlog
17. Tight hairpins (R/t below 0.5) are closed form only and the elastic model bridges the stack; stand-off is the least mesh-converged output. Add a pre-tension or contact treatment and a convergence study.
18. Roadmap phases 2 to 5: full kinematic assembly, FEM fold cycle with contents, wear and card-pull (Archard), drop test (what failure means is undecided). Not modelled: permanent set, finish crazing, wet and salt flex, ageing.
19. Material library from offcuts and bend tests; the `fit-law` tool needs the owner's own flex data.

### E2. Leather types, hide parts and behaviour (the owner says all of it matters)
Built: `src/walletsim/species.py` (hide group and class), `src/walletsim/leather_cards.py` and `cards/*.yaml` (3 cards, a source on every value), coverage map (10 of 90 sheet-hide cells), strip-test functions in `materials.py` and the Lab's *Measure a strip*, the composite-hide refusal (`NotApplicable`, exit code 3). Open:
- Find and read in full more literature cards: pig leather, horse leather, goat (a Kenyan vegetable-tanned goat study reports 0.81 mm, 27.5 N/mm2 and 18 % elongation, which looks low and was not verified), sheep, Nile perch (none found; tilapia is a different fish), crocodilian. Never add a value you have not read in a table; the earlier 24 to 53 MPa misattribution is the cautionary tale.
- Get the owner's strips measured (thickness at several points, cantilever bending length, mass and size, along and across the backbone, several thicknesses of one leather) and add them as `cards/*.yaml` with `source: measured`.
- Add strain at grain crack: lastometer grain-crack distension (ISO 3379) or flex-to-crack at several mandrel radii. Only then can the report show a margin (capacity against demand); until then it shows demand only and says so.
- Put measured direction ratios, hide-region maps (thickness and stiffness by region) and through-the-hide layers (grain and corium, for finish cracking) into the solver. They need data first; do not use the library's directional priors as numbers.
- Aged states: run the experiment in `docs/MATERIALS.md` section 5 and store each state as a card state.
- A composite model for plated and scaled hides (the six Isaac Sellam alligator and crocodile wallets, snake, stingray): plate geometry, a soft-matrix hinge model and an interface-failure criterion. Until then they stay refused.
- Use the measured seam and perforation effect (the calfskin paper's S2 and S3 samples) once there is a way to apply it.
- No free 3D model exists for goat, fish, reptiles or exotics in the app.

### F. Code hygiene
20. `sim/styles.json` carries no input hash, so it goes stale silently when a record changes. Add the hash and make `build-site` flag stale results; do the same for `viewer.html` and `lab/results.json`.
21. `page.latest_run` picks by file modification time; make it deterministic. Add cleanup of superseded run directories.
22. No licence file for the repo yet.

## Decisions waiting on the owner
A physical wallet or flat pattern to measure (closed depth empty and loaded, sheet thickness, hairpin radii; the WHALET maker holds the cutting file); whether to run flex tests; the CC-BY-SA goat; which twin and which corpus item come next; whether real-size flat patterns or a physics simulation with cards are wanted beyond the kinematic twin; permission for photographs and biographies; the open decisions in `docs/ROADMAP.md`.

## Separate project, not part of Wallet-Sim
The D455/G1 head-mount work: recovered scripts are in https://github.com/Sigurius23/Robot-print-files. The print files, zip and vote PDF must be re-attached by the owner. Do nothing on it until they are.
