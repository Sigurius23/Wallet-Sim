# sr-whalet-sr202-2022: notes

**What this is:** the WHALET SR202 by Sruli Recht in its 2022 EDITIONS reissue, from the Wallet-corpus- research archive, item `sr005_whalet_sr202_editions_2022`
(`https://github.com/Sigurius23/Wallet-corpus-`, commit `bda0572`, `carpe_diem_research/wallet/designers/sruli_recht/items/sr005_whalet_sr202_editions_2022/`).
**Everything here comes from the maker's own product page and four product photographs. Nothing has been measured on a physical wallet.**

**Rights:** the corpus says its images are research documentation only (they belong to Sruli Recht / Atelier Sruli Recht, photography Marinó Thorlacius), so they are referenced by path and are not copied into this repository.

## What the maker states (tagged `reported`; corpus source `SRW11`, first-party)
| fact | source |
|---|---|
| "a single piece of leather, laser cut, folded into shape, formed with steam vapor, and hand tethered with black oxidized rivets to create a card wallet" | EDITIONS product page |
| horse skin; the 2022 version is "regional vegetable tanned"; the 2010 original was chromium-tanned Icelandic horse skin | same |
| one colour, Black Sable | same |
| **85 mm x 100 mm x 10 mm** | same ("Dimensions of WHALET"); not checked, and not said whether empty or loaded |
| "designed to hold 4-5 cards per slot"; the leather "needs to be eased" and "is designed to stretch to fit"; "the back section is a larger third slot, spaced for fitting bills, either folded or open"; no coin section | same |
| design "has not been altered" from the 2010 original; the same cutting file; edition of 25; made in Portugal with The Last Conspiracy | same |
| published 2022-08-03 | the shop's product feed (`SRW29`) |

**The year.** The record's year is 2022, the date of this reissue. The page says the design is from 2010, so the timeline shows 2022 with a note rather than 2010. The 2010 horse-skin WHALET (`sr003`) shares the same geometry.

## What I read from the photographs (tagged `inferred` or `assumed`), with my confidence
| observation | confidence |
|---|---|
| closed, landscape, 100 x 85 mm, a flap with rounded corners and a hole for the rivet or snap on the bottom panel | moderate |
| open (image 035): the flap, a stepped set of three rounded panels, and a larger bottom panel with a rivet or snap | moderate |
| low view (image 034): a hairpin wrap at one short end and stepped layer edges at the other | low |
| which end is the flap hinge, which folds wrap the pack, and how many layers there are | **not visible**: one oblique photograph, no edge-on view, no scale |
| the sheet thickness | **not stated**; the record assumes 1.0 mm and marks it so |

## What the report concludes (run `walletsim wallet-report wallets/sr-whalet-sr202-2022`)
See `sim/run-*/report.md` and `page.html`. Two folds are modelled, both wrapping the pack that the 10 mm depth implies (10 less the sheet on each side, 8 mm, with a lower bound of 4 mm): inside radius 4 mm, closed-form strain 11 %, simulation 10 to 12 %, up to 20 % if the pack is only 4 mm.
**Both numbers rest on the assumed 1.0 mm sheet**, which is why the derived stack is tagged `assumed`, not `inferred`. This is the mildest record in the archive so far: no tight hairpin is claimed, because nothing in the evidence shows one.

## What the record does not model
The rivets and the snap, the three card panels (which the maker says stretch to fit), the flat pattern, and wear. The elastic model treats leather that is "designed to stretch" as an ordinary sheet.

## The functional twin (`assembly.yaml` and `viewer.html`)
`assembly.yaml` is my **reconstruction** of the interior at the maker's size, read off image 035 (open) with the body width scaled to 85 mm; each number carries its provenance and about 3 mm of reading error. `walletsim wallet-viewer` turns it into
a 3D model that works like the wallet at that level: the flap opens on its hinge, the four layered pockets fill with ISO cards (0.76 mm) or folded banknotes (assumed 0.11 mm each), the layers move apart, and the closed depth, the hinge's stack, its radius and its strain follow.
Warnings appear where the contents leave the maker's statements (more than 5 cards in a slot) or where a card cannot fit the pocket.

What the twin showed that the earlier sketch could not:
- Empty, with a 1.0 mm sheet, the six layers (back panel, four walls, flap) close to **7.1 mm**, not the maker's 10 mm. Either the sheet is about **1.5 mm** (the page shows the thickness that would reproduce 10 mm for the contents you choose), or the 10 mm was taken with about four cards in it. The record's 8 mm stack came from subtracting two sheets from 10 mm, so it is an upper bound.
- The maker names three slots; the photograph shows four layered walls. The twin keeps all four and marks the second pocket's role as unknown.

What it does not know: how the walls join the back panel (they are drawn as separate plates attached at the free end), the tether tab, the flap's closure force, and the leather's stretch. Panels are rigid between the folds.

## To turn this into a real record
Measure a physical WHALET: closed depth empty and loaded, the sheet thickness at several points, an edge-on photograph at each short end with a ruler, and the flat pattern (the maker has the laser-cutting file).
