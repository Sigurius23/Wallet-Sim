# Can we capture everything the simulator needs?

**No, not from photos alone.** A simulation needs three kinds of input, and photos cover only the first well.

| Need | From photos? | What closes the gap |
|---|---|---|
| **A. Geometry and construction** (outline, stitching, folds, pockets, layer order) | outline and stitching yes; hidden layers no | calipers, edge close-ups, a cross-section of a spare, optionally CT |
| **B. Material properties** (stiffness, anisotropy, thickness, finish) | **no** | measurements on strips, calipers, per-wallet sampling |
| **C. Ground truth** (real strain, real wear, real cycles to crack) | wear yes; strain and cycles no | wear photos, fold-radius photos, flex tests |

Research date: November 2026. Items marked *unverified* come from a single vendor page or have no leather-specific
study behind them. Re-check before relying on them.

## A. Geometry and construction

| What | Method | Evidence and limits |
|---|---|---|
| Panel outline, stitch holes, pitch, corner radius | calibrated flat-lay photo (ArUco mat) | the earlier prototype measured ~0.4 mm mean outline error and recovered the pitch on a **synthetic** photo; it has not been validated on real photos yet. A burnished edge biases outlines outward by 0.5-1.3 mm |
| 3D shape, open and closed | photogrammetry, or a handheld 3D scanner | glossy finishes degrade both, and cross-polarised capture is the usual mitigation. Scanner makers quote ~0.05 mm, but dark leather needs a laser or infrared mode or scanning spray. **No leather accuracy benchmark found**; we test on our own reference object. Spray should never be used on an archive wallet (try an offcut) |
| Closed thickness, bulge | calipers, edge-on photos with a scale | direct and cheap |
| **Layer order and hidden construction** (lining, reinforcements, glue lines, how slots stack) | edge close-ups; cutting open a spare; CT | photos see only edges. Industrial CT is used to inspect the inside of shoes and balls, and micro-CT has imaged leather's layers and fibre bundles in research. Whether CT separates leather layers, glue and thread in a finished **wallet** is *unverified*: one source warns that attenuation differences between low-density materials can be below the noise. No wallet CT precedent found. A pilot scan decides it |
| Skived areas, edge treatment, thread | close-ups, calipers | visible, but skive depth is not |
| Non-destructive thickness | THz spectroscopy, airborne ultrasound | research instruments only; calipers are the practical route |

**Most informative cheap experiment: the sacrificial twin.** Cut one spare copy of a wallet in half and photograph the
cross-section. Then ask how well a photo-only rebuild of the *uncut* wallet predicted what was inside. That number is
the trust level for every wallet captured from photos alone.

## B. Material properties: the biggest gap

- **Stiffness varies within one leather.** The one measurement I have read in full (calfskin upper, 1.2 mm, 9 specimens) has a modulus
  of **72 N/mm2 with a coefficient of variation of 29 %** (Mihai et al. 2022). A database range for cowhide is 30-110 MPa (not a
  measurement). So "this leather" is not one number, and which part of the hide a panel was cut from may matter.
- **Poisson's ratio:** the same paper reports 0.6 for calfskin, measured by hand just before break; it is a lateral-contraction figure
  for a fibrous sheet, not an isotropic bulk value (which cannot exceed 0.5), and there is no standard test. An older paper measures
  it for leather with an image-analysis technique.
- **Anisotropy:** leather bends and stretches differently along and across the backbone. It cannot be read from a photo.
- **What to measure instead:** folds are bending-dominated, so the most useful single measurement is **bending
  stiffness** from a cantilever bending-length test on a strip: a ruler, an offcut, a phone photo. Leather studies
  use IS 6490 or the fabric standard ASTM D1388 (a sheep garment leather study reports flexural rigidities of 94-124 in its units, and
  leather wallet stock will differ). ISO 17235:2015 (softness) is a non-destructive compression test that needs its own device.
- **Consequence:** uncertain inputs become **ranges**, not guesses. The solver runs in about 7 s per case on a CPU, so we
  can sweep stiffness over the measured range and report only conclusions that hold across it.

The placeholder stiffness in the FEM benchmark was 100 MPa. It is now 50 MPa, within the measured range. The benchmark's
strain result does not depend on it.

## C. Ground truth for validation

