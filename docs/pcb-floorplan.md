# APE-SBC floorplan, for review

Image: [pcb-floorplan.png](pcb-floorplan.png). This is the plan as it was reviewed and approved on 2026-11-05. The board has since been placed from it, and [Changes during detailed placement](#changes-during-detailed-placement) lists where the real placement differs. Current results are in [pcb-placement.md](pcb-placement.md).

The plan is a **110 x 80 mm** board, up from 100 x 70. The Pi rectangle stays at the upper left, so the four holes and the 40-pin header keep their relative positions and a HAT still fits.

"Now" is the current placement. "Plan" is a first-cut estimate: big parts by hand, small parts dropped into their regions at the free spot nearest what they serve, with 10 mil spacing. Vias and routing room are not modelled, and nothing has been tuned.

## Changes during detailed placement

| Change | Why |
|---|---|
| SiP moved to the middle of the board, (52, 43), with its west, north and south blocks moving with it, and the HDMI chain and PHY moved to suit | Asked for at review, so the blocks use the whole board. It shortens CSI, MDI and TMDS and cuts the area over 100 % routing demand; USB0 and RGMII get longer |
| `J900`, `J1200`, `J800` and their blocks 12 mm east, the boot DIP and LEDs beside them | Decided at review: the bottom-right corner was empty and the south-west was full |
| 5 V converter (`U102`, `L101`) beside USB-A, 3.3 V stage (`U101`, `L100`) further south with its output caps below the inductor | Uses the freed south-west; USB-A is most of the 5 V load |
| `J702` 7.2 mm east, `U1100` to (94.2, 62.5) | The M.2 socket's north peg goes through the board and would sit under the SD socket |
| `J1501` behind the level shifters at (30, 61.3) | Its locating holes go through the board and must miss the parts on top |

The image and the table below are the plan as first reviewed, so their positions and lengths are out of date. Current numbers are in [pcb-placement.md](pcb-placement.md#before-and-after).

## The eight review points

| # | Problem | Move | Now | Plan |
|---|---|---|---|---|
| 1 | Passives scattered | One region per function on each side. A part sits by the pin it serves | Within 3 / 5 mm of their pin: 22 / 42 % | 33 / 52 % |
| 2 | Parts far from what they serve | SiP decoupling first: 21 caps under the SiP in spots clear of the vias, the rest in a ring around it. Crystal group placed by hand at its balls | Decoupling within 3 / 5 mm: 19 / 35 %. SiP caps median 10.4, worst 15.8 mm | 50 / 69 %. Median 6.1, worst 12.2 mm |
| | | | `C602` to `Y600` 7.0; `R602` to `Y600` 5.7, to H2 10.0 | 2.2; 2.1, 3.5 mm |
| | | | `C361` to N7 9.3; `R1300`-`R1304` to balls 7.7-10.5 | 2.3; 3.2-5.7 mm |
| 3 | eMMC plugs and M.2 take the back around `U1` | Module moved out west to 10-15 mm. M.2 moved to the north-east. The back around the SiP is now clear | eMMC 2.9-7.5 mm, 54 mm of meander | 10.4-15.0 mm, 13 mm of meander |
| 4 | Debug beside `U1` | FT4232, level shifters and `J1501` in the north-west corner by `J1500` | Prime space beside the SiP | 13 slow lines to the SiP |
| 5 | `SW602` in a routing channel | On the south edge beside `J800`, with 4 slow lines. The 32 strap resistors stay on the back east of the SiP, on their DPI and BOOTMODE lines | Mid-board | South edge |
| 6 | `J1200` mid-board | South edge, below the CSI balls. It is a vertical ZIF, so the cable rises from the edge | CSI 10-17 mm | 47-53 mm, limit 254 mm |
| 7 | HDMI on a diagonal | `U1000`, `U1001` and `J1000` in a straight line east of the DPI balls. M.2 no longer decides this | TMDS 38 mm, diagonal | 30 mm, straight |
| 8 | USB0 long, crosses USB1 | `J100` on the west edge, level with the SiP. Hub south-west of the SiP, `J900` below it. USB0 and USB1 still cross at the balls, by layer: USB0 on L3, USB1 on L1 | USB0 47 mm | 34 mm |

Other moves:
- The three buttons go on the west edge, south of the Pi hole and clear of any HAT, because their nets start on the SiP's west side.
- The LEDs stay in the south-east, where a HAT cannot cover them.
- Test pads for the SiP rails go on the back in the south-east.

## What got worse or did not improve

| Measure | Now | Plan | Why |
|---|---|---|---|
| Signal ratsnest | 7624 mm | 8662 mm (+14 %) | Connectors moved out to edges. The current placement was also tuned for exactly this number, and the plan is not tuned |
| Signal ratsnest crossings | 3080 | 3225 (+5 %) | Same |
| Routing demand, peak | 2.92 | 2.78 | This is the SiP's own escape, and no floorplan removes it |
| Routing demand, area over 100 % | 424 mm² | 456 mm² | Same |
| Routing demand, area over 70 % | 908 mm² | 980 mm² | Same |
| Main bus lines crossing | 19 | 43 | SD and SDIO cross once as whole bundles (6 x 6 lines). `J702` is on top and `J1300` on the back, so SD stays on the upper layers and SDIO on the lower ones. The 11 DPI and SDIO crossings are gone. RGMII TX and RX (5) and USB0 and USB1 (2) remain |
| RGMII | 8-13 mm | 14-19 mm | Room for the series row. Limit 50.8 mm |
| USB1 | 22 mm | 36 mm | Hub moved south-west. Limit 304.8 mm |
| SDIO | 10-14 mm | 34-36 mm | M.2 moved out. Meander falls from 6.4 to 1.2 mm |
| CSI | 10-17 mm | 47-53 mm | Edge connector. Limit 254 mm |
| Board area | 7000 mm² | 8800 mm² | See below |

Total meander falls from 84 to 38 mm.

These overall numbers do not prove the board routes more easily. The gains are in grouping, passives near their pins, straight buses and meanders. Step 2 will report the same measures from real positions.

## Why 110 x 80

| Size | Share of both sides used | Ratsnest, mm | Crossings | Demand peak | Over 100 %, mm² | Parts with no room | Conflicts between big parts |
|---|---|---|---|---|---|---|---|
| 100 x 70 | 56 % | 8297 | 3281 | 2.59 | 452 | 52 | `J800` on Pi hole, `J702` on `U1100`, `J1100` peg under the M.2 card, M.2 standoff off the board, and others |
| 105 x 75 | 50 % | 8479 | 3290 | 2.57 | 508 | 1 | `C911` on `L100`, `SW200` on Pi hole, `J702` on `U1100`, `J1100` peg under the card |
| **110 x 80** | **44 %** | **8662** | **3225** | **2.78** | **456** | **0** | **None** |
| 120 x 85 | 38 % | 9057 | 3223 | 2.59 | 520 | 0 | None |
| 130 x 95 | 32 % | 9651 | 3236 | 2.58 | 516 | 0 | None |

- Routing demand barely changes with size, because the peak is at the SiP. Differences of 0.2 in the peak are noise from the 2 mm grid.
- 110 x 80 is the smallest size where this floorplan fits with no forced conflict. Beyond it, only wire length grows.
- 105 x 75 could probably be made to work with more moves, but that has not been tried.
- About 34 x 17 mm stayed empty on both sides, east of `J800`. That was the cost of this size, not routing room: MDI stays west of it and TMDS north of it. The later changes above used most of it.

Every region has room: fill is 8-64 % of the free area, with the tightest being `sdio` 64 %, `pmic` 63 % and `strap` 62 %.

## Not checked yet

- **Cap sites under the SiP:** the 21 sites assume each inner signal ball can use a via site that leaves them clear. The fan-out has not been re-run on this plan.
- **Under the M.2 card:** "only 0402s" is an assumption. The clearance under the card has not been checked.
- **Under the eMMC module:** treated as empty. The mated height has not been checked.
- **Power planes:** the voltage-drop numbers and trunks from the last run no longer apply. They will be re-run after placement, and the layers shown in the power panel are the plan from that run.
- **Enclosure:** whether a larger board fits anything other than the Pi hole pattern has not been considered.
- **Existing items that remain:** `J1400` touches `H1602` and `H1603` (forced by the Pi pattern), and there are 61 mask slivers on the `J700`, `J701` and `J702` footprints.

## Decisions for you

1. Is this floorplan approved for detailed placement, or what should change?
2. Is 110 x 80 acceptable, or should I try harder for 105 x 75?
3. Are the buttons on the west edge, the boot DIP on the south edge and the LEDs in the south-east acceptable for how the board is used?

## Regenerating

From `hardware/gen`:

```bash
python floorplan.py compare
```

```bash
python floorplan.py report 110 80
```

```bash
python floorplan.py render 110 80
```
