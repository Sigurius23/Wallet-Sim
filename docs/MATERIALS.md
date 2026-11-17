# Different leathers, thicknesses and ageing

> **Correction (this revision).** Earlier versions of this repo quoted "24-53 MPa, vegetable-tanned bovine, back versus flank"
> and cited *Materials* 2022, 15(15):5107. That paper does not report that: I read its full text. It measures **footwear-upper
> calfskin, 1.2 +- 0.1 mm: E = 72 N/mm2, CV 29 % (9 specimens)**, calfskin with a chrome-tanned sheep lining 70.2 N/mm2 (CV 19.4 %),
> and Poisson's ratio 0.6 (measured by hand just before break). It does not say how the calfskin was tanned. The 24-53 range had no
> source I can show, so it is removed everywhere, defaults are now 72 MPa (labelled as that one tensile measurement), and the
> numbers below were recomputed.

You want to compare how different leathers and thicknesses bend, and how they age. This is what works today, what the
research says about ageing, and how the simulator will handle the parts that cannot be predicted.

## 0. How far the leather data goes (read this first)
The framework is in place; the data is not. `walletsim.species` sorts every hide into a group from the anatomy library and a class (`sheet`, `caution`, `composite`). `cards/*.yaml` holds the leathers a paper
describes, each value with its source. The Lab's *Leather cards and coverage* tab (`walletsim build-site`) maps every hide group against every property the simulator needs:

