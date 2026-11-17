# What the simulator can and cannot claim

Leather is hard to simulate honestly. The research that does it well (Fraunhofer ITWM's fibre-network models, Simucal
at the Polytechnic University of Valencia) is calibrated per hide and is not open source. No validated fatigue law
exists for leather. This project is built around that fact rather than around hiding it.

## Three tiers of statement

| Tier | Example | Needs |
|---|---|---|
| **Will claim** | "The spine fold of wallet A reaches 14 % outer-fibre strain, wallet B 9 %." "Wear on the pocket mouths concentrates at the corners." "A wears at the spine before the corner for every exponent in 3..12." | geometry, thickness, a stated material model |
| **Only after calibration** | "Cracks at about N cycles for this leather lot at this strain." | flex tests on the same leather (see below) and the fitted law, with the range it was tested over |
| **Will not claim** | A service life in years or days from an uncalibrated model. An acceleration factor between test and use. | no such validated thing exists |

Every simulation output carries the tier it belongs to, the material parameters it used, and whether each was
measured, inferred or assumed (see `DATA_MODEL.md`).

## The fidelity ladder
Conclusions from `prior-research/reference/durability.md`, which is itself a literature survey and should be re-verified
before anything is published:

| Level | Model | Data needed | Used here for |
|---|---|---|---|
| 0 | analytic `eps = t/(2R+t)` | thickness, radius | screening every fold, instantly |
| 1 | continuum FEM, anisotropic / viscoelastic | tensile + biaxial tests per lot (Poisson's ratio and shear modulus have no standard test) | the wallet simulator (CalculiX now; GPU backends later) |
| 2-3 | fibre-network FEM | micro-CT at ~3 µm | out of scope |
| film model | stiff finish on a soft substrate: wrinkling / creasing / delamination | finish thickness, adhesion | explain surface creasing, later |

**Gaps at every level:** cumulative fatigue damage over thousands of cycles, and the effect of moisture. Both are
empirical, which is why this project asks for physical tests instead of pretending a solver covers them.

## Validation plan
1. **Numerical (done for the simplest case):** with Poisson 0 the FEM strip reproduces `t/(2R+t)` to +1.0 % and the beam
   bending moment to -0.2 %, on two mesh densities. With Poisson 0.3 the peak strain is 11-20 % higher than the closed form
   (3D contraction and constrained ends), so the closed-form screen can under-estimate. An earlier +0.9 % figure for the
   0.3 case came from a coarse mesh and was a coincidence; it is withdrawn. Repeat this for each new scenario that has a
   closed form before trusting it without one.
2. **Physical, cheap:** flex-test strips cut from the same leather as a wallet, folded over a few mandrel radii, cycles
   to first crack recorded -> `walletsim fit-law`. This turns "relative damage index" into a calibrated, range-limited
   prediction.
3. **Qualitative, free:** used wallets with known history. Photograph the real wear, then check that predicted hot spots
   (spine crease, pocket mouths, corners, edges) coincide with where the leather actually wore. Wallets in the archive
   with wear photos are the validation set. Hold some out.
4. **Comparative:** two wallets with a known real-world difference in durability should rank the same way in simulation.

## Known simplifications of what exists today
- The FEM benchmark uses a neo-Hookean (hyperelastic) material; leather is viscoelastic, anisotropic and has a finish
  film. It validates the solver's large-rotation behaviour and bending mechanics, not leather physics. The stiffness and
  Poisson's ratio in it are placeholders.
- The strain screen ignores the finish layer, creep and permanent set. Its 20 % and R/t thresholds are screening
  heuristics, not failure criteria.
- `rank_locations` uses an assumed exponent range (3..12) only to test whether a ranking is robust. It is not a
  material property.

## Candidate methods for fitting material parameters from observation (not adopted, to evaluate)
Differentiable simulation can fit cloth parameters to video or images (Liang, Lin and Koltun, NeurIPS 2019;
phi-SfT, arXiv 2203.11938; gradSim, arXiv 2104.02646). Those are cloth, not leather, and recovering bending stiffness
from multi-view video is still described as an open problem. Worth an experiment once a GPU is available; not a
foundation to build on.
