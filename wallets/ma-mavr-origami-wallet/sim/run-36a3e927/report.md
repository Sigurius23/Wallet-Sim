# M.A+ MAV.R 1.0 Origami Wallet (W-9): simulation report

> **This record comes from a retailer's text and product photographs, not from a wallet in hand.** Nothing is measured. Every radius and stack is an inference or an assumption, shown with its range. The results say what the model gives for those inputs, not what this wallet does.

- wallet: `ma-mavr-origami-wallet` (custom, 2 folds listed in the record, plain layup); status: photos-only
- usage: used. The seller rates it 9/10 ('flawless'). Photograph 04 shows light abrasion on the flap; it has not been analysed.
- inputs by source: 3 reported, 1 inferred, 1 literature, 5 assumed (of 10)
- leather: porcine (pig) -> Pig, hog, peccary (sheet). Reference cards for this group: none. No card holds a strain at grain crack, so this report shows the strain each fold demands, not a margin against a limit.
- model: walletsim 0.1.0, CalculiX ccx 2.21, plane-strain neo-Hookean fold, pull for 'taut' 0.1 N per mm; run `36a3e927`

## Inputs and where each came from

| input | value | source | what it changes | note |
|---|---|---|---|---|
| shell thickness | 1.0 mm | **reported** | strain at the fold (t / (2R + t)) and stiffness | DRIEW listing (corpus MAP08): 'vegetable-tanned full-grain pig leather, 1mm thickness' |
| shell stiffness E | 72 MPa | **assumed** | closing moment (not strain) | placeholder: the tensile value measured for 1.2 mm CALFskin (Mihai et al., Materials 2022, 15(15):5107); this  |
| Poisson's ratio | 0.3 - | **assumed** | small effect on moment |  |
| cards | 0  | **assumed** | the stack the spine wraps | contents not stated; the depth was measured flat |
| card thickness | 0.76 mm | **literature** | the stack the spine wraps | ISO/IEC 7810 ID-1 nominal thickness |
| other contents | 0.0 mm | **assumed** | the stack the spine wraps |  |
| closed thickness at the spine | 18.0 mm | **reported** | the inside radius of the spine fold (stack = closed thickness - 2 x shell) | DRIEW listing: Measurements (Flat) Depth 1.8 cm, 'measured by hand, laid flat'; length 14.5 cm, width 9.5 cm |
| bill-pocket gusset crease (one of two): stack it wraps | 1.0 mm | **assumed** | the inside radius of this fold | the V pleat at each side of the bill pocket, collapsed flat when the pocket is empty; the void is assumed to l |
| main fold: stack it wraps (derived from the closed thickness) | 16.0 mm | **inferred** | the inside radius of this fold | derived: closed thickness 18 mm - 2 x 1 mm of shell; the lower bound 10 mm is assumed (the pack compresses). t |
| closed thickness | 18.0 mm | **reported** | report only | DRIEW listing: Measurements (Flat) Depth 1.8 cm, 'measured by hand, laid flat'; length 14.5 cm, width 9.5 cm |

Folds modelled (stack = what each fold wraps in the closed wallet; the range is what the sweep below covers). Closed thickness: 18.0 mm.

| fold | grain | stack [mm] | range [mm] | source |
|---|---|---|---|---|
| main fold | in | 16 | 10 to 16 | **inferred** |
| bill-pocket gusset crease (one of two) | out | 1 | 0.5 to 4 | **assumed** |

## The fold(s)

| fold | grain | stack [mm] | inside radius [mm] (R/t) | tension face, loose | taut | closed-form limit | grain face (taut) |
|---|---|---|---|---|---|---|---|
| main fold | in | 16.00 | 8.00 (8.0) | 6.1 % | 6.2 % | 5.9 % | -5.7 % |
| bill-pocket gusset crease (one of two) | out | 1.00 | 0.50 (0.5) | 18.9 % (bridges) | 20.6 % (bridges) | 50.0 % | 20.6 % |

loose = the leather lies on the stack with no pull; taut = a pull of 0.1 N per mm on the panel; limit = the leather follows the stack exactly (closed form). A real wallet is somewhere between loose and the limit; an edge-on photo of the closed spine would show which.

In the figure the strip lifts off the stack before the bend. That is the model's result for leather with little or no pull on the panel; whether a real closed wallet does this is exactly what that edge-on photo would show.

**bridges** = with no pull the elastic model's leather stands further off the stack than the stack's radius, so it does not follow the stack: the FEM then understates the strain of leather that is pulled onto it (by a thread tie, by pressing or by the closed panels). Those folds are ranked by the closed form, shown next to the FEM numbers.