| Quantity | Method | Notes |
|---|---|---|
| Fold radius and shape under load | edge-on photo of the folded wallet or strip, with a scale | cheap; gives the inside radius, so the level-0 strain can be checked against the FEM shape |
| Real surface strain during a fold | digital image correlation (DIC) with a speckle or dot pattern | open-source tools exist: muDIC (Python), OpenCorr (C++), pyALDIC (2026 preprint). **No leather bending DIC study found**; an older speckle-based paper measured leather strain and Poisson's ratio. Painting a speckle pattern changes the surface, so it is for test strips only |
| Wear | hand-annotated wear maps on rectified photos of used wallets | automated leather defect segmentation exists (tick bites, wrinkles, black lines, breakage), but the datasets are small and **none covers wear or cracks**; a handful of hand-annotated wallets is realistic and enough |
| Cycles to first crack | flex tests on strips (see `CAPTURE.md`) | the only route to a calibrated "x folds" |

## What each capture tier supports

| Tier | You provide | The simulator can say |
|---|---|---|
| **1: photos + calipers** | the shot list, thicknesses, card count | geometry, stack thickness, level-0 strain per fold, interference, **relative** hot spots under assumed stiffness ranges |
| **2: + bend test + spare cross-section** | strip bending stiffness, true layer stack | FEM fold strain with the measured stiffness; photo-inference accuracy measured |
| **3: + flex tests (+ CT, DIC, scanner as available)** | flex-test data, scan or CT, strain fields | calibrated cycles to crack for that leather within the tested range; strain maps checked against measurement |

Never capturable here: moisture and ageing effects, finish adhesion, edge paint, thread pre-tension, adhesive
properties. These stay in the "unknown" column and are listed with every result.

## Proposed pilots (each answers one open question)
1. **Photo-only vs cross-section** on one wallet (needs a spare to cut).
2. **3D scan accuracy** on a known object (an ISO card and a gauge block) with the scanner or photogrammetry we choose,
   including a dark leather offcut.
3. **Bending-length test** on strips from two parts of one offcut, in both directions: how much does stiffness vary?
4. **CT pilot** on one wallet at a service with a lab CT: can it separate the layers?
5. **Fold-radius photos** of a strip bent over mandrels, compared with the FEM.

## Sources
- Leather micro-CT of layers and fibre bundles: [Micro-computed tomography studies for three-dimensional leather structure analysis](https://www.researchgate.net/publication/290041265_Micro-computed_tomography_studies_for_three-dimensional_leather_structure_analysis)
- Industrial CT of finished footwear: [Lumafield, non-destructive inspection of shoe assemblies](https://www.lumafield.com/resource/non-destructive-inspection-of-shoe-assemblies)
- Measured modulus of calfskin upper leather and sheep lining: [Materials 2022, 15(15), 5107](https://doi.org/10.3390/ma15155107)
- Leather Poisson's ratio by image analysis: [Application to leather](https://www.researchgate.net/publication/235652490_Development_of_an_image_analysis_technique_for_measurement_of_Poisson's_ratio_for_viscoelastic_materials_Application_to_leather)
- Leather flexural rigidity and drape: [Study on effect of leather rigidity and thickness](https://pmc.ncbi.nlm.nih.gov/articles/PMC8398511/)
- Softness standard: [ISO 17235:2015 (DIN Media)](https://www.dinmedia.de/en/standard/din-en-iso-17235/232360090)
- Open DIC tools: [muDIC](https://www.sciencedirect.com/science/article/pii/S2352711019301967), [pyALDIC](https://arxiv.org/pdf/2607.22755)
- Cross-polarised capture of glossy surfaces: [Cross Polarization Photogrammetry](https://www.pix-pro.com/blog/cross-polarization)
- Scanner specifications (vendor claims): [Revopoint INSPIRE 2](https://3dvf.com/en/redaction/an-affordable-3d-scanner-in-your-pocket-here-is-what-we-achieved-with-the-new-revopoint-inspire-2-3d-scanner/)
- Leather defect segmentation: [A systematic review of machine-vision leather defect inspection](https://mdpi.com/2079-9292/11/15/2383)
- Non-destructive leather thickness and moisture: [THz-TDS of leather](https://bvbvf1.bib-bvb.de/vufind/PrimoRecord/cdi_proquest_miscellaneous_1808119033), [airborne ultrasonics](https://journals.uc.edu/index.php/JALCA/article/view/3135)
