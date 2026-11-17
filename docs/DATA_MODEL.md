# Archive data model (draft)

One folder per wallet:
```
wallets/<slug>/
  wallet.yaml        the record (below)
  photos/            originals, named by shot number from CAPTURE.md (01_open_outside.jpg, ...)
  measured/          rectified outlines, hole positions, photogrammetry mesh (if any)
  sim/               results, one subfolder per scenario run, each with the exact inputs used
  notes.md           anything that does not fit
```
Units are millimetres, grams, degrees, MPa. The wallet frame: x across the open wallet, y along the spine, z through the
thickness with +z toward the outside of the front cover.

## wallet.yaml
Every number that feeds a simulation is stored as a value with its provenance:

```yaml
id: example-bifold-01
name: Example bifold
maker: unknown
status: measured            # design (numbers from a design file) | measured
photos: {open_outside: photos/01_open_outside.jpg}
archive:                                                       # drives the timeline and carousel (docs/UI.md)
  designer: Example Designer
  year: 2018
  series: Example Series No. 1
  bio_ref: designers/example-designer.md
  hero_image: photos/hero.jpg
  rights: {photos: unknown, bio: unknown}
leather:
  - id: shell
    thickness_mm: {value: 1.2, source: measured, n: 5}      # source: measured | inferred | assumed
    species: {value: bovine, source: inferred}
    hide_region: {value: unknown, source: assumed}          # a region name does not guarantee a strength
    windows:                                                # the four processing windows; blank = ask the maker
      beamhouse: unknown
      tanning: {value: vegetable, source: inferred, confidence: 0.6}
      post_tanning: unknown
      finishing: {value: semi-aniline, source: inferred}
    edge: {value: painted, source: measured}
    material:                                               # stand-ins until measured; cv = spread within the leather
      youngs_modulus_mpa: {value: 50, source: assumed, cv: 0.4}
      poisson: {value: 0.3, source: assumed}
components:                                                     # what the UI maps to animals: body, pockets, lining
  - id: body
    role: exterior body
    leather: shell
    hide_region: {template: bovine, region: unknown, source: assumed}   # region id on the species template; unknown is valid
process_steps:                                                 # ordered, free-form; each tagged with its window
  - {order: 1, name: Raw hide, window: beamhouse, source: inferred}
  - {order: 2, name: Vegetable tanning, window: tanning, source: inferred}
  - {order: 3, name: Waxing and buffing, window: post_tanning, source: inferred}
  - {order: 4, name: Distressed finishing, window: finishing, source: inferred}
contents:                                                      # what the closed wallet holds
  cards: {value: 6, source: measured}
  card_mm: {value: 0.76, source: literature, ref: ISO/IEC 7810 ID-1 nominal}
  extra_mm: {value: 0.0, source: assumed}
construction:                                                  # how the folds are made; read by walletsim wallet-report
  type: bifold                                                 # bifold | trifold | z-fold (see docs/WALLET_TYPES.md)
  spine: {value: round, source: inferred}                      # round | box
  grain: out
  layup: plain                                                 # plain | skived | lined | skived+lined | hinged | turned edge | bound edge
  interior_leather_layers: {value: 9, source: assumed}         # slot / bank pieces lying between the two halves at the spine
  closed_thickness_mm: {value: 12.5, source: measured}         # calipers at the spine; stack = this - 2 x shell. Overrides the layer count
panels:                                                        # flat outlines, from calibrated photos
  - {id: outer, leather: shell, outline: measured/outer.svg, grain_direction_deg: {value: 0, source: assumed}}
folds:
  - {id: spine, panel: outer, line: [[99.2, 0], [99.2, 87]], rest_angle_deg: 180, skived: {value: false, source: inferred}}
seams:
  - {id: perimeter, between: [outer, lining], crosses_fold: [spine], stitch: {pitch_mm: {value: 3.85, source: measured}, edge_offset_mm: {value: 3.5, source: measured}}}
pockets:
  - {id: left-1, panel: slot_1, card_capacity: 1, reveal_mm: {value: 8, source: measured}}
usage: {used: false}
```