![fold](fold1_shape.png)
![fold](fold2_shape.png)
![strain](fold1_strain.png)
![strain](fold2_strain.png)

## How sure are we? Each fold across the range of its stack

The stacks are inferences or assumptions, so each fold is run at the low, recorded and high end of its range.

| fold | end of range | stack [mm] | inside radius (R/t) | tension face, loose | taut | closed form |
|---|---|---|---|---|---|---|
| main fold | low | 10 | 5.00 (5.00) | 9.2 % | 9.7 % | 9.1 % |
| main fold | recorded | 16 | 8.00 (8.00) | 6.1 % | 6.2 % | 5.9 % |
| bill-pocket gusset crease (one of two) | low | 0.5 | 0.25 (0.25) | closed form only | | 66.7 % |
| bill-pocket gusset crease (one of two) | recorded | 1 | 0.50 (0.50) | 18.9 % (bridges) | 20.6 % (bridges) | 50.0 % |
| bill-pocket gusset crease (one of two) | high | 4 | 2.00 (2.00) | 14.0 % | 15.3 % | 20.0 % |

## Failure modes, in the order of `docs/FAILURE_MODES.md`

| # | mode | status | for this wallet |
|---|---|---|---|
| 1 | Grain crack at the hinge | **computed** | bill-pocket gusset crease (one of two): tension-face strain 18.9 % loose to 20.6 % taut (closed-form limit 50.0 %), inside radius 0.50 mm, R/t = 0.5; the model's leather bridges this stack, so the closed form is the number to read; inside radius below 1 x t: the grain relies on the finish to hold, expect cracking (R/t=0.50); outer-fibre strain >= 20 % (screening threshold, not a validated failure criterion). Cycles to crack need flex-test data. |
| 2 | Permanent set | **not modelled** | needs a cyclic viscoplastic model and fold-and-measure data; it is the usual first visible sign of a worn hinge |
| 3 | Finish crazing or delamination | **not modelled** | a film-on-substrate model quoted in prior-research/reference/durability.md section 2b has a stiff finish buckling at 2-12 % compressive strain; at bill-pocket gusset crease (one of two) the compression face is -17.7 % and the grain is in tension, not compression |
| 4 | Stress at stitch holes | **unknown** | the record lists hand stitching, but whether it crosses or pins a fold is not recorded |
| 5 | Skive-line or thickness step | **unknown** | whether the folds are skived is not recorded; a skive line is a stiffness step where cracks start |
| 6 | Edge paint chipping | **unknown** | the edge treatment is not recorded; record it (painted edges chip where they flex) |
| 7 | Pocket-mouth and corner abrasion | **not modelled** | 3 pocket(s) recorded; needs the card-pull scenario (roadmap phase 4) and wear photos to calibrate |
| 8 | Perforation tear line | **unknown** | no recorded row of holes crosses a fold |
| 9 | Layer delamination | **not modelled** | layers are treated as perfectly bonded; the record does not say what is glued |
| 10 | Cold embrittlement | **not modelled** | needs a cold flex test; no built-in factor |
| 11 | Wet and salt flex | **not modelled** | needs a wet flex test |
| 12 | Over-drying | **not modelled** | needs a measured material state (stiffness and strain to crack at a stated humidity) |
| 13 | Long-term chemical ageing | **not modelled** | ageing enters only through measured aged states; none recorded |
| 14 | Colour, patina, water spotting | **not modelled** | appearance only |

## What to measure first

1. **closed thickness, and how much of it the main fold wraps**: Calipers across the closed wallet at the spine, edge-on photographs with a ruler, and a count of the layers. The depth now on record is the seller's hand measurement; the pockets, the cards and the bills all add to it, and nothing says how much of that depth the main fold turns round.
2. **the gusset creases**: Photograph one side pleat of the bill pocket edge-on against a ruler, empty and with a few bills in it. Their radius is only assumed here, and it decides the tightest fold in the model.
3. **sheet thickness**: Calipers at 3 or more points along the sheet, away from the edges and folds; the listing says 1 mm.
4. **where the stitching goes**: Record which seams cross or pin a fold; the listing says only that the wallet has hand-stitched details.
5. **stiffness and ageing**: No tensile or bend test of this leather exists. Any test on an offcut or a worn sample gives the closing moment; the calf value in use is a placeholder, and pig leather differs.
6. **wear history**: The seller's photograph of the flap shows light abrasion. Photograph the wear at the folds and pocket mouths with a ruler, and note how long and how it was carried.

## Reproduce

`walletsim wallet-report wallets/ma-mavr-origami-wallet` with walletsim 0.1.0. The exact `wallet.yaml` used is stored next to this report as `inputs.yaml`; every number above comes from `result.json`.
