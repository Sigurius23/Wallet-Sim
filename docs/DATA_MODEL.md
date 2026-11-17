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
panels:                                                        # flat outlines, from calibrated photos
  - {id: outer, leather: shell, outline: measured/outer.svg, grain_direction_deg: {value: 0, source: assumed}}
folds:
  - {id: spine, panel: outer, line: [[99.2, 0], [99.2, 87]], rest_angle_deg: 180, skived: {value: false, source: inferred}}
seams:
  - {id: perimeter, between: [outer, lining], stitch: {pitch_mm: {value: 3.85, source: measured}, edge_offset_mm: {value: 3.5, source: measured}}}
pockets:
  - {id: left-1, panel: slot_1, card_capacity: 1, reveal_mm: {value: 8, source: measured}}
usage: {used: false}
```

Rules:
- `assumed` values are allowed, but any result that depends on one is labelled with it.
- Photos are never overwritten; rectified or derived images go in `measured/`.
- A simulation result stores a copy of the record version it ran on, so results stay reproducible.

A template lives in `wallets/_template/wallet.yaml`.
