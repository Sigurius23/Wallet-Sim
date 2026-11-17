# Different leathers, thicknesses and ageing

You want to compare how different leathers and thicknesses bend, and how they age. This is what works today, what the
research says about ageing, and how the simulator will handle the parts that cannot be predicted.

## 1. Thickness: works now

`walletsim sweep` folds a strip around a fixed inside radius (what a wallet's contents impose) for several thicknesses.
180 deg fold, inside radius 3 mm, E = 38 MPa (middle of the 24-53 MPa literature range), Poisson 0.3, CalculiX, about 7 s per row:

| t [mm] | closed-form strain | FEM peak strain | bending moment [N mm] | relative to 0.6 mm |
|---|---|---|---|---|
| 0.6 | 9.1 % | 10.1 % | 2.2 | 1.0x |
| 1.0 | 14.3 % | 16.3 % | 9.6 | 4.3x |
| 1.4 | 18.9 % | 22.2 % | 24.4 | 10.9x |
| 2.0 | 25.0 % | 30.1 % | 63.8 | 28.5x |

- **Strain grows with thickness** at a fixed radius, which is why thick leather cracks at a tight spine fold first.
- **Stiffness grows much faster.** A homogeneous plate has bending stiffness proportional to t^3 (3.3x thicker = 37x stiffer;
  the table shows 28.5x because large strains soften the thick case). Thick leather resists closing, which pushes the spine
  to a larger radius and bulges the wallet.
- **Leather is not a homogeneous plate.** Its fibrous, layered structure may follow a different exponent, and I did not find a
  published value for it (a Northampton study fits a power law for leather softness, but the index was not readable in the
  sources I could reach). `LeatherMaterial.bending_exponent` defaults to 3, marked *assumed*; measuring strips of several
  thicknesses of one leather gives the real exponent.
- **Absolute moments scale with E, which is a placeholder.** Strains do not depend on E. Beyond roughly 20 % strain these are
  kinematic numbers: real leather leaves its linear range, and its finish film can wrinkle at 2-12 % strain (`SCIENCE.md`).
- **The solver's accuracy:** with Poisson 0 the strain is within 1 % of theory and the moment within 0.2 % (two mesh densities
  agree). With Poisson 0.3 the peak strain is 11-20 % *above* the closed form: Poisson contraction and the constrained ends of a
  wide strip are real 3D effects that the textbook formula ignores. So the closed-form screen can under-estimate.

## 2. Different leathers: needs a measured card

A leather's name does not determine its behaviour. Stiffness varies about 2x across one hide (24 vs 53 MPa in one
vegetable-tanned study), and comparisons between tannages disagree (see below). So every leather in the archive gets a
**material card** (`walletsim.materials`) with provenance on each number: `measured`, `literature` or `assumed`.

| Input | How to get it | Status |
|---|---|---|
| Thickness | calipers, 3+ points | easy |
| Bending stiffness | cantilever bending-length test on a strip (`CAPTURE.md`) | easy, the most useful single number |
| Along / across backbone ratio | the same test on two strip directions | easy |
| Young's modulus, Poisson's ratio | tensile test or a lab; Poisson has no standard test | hard, so carried as a **range** |
| Strain to crack | flex-test strips over several mandrel radii | needs tests, enables `fit-law` |
| Finish and fat content | known from the supplier or not at all | recorded, not simulated |

Only one card ships: the vegetable-tanned literature range. No chrome-tanned, oil-pull-up or other values are built in,
because I did not find matched, cited numbers and I will not invent them. They come from your strips.

## 3. Ageing: what is known

I looked for quantitative models. There is no validated one. What the sources do say:

- **Pollution and acid decay (red rot).** Vegetable-tanned leather attacked by airborne sulfur dioxide loses tannin, its
  collagen oxidises, and the surface powders. It is irreversible, and condensed (catechol) tannins are reported to be more
  susceptible. The mechanism is described in conservation work; the exact chemistry is disputed (one popular account gives a
  peroxide route that I could not confirm).