| | |
|---|---|
| Hide groups (the library's 12 files, split where the class differs) | 15: 9 sheet, 3 caution, 3 composite |
| Cards | 3: calfskin upper (E, thickness), Nile tilapia (thickness, tensile strength, elongation, tear), rabbit (the same four) |
| Cells filled for the sheet hides | **10 of 90** |
| Species with no card at all | pig, horse, goat, sheep, deer and the rest: nothing was found that I could read in full |
| Properties no card holds for any species | **bending stiffness, strain at grain crack, along-versus-across ratio, hide-region effect, aged state** |

What this means for behaviour today: every leather is simulated as the same isotropic elastic sheet with a placeholder stiffness, so species, tanning and hide region change nothing in the strain; only thickness does.
Strain is set by geometry (t and the fold radius); a leather decides the closing force, the capacity (strain at grain crack, unknown for every leather here) and how both change with age and direction.
- **Plated and scaled hides** (crocodilian, snake and lizard, stingray) are **refused**: `walletsim wallet-report` exits with code 3 and writes nothing, and the app says *not simulated*. The composite model they need is not built.
- **Caution hides** (ostrich, elephant and other heavy exotics, toad and turtle) run with a warning.
- **Tilapia is not Nile perch.** The only fish card is *Oreochromis niloticus*, chrome-tanned; the Sruli Recht WHALET family in the corpus is Nile perch, for which no leather data was found.
- Tensile elongation (79 % for tilapia, 110 % for rabbit) is **not** the strain at which a bent grain cracks. Nothing here compares a fold's strain with it.
- The `Measure a strip` tool (live in the Lab) turns a cantilever test and a weighed strip into a bending modulus, and fits a thickness exponent, so the first missing column can be filled from your own offcuts.
- The paper behind the calfskin card also measured stitched and perforated strips: the modulus fell from 72 to 7 to 13 N/mm2 with a seam and to 21 to 32 with perforations. That is a measured effect of seams and holes on a tensile strip, not yet used by the simulator.

## 1. Thickness: works now

`walletsim sweep` folds a strip around a fixed inside radius (what a wallet's contents impose) for several thicknesses.
180 deg fold, inside radius 3 mm, E = 72 MPa (the tensile value measured for 1.2 mm calfskin; yours will differ), Poisson 0.3, CalculiX, about 7 s per row:

| t [mm] | closed-form strain | FEM peak strain | bending moment [N mm] | relative to 0.6 mm |
|---|---|---|---|---|
| 0.6 | 9.1 % | 10.1 % | 4.2 | 1.0x |
| 1.0 | 14.3 % | 16.3 % | 18.2 | 4.3x |
| 1.4 | 18.9 % | 22.2 % | 46.3 | 10.9x |
| 2.0 | 25.0 % | 30.1 % | 120.9 | 28.5x |

- **Strain grows with thickness** at a fixed radius, which is why thick leather cracks at a tight spine fold first.
- **Stiffness grows much faster.** A homogeneous plate has bending stiffness proportional to t^3 (3.3x thicker = 37x stiffer;
  the table shows 28.5x because large strains soften the thick case). Thick leather resists closing, which pushes the spine
  to a larger radius and bulges the wallet.
- **Leather is not a homogeneous plate.** Its fibrous, layered structure may follow a different exponent, and I did not find a
  published value for it (a Northampton study fits a power law for leather softness, but the index was not readable in the
  sources I could reach). `LeatherMaterial.bending_exponent` defaults to 3, marked *assumed*; measuring strips of several
  thicknesses of one leather gives the real exponent.
- **Absolute moments scale with E, which is a placeholder.** Strains do not depend on E. Beyond roughly 20 % strain these are
  kinematic numbers: real leather leaves its linear range, and a stiff finish film is said to buckle at 2-12 % compressive strain (`prior-research/reference/durability.md` section 2b, a film-on-substrate model; I have not checked its source).
- **The solver's accuracy:** with Poisson 0 the strain is within 1 % of theory and the moment within 0.2 % (two mesh densities
  agree). With Poisson 0.3 the peak strain is 11-20 % *above* the closed form: Poisson contraction and the constrained ends of a
  wide strip are real 3D effects that the textbook formula ignores. So the closed-form screen can under-estimate.

## 2. Different leathers: needs a measured card

A leather's name does not determine its behaviour. Stiffness of one calfskin lot varied with a CV of 29 % over nine specimens
(Mihai et al. 2022), tensile *strength* varied 4-7x within one hide (see section 6), and comparisons between
tannages disagree (see below). So every leather in the archive gets a
**material card** (`walletsim.materials`) with provenance on each number: `measured`, `literature` or `assumed`.

| Input | How to get it | Status |
|---|---|---|
| Thickness | calipers, 3+ points | easy |
| Bending stiffness | cantilever bending-length test on a strip (`CAPTURE.md`) | easy, the most useful single number |
| Along / across backbone ratio | the same test on two strip directions | easy |
| Young's modulus, Poisson's ratio | tensile test or a lab; Poisson has no standard test | hard, so carried as a **range** |
| Strain to crack | flex-test strips over several mandrel radii | needs tests, enables `fit-law` |
| Finish and fat content | known from the supplier or not at all | recorded, not simulated |

Three cards ship (`cards/`): the calfskin upper (72 N/mm2, CV 29 %, tanning unknown) and the chrome-tanned Nile tilapia and rabbit skins, each read in full from an open-access paper. No oil-pull-up, goat, pig, horse or other values are built in,
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

## 6. What the treatments and anatomy library adds

Your update (`prior-research/reference/treatments/`, `anatomy/`) organises how a leather gets its properties into **four
processing windows**, each deciding different things. A material card now records what is known about each one (and
`missing_windows()` lists what to ask the maker):

| Window | Decides | Example descriptor |
|---|---|---|
| Beamhouse | stretch, softness ceiling, grain tightness; cannot be recovered later | heavy or light liming, bating, unhairing route |
| Tanning | heat resistance, water uptake, **how it ages**, whether it patinas | vegetable (which tannin), chrome, aldehyde, combination |
| Post-tanning | temper (firm or soft), colour, break, yield | retan, fatliquor level, drying, milling |
| Finishing | surface durability, stain resistance, breathability | aniline, semi-aniline, pigmented, pull-up wax, edge treatment |

The library's **property matrix** gives, for each treatment, the *direction* of change in softness, strength, elongation,
firmness, heat stability, flex resistance and so on (checked vs single-source figures are tagged). I use it as **priors and
sanity checks, not numbers**: for example, vegetable tanning pushes firmness up and flexibility down, so a vegetable-tanned
wallet whose measured bending stiffness comes out *softer* than a chrome one is a result to question before trusting. Its
central point is that every lever is zero-sum (more fatliquor means softer but a coarser break), so a card claiming
"soft and tight-grained" needs a measurement, not an assumption.

**Within-leather variability.** Tensile strength varied 4-7x across one chrome-tanned sheepskin (2,147 specimens); the
coefficient of variation inside a single leather was 0.31 (aldehyde) and 0.44 (chrome); and a survey of three species found
**no region consistently strongest** (the butt is reliably the thickest, most uniform and least stretchy, which is not the
same thing). So a card carries a spread as well as a value (`Value.cv`), and `walletsim sweep --cv 0.4 --samples 2000` shows
what that does. With a stand-in stiffness cv of 0.4, the P5 to P95 bending moment of a 1.2 mm leather runs from 7.9 to
27 N mm and that of a 0.8 mm leather from 2.5 to 8.8 (medians 14.6 and 4.7). The two ranges **overlap** (7.9 is below 8.8): a
stiff 0.8 mm piece and a soft 1.2 mm piece of the same leather can bend alike, so within-leather spread is comparable to a
0.4 mm thickness difference. The stand-in cv is a tensile-strength figure, not a stiffness measurement, so the spread of your
own leather is the first thing to measure.

**Direction.** The textbook rule (stronger and stiffer parallel to the backbone, stretchier across) is measured at one
point only; direction rotates over the hide, and one sheepskin study found elongation *higher* parallel. Direction is a
strong first-order effect for long parts, unreliable for fine layout. Tear strength varies little with direction, tensile
varies a lot (about 1.6x in strength, 2.3x in extension in one aldehyde-tanned leather), so one grain arrow understates both.

**Species.** Rules do not transfer: on goat and sheep the shoulder is strongest, not the rump; kangaroo is effectively one
region; plated hides (crocodilian, stingray, ostrich leg, snake) are composites of hard parts in a soft matrix, where failure is
an interface problem, so the sheet-based fold screen and this simulator **must not be applied to them**. `species` is a card field
for exactly this reason.

## 7. Ageing facts the treatments library adds
Each is tagged as the library tags it; none is a rate.
- **Iron-mordanted black** (ferrous sulphate and tannin) is the traditional route to true black, makes the fibre brittle and accelerates
  degradation over decades; craft guidance accepts it for an expected life of 5-10 years.
- **Vegetable-tanned leather de-tans and acidifies as it degrades** (conservation source), leaving a powdery, acidic surface.
- **Aldehyde (wet-white) tannages yellow in UV** and are the softest leathers, with the lowest water resistance.
- **Pull-up and wax finishes patinate through wear**: micro-cracks in the film reveal the lighter base, so *appearance
  change is the intended ageing mode*.
- **Edge paint is a consumable**: it chips where the edge flexes. Hand-burnished edges (vegetable tanned only) last far longer.
- **Heat stability is set by the tannage** and nothing later raises it much: chrome above 100 C, vegetable 70-85 C, transparent leathers
  50-70 C (claimed, untested independently), so a transparent leather is materially less heat-stable.
- **Over-drying** raises strength and removes elongation, and **cold** cut flex life about 4x between 23 C and -10 C in one
  automotive comparison (not a law).

## 8. Where my research and the library disagree
**Acid and hydrolytic decay of vegetable tannins.** The library says condensed tannins (mimosa, quebracho) are "not decomposed
by acids" while hydrolysable ones (chestnut, tara, sumac) are "more vulnerable to hydrolysis and acid degradation". My search
of conservation sources found the opposite statement: leather tanned with condensed tannins is more susceptible to acid
deterioration (red rot) than hydrolysable-tanned leather. They may both be right for **different decay modes** (pollution-driven
oxidative red rot versus hydrolytic de-tanning), but I could not confirm that, so it stays **unresolved**. The simulator does not
use either claim: ageing enters only through measured states. Check which mode matters for the wallets before choosing a tannin.

## Decisions for you
- Which leathers first, and can you get offcuts of each (or buy a wallet-weight offcut set)? For each, can the maker tell us the four windows?
- Which ageing conditions matter for the wallets you care about?
- Is "relative ranking of leathers and thicknesses" enough as the first deliverable, with calibrated cycles after the tests?

## Sources
- Calfskin tensile modulus 72 N/mm2 (CV 29 %), sheep lining, Poisson 0.6: Mihai, Seul, Curteza & Costea, [Materials 2022, 15(15), 5107](https://doi.org/10.3390/ma15155107) (read in full)
- Heat and humidity on vegetable-tanned leather: [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1296207424001390)
- Chrome-tanned ageing (temperature, humidity, UV): [study](https://www.researchgate.net/publication/287841114_Study_of_the_effect_of_temperature_relative_humidity_and_UV_radiation_on_chrome-tanned_leather_ageing)
- Artificially aged chrome-tanned garment leather: [study](https://www.researchgate.net/publication/289872277_Determination_of_some_physical_characteristics_of_artificially_aged_chrome_tanned_garment_leather)
- Organ leather ageing: [A Reexamination of the Aging of Organ Leather](https://www.academia.edu/83300414/A_Reexamination_of_the_Aging_of_Organ_Leather)
- Chrome versus vegetable properties: [comparison](https://www.researchgate.net/publication/383858010_Comparison_of_physical_and_mechanical_properties_of_chrome_and_vegetable_tanned_leather)
- Deterioration of vegetable-tanned leather: [Environment Leather Project](https://www.researchgate.net/publication/313425825_Deterioration_and_conservation_of_vegetable_tanned_leathers_The_Environment_Leather_Project), [CORDIS](https://cordis.europa.eu/project/id/STEP0105)
- Treatments, anatomy, property matrix and failure-mode notes: the earlier research in `prior-research/reference/` (confidence tags retained)
- Leather rigidity and thickness: [sheep garment leather](https://pmc.ncbi.nlm.nih.gov/articles/PMC8398511/), [Northampton softness](https://nectar.northampton.ac.uk/id/eprint/2658/)