Provenance (`source`) is one of `measured` (you measured it on the object), `reported` (stated by a seller, maker or retailer and not checked: a listed thickness, a stated size),
`inferred` (read from photos or drawings, or derived from other numbers), `design` (what a design file or pattern specifies; the physical object may differ), `literature` (a cited
publication or standard) or `assumed` (a stand-in). `walletsim.record` rejects a number without one. `reported` is not `measured`: reports count it as not measured.

Rules:
- `assumed` values are allowed, but any result that depends on one is labelled with it.
- `status` is `design` (the record comes from a design file), `photos-only` (from product photographs and text, nothing measured) or `measured`; reports say so at the top.
- A wallet whose folds do not fit bifold, trifold or z-fold (origami and other one-sheet constructions) sets `construction.type: custom` and lists its folds one by one;
  each fold's stack may carry a range that the report sweeps. Seams list the folds they cross or pin in `crosses_fold`:

  ```yaml
  construction:
    type: custom
    folds_modelled:
      - name: spine
        stack_mm: {value: 3.0, low: 3.0, high: 9.1, source: inferred, ref: "3 inner leaves seen x 1 mm; upper bound adds 8 cards"}
        sense: out                       # out: grain on the outside of the fold; in: grain inside
      - {name: loop 1, stack_mm: {value: 1.0, low: 0.5, high: 4.0, source: assumed}, sense: in}
  ```
  A fold's stack may also be **derived**, so that it moves when the number it comes from moves:
  `stack_from_loops: {leaves: {value: 4, source: inferred}, gap_from: <loop fold>}` (a one-sheet accordion: `leaves x t + (leaves + 1) x gap`, with the gap taken from the named loop) and
  `stack_from_closed_thickness: {shells: 2, low: 10.0}` (a fold that wraps the whole pack: `closed_thickness_mm - shells x t`, with the stated lower bound; tagged `inferred`).
  A fold's stack derived from the closed thickness is tagged `inferred` only if the shell thickness it subtracts is also stated; with an assumed shell thickness it is `assumed`.
  `geometry: gusset` on a fold (or "gusset" in its name) makes the 3D viewer draw it as a bill-pocket pleat; `archive.year_note` qualifies a year (for example a reissue date); the viewer draws only the first fold of a closed-depth record plus any gusset.
  `seams.crosses_fold: unknown` says the seam exists but nobody has recorded where; the stitch-hole and perforation modes then read *unknown*, not *not triggered*.
  `usage: {used: true, condition: "..."}` marks a wallet that has been carried; the report prints the condition under its title, and no ageing is inferred from it.
- A fold whose inside radius is below half the leather thickness is not run through the solver (the elastic model shows the leather bridging the gap); it gets the closed form and is
  marked *closed form only*. A fold whose leather, with no pull on it, stands off the stack by more than the stack's radius is marked *bridges* and is ranked by the closed form.
- Photos are never overwritten; rectified or derived images go in `measured/`.
- A simulation result stores a copy of the record version it ran on, so results stay reproducible.

A template lives in `wallets/_template/wallet.yaml`.

### `assembly.yaml` (optional): the functional twin
A wallet folder may hold `assembly.yaml`, a **reconstruction** of the interior at real size, kept apart from `wallet.yaml` because it is not a fact about the wallet: it is read off photographs and carries its own provenance on every number
(`kind: twin`, the back panel and flap, `walls` with their reach and insets, `pockets` with their roles and card capacities, the closure stud, the card and note thickness, the empty-gap and stretch allowances, a thickness range). `walletsim wallet-viewer` then builds a
model whose flap opens, whose pockets fill with cards and notes, and whose closed depth, stack, hinge radius and strain follow the contents, and it says which sheet thickness would reproduce the maker's closed depth. See `wallets/sr-whalet-sr202-2022/assembly.yaml`.
