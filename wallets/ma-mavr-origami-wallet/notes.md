# ma-mavr-origami-wallet: notes

**What this is:** the M.A+ (Maurizio Amadei) MAV.R 1.0 One-Piece Origami Wallet (W-9), a **used** wallet sold second-hand, from the Wallet-corpus- research archive, item `map04_origami_mavr`
(`https://github.com/Sigurius23/Wallet-corpus-`, commit `bda0572`, `carpe_diem_research/wallet/designers/ma_plus/items/map04_origami_mavr/`).
**Everything here comes from a reseller's listing text and five photographs. Nothing has been measured by us.**

**Rights:** the corpus says its images are research documentation only and that no licence is granted, so they are referenced by path and are not copied into this repository.

## What the sources state (tagged `reported`: stated by the seller, not checked)
| fact | source |
|---|---|
| reversed GUIDI vegetable-tanned full-grain **pig** leather, 1 mm thick | DRIEW resale listing, corpus source `MAP08` |
| one large bill pocket, four medium pockets, four vertical card slots; .925 silver cross; hand-stitched details | same |
| one size, large; flat measurements L 14.5 x W 9.5 x **depth 1.8 cm** ("measured by hand, laid flat") | same |
| condition 9/10 ("flawless"); $395; sold out | same |

The 18 mm depth is the only dimension in the record that sets a fold radius, and it is the seller's hand measurement, not ours.

## What I read from the photographs (tagged `inferred` or `assumed`), with my confidence
| observation | confidence |
|---|---|
| closed, folded once, with a flap over the front (images 02, 05) | moderate |
| two V-shaped pleats (gussets) at the sides of the bill pocket, opened by hand in image 03 | moderate |
| a diagonal triangular crease on the back, the origami line (image 05) | moderate |
| light abrasion on the flap and the cross (image 04) | moderate; **not analysed** |
| "reversed" leather means the reverse side faces out and the grain is inside | my reading of one word; assumed |
| any edge-on view, any scale: none | n/a |

## What the report concludes (run `walletsim wallet-report wallets/ma-mavr-origami-wallet`)
See `sim/run-*/report.md` and `page.html`. Two folds are modelled:
- the **main fold**, from the seller's 18 mm depth: it wraps 16 mm (the depth less the shell on each side), so its inside radius is 8 mm and its closed-form strain 5.9 % (6 % in the simulation), range 9 % at 10 mm of stack. This is the only fold with a real datum behind it, and the datum is the whole pack's depth, so how much of that the fold really turns round is itself an assumption;
- one **gusset crease**, with the One Piece loop assumption (1 mm void) copied in, which is why it is the tightest fold in the model (50 % closed form, 21 % simulation). **That is a placeholder, not a finding**; the photograph shows the gussets but no scale.

Not modelled: the flap hinge, the bottoms of the four pockets, the card slits, the diagonal back crease, the cross, and any wear. The stiffness is the calfskin placeholder (72 MPa) because no pig leather value is on record; it changes the closing moment, not the strain.

## To turn this into a real record
Closed thickness at the spine edge-on with a ruler, and a count of the layers; one gusset crease photographed edge-on, empty and loaded; the sheet thickness; and a bend or tensile test on an offcut. The flap wear in image 04 is the one outcome this wallet already
has: photograph it and the pocket mouths with a ruler, and ask the seller how long it was carried.
