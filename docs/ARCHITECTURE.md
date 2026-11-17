# Architecture

```
photos + measurements ──▶ wallet record ──▶ 3D assembly ──▶ scenario ──▶ solver backend ──▶ fields ──▶ analysis ──▶ archive / viewer
   (CAPTURE.md)           (DATA_MODEL.md)    (mesh, seams,    (fold N,     (CalculiX now,      (strain,    (hot spots,   (browse, replay,
                                              pockets)         card pull,   GPU later)          pressure,   ranking,      compare)
                                                               drop)                            slip)       damage)
```

The wallet record describes **what the wallet is**. The scenario and the backend describe **how it is tested**. Keeping
them apart is what lets the same archive entry run on a CPU solver today and a GPU solver later.

## Stages
1. **Capture** gives two things: a *construction record* (panels, folds, seams, pockets, thicknesses, materials) and,
   optionally, a *measured surface* from photogrammetry used to check the rebuilt model against reality.
2. **Assembly** turns the record into a mesh: panels meshed, seams as tie constraints along stitch lines, pockets as
   stacked layers, folds as hinge regions with their rest angle.
3. **Scenarios** are small, declarative: `fold(angle_range, cycles=N, contents=[cards])`, `card_pull(slot, card)`,
   `drop(height, orientation, surface)`. A single fold cycle is simulated in detail; N-cycle outcomes come from the
   damage model, not from running N solves.
4. **Backends** implement one interface: `run(assembly, scenario) -> Fields`. Fields are per-element strain, contact
   pressure and slip distance over time.
5. **Analysis** reduces fields to hot spots, rankings and (when calibrated) cycles to crack. Wear from sliding contact
   (card pulls) uses an Archard-type law, `wear ~ pressure x sliding distance`, again relative until calibrated.
6. **Archive** stores records, photos, results and the viewer's assets.

## Backends

| Backend | Where | Good for | Limits |
|---|---|---|---|
| **CalculiX** (implemented as a benchmark) | CPU, `apt install calculix-ccx` | single wallet, single cycle, contact, large rotations; validated against theory in 7 s | slow for parameter sweeps; implicit, so drops are costly; GPL, so it is called as an external program |
| **GPU solvers** (to evaluate) | needs a machine with a GPU | sweeps over design parameters, many drops, differentiable fitting | not yet chosen. Newton (Warp-based, Apache-2.0) has cloth and soft-body examples, but a shell-FEM solver was **not** confirmed in the sources checked |

Switching machines later is expected and is cheap if the backend interface stays narrow. A GPU is **not** needed to
start: the first wallets, the strain screens and the calibration workflow all run on 4 CPU cores.

## Capture options

| Method | Gives | Verdict |
|---|---|---|
| Calibrated flat-lay photos (ArUco mat) | metric outlines, stitch pitch (prior prototype: ~0.4 mm outline error on synthetic data) | right for panel geometry |
| Photogrammetry (mesh-first) | measurable 3D surface of the closed/open wallet | right for checking the rebuilt model; geometry is generally better than splatting |
| Gaussian splatting | very good appearance, not a measurable mesh | only for the viewer, if wanted |
| Vision-model inference | construction: which layers, how pockets stack, where seams join | needed, but every inferred field is marked `inferred` and confirmed by you |

Leather thickness cannot be seen in a photo. It is measured with calipers.

## Decisions this design leaves open
See `ROADMAP.md`.