- **Alkalinity.** Above about pH 6 both tannages are reported to harden and embrittle.
- **Heat and humidity.** Vegetable-tanned leather aged at 80 C and 40-80 % RH lost tensile strength and elongation at break,
  with up to 25 % weight loss. In a chrome-tanned garment leather study, stiffness fell with humidity while tensile strength,
  tear strength and elongation gradually decreased with ageing.
- **Chrome versus vegetable: no settled ranking.** One organ-leather study found chrome-tanned leather lost about 70 % tensile
  strength in a five-day air-ageing test against 15 % for vegetable-tanned. Other studies find chrome-tanned leather performs
  better, and one chrome-tanned study reports a *gain* after UV. The result depends on conditions, retanning agents and pollutants.
- **Creases and permanent set.** The sources are consumer care guides. Fibres drying out is the commonly stated cause, but I found
  **no quantitative creep, stress-relaxation or crease-formation data for leather.**
- **No validated acceleration factor** links an ageing test to years of real use.

## 4. How the simulator handles ageing

Ageing is **a measured state, not a formula.**

1. A leather has several named **states**: `new`, `aged: 28 d at the test conditions`, ... Each is a full set of properties
   (stiffness, strain to crack, thickness) measured on aged strips of that leather.
2. The same wallet and scenario are run in each state and compared: stiffer aged leather at the same spine radius gives a
   larger closing force and bulge; lower strain to crack moves the failing fold earlier.
3. Time enters only through your data. The simulator interpolates between measured states, does not extrapolate beyond the
   oldest one, and labels accelerated states as *not validated for real-time ageing*.
4. **Wear and ageing are different axes.** Wear comes from use (fold cycles, abrasion), ageing from environment (heat,
   humidity, UV, pollution, oil loss). Each shifts the material state, and they combine only through measured data.

## 5. An ageing experiment that fits the project
Strips from one leather and one hide area, 3 per condition per time point. Conditions chosen from how the wallet is really
carried (body heat, sweat humidity, light, still air). Time points such as 0, 1, 2, 4 weeks. Condition each strip the same
way before every measurement, then record thickness, weight, bending length, appearance photos, and cycles to first crack at
two or three mandrel radii. Report it as "N weeks at these conditions", never as years.

## Decisions for you
- Which leathers first, and can you get offcuts of each (or buy a wallet-weight offcut set)?
- Which ageing conditions matter for the wallets you care about?
- Is "relative ranking of leathers and thicknesses" enough as the first deliverable, with calibrated cycles after the tests?

## Sources
- Vegetable-tanned modulus: [Materials 2022, 15(15), 5107](https://mdpi.com/1996-1944/15/15/5107/html)
- Heat and humidity on vegetable-tanned leather: [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1296207424001390)
- Chrome-tanned ageing (temperature, humidity, UV): [study](https://www.researchgate.net/publication/287841114_Study_of_the_effect_of_temperature_relative_humidity_and_UV_radiation_on_chrome-tanned_leather_ageing)
- Artificially aged chrome-tanned garment leather: [study](https://www.researchgate.net/publication/289872277_Determination_of_some_physical_characteristics_of_artificially_aged_chrome_tanned_garment_leather)
- Organ leather ageing: [A Reexamination of the Aging of Organ Leather](https://www.academia.edu/83300414/A_Reexamination_of_the_Aging_of_Organ_Leather)
- Chrome versus vegetable properties: [comparison](https://www.researchgate.net/publication/383858010_Comparison_of_physical_and_mechanical_properties_of_chrome_and_vegetable_tanned_leather)
- Deterioration of vegetable-tanned leather: [Environment Leather Project](https://www.researchgate.net/publication/313425825_Deterioration_and_conservation_of_vegetable_tanned_leathers_The_Environment_Leather_Project), [CORDIS](https://cordis.europa.eu/project/id/STEP0105)
- Leather rigidity and thickness: [sheep garment leather](https://pmc.ncbi.nlm.nih.gov/articles/PMC8398511/), [Northampton softness](https://nectar.northampton.ac.uk/id/eprint/2658/)
