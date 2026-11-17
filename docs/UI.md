# UI outline (rough draft, not final)

Source: the user's sketches (`docs/ui/`) and written description. This is the outline to build toward, not a spec. Names in the
sketches (designers, wallets, dates) are placeholders.

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
