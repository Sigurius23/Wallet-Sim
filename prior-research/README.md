# Prior research (reference only)

Earlier exploratory research, compiled before this repository existed and updated since. It is a rough outline of ideas and a
record of what was tried, **not** a dependency and not maintained. Nothing in `src/` imports it.

It tags its own confidence: **checked** (a standard or a verified publication), **single-source** (one trade figure), and open
gaps. Those tags are kept as written. Statements here have not been independently re-verified by this project unless a source is
linked in `docs/MATERIALS.md`; one conflict with this project's own research is recorded there (section 8).

| Path | What it is |
|---|---|
| `SKILL.md` | the earlier agent skill: scope, defaults, and a list of "do not claim" rules on durability, exotic leathers, transparent leather, "genuine leather", unhairing routes, iron blacks |
| `reference/durability.md` | simulation and durability survey: who has simulated leather, what is open source, the strain screen, film-on-substrate model, flex testing standards (ISO 5402-1:2022, ISO 5402-2:2015, ISO 17694), failure modes, why no life prediction exists |
| `reference/anatomy/` | species and hide anatomy: regions, within-hide variation, direction, plated and scaled hides, species notes (bovine, ovine and caprine, porcine, equine, exotics) |
| `reference/treatments/` | the four processing windows (beamhouse, tanning, post-tanning, finishing), dyes, novel and avant-garde treatments, the **property matrix**, end-use index (wallets included), regulation |
| `reference/sources.md` and the `sources.md` files inside `anatomy/` and `treatments/` | the citations behind the above, and which claims are single-source or unresolved |
| `reference/blender.md`, `photo-intake.md`, `constraints.md`, `construction.md`, `spec.md`, `api.md`, `pitches.md`, `sketch-brief.md` | 3D tools, photo intake, wallet design rules, and notes for the 2D pattern kernel |
| `docs/wallet-reconstruction-feasibility.md` | photo-to-flat-pattern feasibility study with measured results on a synthetic photo |
| `docs/pattern-making-tools-report.html` | survey of pattern-making tools |
| `leatherkit/` | parametric 2D pattern generator for new wallet designs (MIT, per its skill description) |
| `photo_to_pattern/reconstruct.py` | prototype: calibrated photo of a flat panel -> outline, stitch pitch, corner radius |

Used for: phase 1 capture, the material-card structure and priors (`docs/MATERIALS.md`), and the failure-mode catalogue
(`docs/FAILURE_MODES.md`).
