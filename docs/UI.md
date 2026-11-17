# UI outline (rough draft, not final)

## Status: feature audit against this outline and the README feature list
`walletsim build-site` reads every `wallets/<id>/wallet.yaml`, its stored report run, its 3D sketch and the stored simulator results, and writes `site/index.html`: one file, no server.
This table is the audit: every feature in the outline below and in the README's feature list, and where it stands. "Stored" means a solver result computed here and embedded; "live" means it runs in the page.

| Feature | State | Notes |
|---|---|---|
| Top bar: wordmark, Discover / Artists / Years, search, app-grid icon | **built** | the grid icon opens a menu: all wallets, simulator lab |
| Central timeline by year and designer; focused scrolling; carousel either side; series labels; arrows | **built** | click, up and down keys, or the wheel; series alternate left and right. A record with no year sits at the end as *Undated*; no year is invented |
| Read bio | **built, empty** | the panel says no biography is recorded; biographies and portraits need the designer's permission |
| Product photograph as each wallet's hero | **only if a record names a cleared `hero_image`** | none does (the corpus images are research documentation), so the wallet's cross-section is drawn from its fold structure instead |
| 3D animal models with cut zones | **built** | the cow, pig, horse and sheep are CC0 models (Quaternius, Farm Animals Pack); zones are shaded only if the record names a region, and a reference selector shows where each zone sits. **No free goat model was found**, so goats show a flat schematic hide |
| Multi-part mapping lines (component to animal) | **partly** | a dotted link joins each leather component to its animal; every record so far has one leather, so the several-animals case is untested |
| Treatment pipeline | **built** | the record's steps, or the four windows with what the record states; gaps marked *not recorded* |
| Compare two wallets | **built as a table** | not a side-by-side 3D view |
| Alternative layout of sketch 4 (Overview / Wallet / Desktop frame) | **not built** | a presentation frame, not a function |
| Behaviour: animated open and close with strain colouring | **built** | all four wallets; the WHALET's is a **functional twin** (cards and banknotes fill the pockets and the depth, radius and strain follow); the others are kinematic sketches without pockets |
| Behaviour: failure-mode list | **built** | all 14, marked computed, flagged, unknown or not modelled |
| Behaviour: fold-style comparison | **built, stored** | the wallet's main fold run as seven constructions in CalculiX |
| Behaviour: another thickness, with ranges | **built, live** | closed form recomputed as a slider moves; the stack follows the sheet where the record derives it |
| Behaviour: another leather | **not possible yet** | one material card exists (calfskin, literature) and every record uses it as a placeholder; a swap needs cards made from measured data |
| Behaviour: predicted hot spots next to real wear photos | **not built** | there is no wear model and no wear photographs; the record for the used origami notes its wear photo as not analysed |
| Lab: strain screen, damage ranking, damage-law fit | **built, live** | the same arithmetic as `walletsim screen`, `walletsim.damage.rank_locations` and `fit-law`; the fit takes your own flex data and refuses a narrow strain range |
| Lab: FEM backend check, thickness sweep, fold styles, gussets, box spine, turned edge, wallet types | **built, stored** | verbatim output of the command, how long it took, the walletsim version; refresh with `walletsim lab-run` |
| Leather types: hide group and class for every wallet, reference cards, plated hides refused | **built** | `species.py`, `cards/`; a composite hide (crocodilian, snake, stingray) is not simulated and the app and report say so |
| Leather behaviour data: cards and a coverage map | **built, mostly empty** | 3 cards; **10 of 90** property cells filled for the sheet hides (Lab: *Leather cards and coverage*) |
| Measuring a leather: cantilever bending stiffness, thickness exponent | **built, live** | Lab: *Measure a strip*; no card holds a bending stiffness yet |
| Direction, hide-region and through-the-hide layer effects in the solver | **not built** | needs measured ratios and maps; none exist for any leather |
| Aged states | **structure only** | no measured aged state exists |
| Composite model for plated hides (alligator, crocodile, snake, stingray) | **not built** | refused instead; needs plate geometry and an interface-failure model |
| Functional twin of every wallet | **four of four, at different depths** | WHALET (flap, four layered pockets, stud); One Piece and Double (each pocket between leaves takes cards, its hairpin opens and the spine follows); origami (flap with its two inner panels, bill pocket with V gussets that can be pulled open as in photo 03, four card slits; the inner lid and four medium pockets are not drawn, so its depth falls short of the seller's 18 mm and the page says so) |
| Each wallet in its own leather (colour, grain, finish, fittings) | **built** | procedural surfaces from `appearance.yaml` (calf, horse, reversed pig nap), colours read from the photographs and marked inferred; the M.A+ silver cross; the One Piece in black or red. Not the photographed texture itself: the photographs are research documentation only |
| How each part of the hide behaves | **built as statements** | choosing a zone on the animal shows what the anatomy library says about that part, with its marks; no region has measured numbers, so no result changes |
| glTF assets from a build step | **not built** | the animals are embedded as compact triangle data instead |

## The idea
A minimalist digital **Wallet Archive** styled after a modern museum or gallery exhibition (MoMA aesthetic): chronological catalogue
navigation, plus an interactive, technical breakdown of each wallet's materials and sourcing.

## Visual style
- Pure white to very light grey background, ample whitespace, clean lines, understated typography, minimal controls.
- Each wallet is framed and presented like a curated design object.

## 1. Discover: the central timeline (`sketch-1`)
- Top bar: **WALLET ARCHIVE**, tabs **Discover | Artists | Years**, a search field, an app-grid icon.
- A vertical timeline runs down the centre, organised by year and designer or artist (for example KADIR INAN / 2018,
  Marta Silva / 2020, HANS MEIER / 2023).
- **Focused scrolling:** only the wallets of the active year and designer are shown, in a carousel either side of the axis
  (labelled by series, for example "Geometric Canvas No. 3", "Zipper Wallets"); every other entry stays collapsed.
- "Read Bio" buttons open the designer's biography; arrows page the carousel.

## 2. Materials and Source: detail mode (`sketch-2`, `sketch-3`, `sketch-4`)
Selecting a wallet opens a breakdown of what it is made of:
- **3D animal models with cut zones:** monochrome, sculptural models (bovine, caprine, porcine) with a subtle wireframe grid on
  the region each piece of leather comes from.
- **Multi-part mapping:** when a wallet combines leathers, fine connecting lines map each component (exterior body, interior
  pockets, lining) to its animal model (`sketch-4`: bovine for the main body, caprine for the interior, porcine for the lining).
- **Treatment pipeline:** a numbered linear progression, for example 1 Raw hide, 2 Vegetable tanning, 3 Waxing and buffing,
  4 Distressed finishing (`sketch-3`), or the shorter 1 Raw hides, 2 Vegetable tanning, 3 Finishing and assembly (`sketch-4`).
- Side-by-side comparison of two wallets of the same designer (distressed bovine against goat leather in `sketch-2` and `sketch-3`).
- `sketch-4` is an alternative layout with its own tabs (Overview | Wallet | Desktop) and a mobile or screen-share frame.

## What each element needs from the archive

| UI element | Data it needs | Where it comes from | Caveat |
|---|---|---|---|
| Timeline entries | `designer`, `year` | the maker, catalogue | placeholders in the sketch; real names need real records |
| Carousel labels | `series`, `title` | the maker | |
| Read Bio | `designer.bio` | the maker or the designer | **rights:** biographies and photos need permission |
| Wallet images | photos | `CAPTURE.md` shot list | one hero image is chosen from the capture set |
| 3D animal and cut zone | per component: `species`, `hide_region` as a region on that species' template | the maker; often **unknown** | see below |
| Multi-part lines | components: `role` (body, pockets, lining), `leather` | construction record | each component can be a different leather |
| Treatment pipeline | ordered `process_steps`, each tagged with its window | the maker | steps are free-form; not one-to-one with the four windows (waxing and buffing is post-tanning, a distressed finish is finishing) |
| (proposed) Behaviour | simulation results | `walletsim` | see below |

## Showing uncertainty honestly
The sketches show a precise grid on the hide. Real records are rarely that exact, and the earlier research is explicit that a
region name does not guarantee a strength. So:
- A cut zone is drawn only when documented, shown **solid** if the maker gave it and **dashed** if inferred; otherwise "region
  unknown" is shown instead of a guess.
- The UI never implies strength from region. Regions are provenance, not performance.
- Every figure carries a provenance mark (measured, literature, inferred, assumed), and any simulated number is shown as a range.
- "Not modelled" failure modes are shown as such (`FAILURE_MODES.md`), never hidden.

## Where the simulation appears (proposal)
A third detail mode beside **Overview** and **Materials and Source**, called **Behaviour**:
- an animated open and close of the wallet, with a strain overlay at the folds;
- the failure-mode list for that wallet, each marked computed, flagged or not modelled;
- the fold-style comparison from [`FOLD_STYLES.md`](FOLD_STYLES.md): the same wallet with a different spine construction, side by side;
- the same wallet in another leather or thickness (a swap control driven by material cards), and the ranges that result;
- for a worn wallet, predicted hot spots next to the real wear photos.
This is the part nothing in the sketches covers yet, so it needs your input.

## Technical shape (suggested)
- A static web app (nothing to host but files): a build step reads `wallets/` and writes JSON and glTF assets; three.js shows the
  animals and the wallet models. No server, and no GPU needed to *view* it. Simulations run offline and their results are stored
  with each wallet.
- Two asset needs: **species templates** (monochrome 3D models with named regions from the anatomy library: butt, shoulder,
  belly, neck, shanks) and the **wallet models** from the capture pipeline. For the templates, check licences; a CC0 source or
  commissioned models avoids trouble. I have not verified any particular model's licence.

## Open questions
1. Are the designers and wallets real? If so, do we have permission for their photos and biographies?
2. Which first: a clickable prototype with mock data, or the material detail view for one real wallet?
3. Who are the viewers (the team, the public)? That decides how much uncertainty detail to show by default.
4. Do you want the Behaviour mode in the first version, or after the material view is solid?
