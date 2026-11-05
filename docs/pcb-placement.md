# PCB component placement

State of `hardware/PCB.PcbDoc`: outline set, every part placed (including DNP parts), stack and high-speed rules set, nothing routed. The rules, their sources and the net lists are in [`hardware/gen/README.md` section 11](../hardware/gen/README.md#high-speed-constraints).

![Placed board in Altium with the ratsnest](pcb-placement-altium.png)

*Altium, top view with both sides' copper shown and overlays hidden. Red is top copper, blue is bottom copper. DRC markers were cleared for this picture; the results are in [Checks](#checks).*

| Top side | Back side (seen from the top) |
|---|---|
| ![Top side courtyards](pcb-placement-top.png) | ![Back side courtyards](pcb-placement-back.png) |

*Offline renders from `placement.py`. Courtyards are coloured by schematic sheet, pink areas are keepouts, blue lines are the signal ratsnest. The blue outline on the back is the M.2 card.*

## Board size: 100 × 70 mm

The Raspberry Pi rectangle (85 × 56) is the upper-left part of the board. The board grows 15 mm to the right and 14 mm down, so the holes and the 40-pin header stay where a Pi has them.

| Item | Position on this board (mm from the lower-left corner) | Source |
|---|---|---|
| Corners | R3 | Pi 4 mechanical drawing |
| Mounting holes | (3.5, 17.5), (61.5, 17.5), (3.5, 66.5), (61.5, 66.5): 58 and 49 apart | Pi 4 drawing, HAT mechanical spec |
| 40-pin header centre | (32.5, 66.5), pin 1 at (8.37, 65.23) | Pi 4 drawing: 29 from the hole column, on the upper hole row |
| HAT footprint | x < 65, y > 14 | HAT spec: 65 × 56 |

### Area budget

Totals come from the real footprints, 717 parts (`placement.py budget`). The "effective" figure adds what courtyards don't count but parts still can't use:

| | mm² |
|---|---|
| All courtyards, both sides | 6,199 |
| Far side of through-hole parts (header, RJ45, USB-A, 4 holes) | 1,204 (upper bound: some space between tails is usable) |
| eMMC module beyond its two plugs (18 × 13 mm, 1 mm stack) | 161 |
| Back of the SiP (fan-out vias) | 193 |
| Back of the TFP410 (thermal vias) | 71 |
| **Effective** | **7,827** |

| Size | Both sides, mm² | Raw | Effective | Result |
|---|---|---|---|---|
| 85 × 56 (Pi) | 9,520 | 65 % | 82 % | Too tight. Also fails on edge length: see below |
| 100 × 56 | 11,200 | 55 % | 70 % | Placed in full, judged too painful to route (see the note below) |
| **100 × 70** | **14,000** | **44 %** | **56 %** | **Chosen. Same as the earlier project size, so the JLC quote stands** |

These percentages are a density estimate, not a routing result. Nothing has been trial-routed.

**Note on the 100 × 56 attempt:** when that version was reviewed, Altium's ratsnest was stale (see [Re-running](#re-running)) and overlays were on, so it looked worse than it was. The density was real, but 100 × 56 wasn't given a fair look. Going to 100 × 70 also let the layout improve, as described below.

**Why 85 × 56 fails on edges as well as area:** RJ45, USB-A and HDMI take 52 of the right edge's 56 mm, which leaves no edge for microSD or the jack. The RJ45 and USB-A must also stay outside the HAT footprint (they are 13.5 and 16 mm tall).

**Why going to 100 × 70 changed the layout rather than just scaling it:** the 14 mm strip below the Pi rectangle is outside a HAT's footprint, so tall connectors can sit on the bottom edge, directly below their buses. That removed the long RGMII and USB runs around the SiP and left the right side clear for HDMI.

## Floorplan

The SiP sits in its zero orientation at (44, 43). Of the four rotations this one has the lowest total wire length to the hand-placed parts (2,021 mm; the others are 2,776 to 3,328 mm), and each side of the ball map faces its destination:

| SiP side | Balls | Goes to | Path |
|---|---|---|---|
| Top (rows A–D) | HDR GPIO, I²C, SPI | J1400 header | Straight up, 15 mm channel |
| Top left | UARTs, JTAG, EMU | Level shifters U1504/5, FT4232, J1501 | Left and up |
| Top right | SD, SDIO | J702 on the top edge, J1300 on the back | Right |
| Right (columns 25–28) | DPI | U1000 TFP410 | 6 mm clear corridor |
| Bottom right | RGMII | U800 PHY directly below, then J800 | Straight down |
| Bottom middle | CSI | J1200 directly below | Straight down |
| Bottom left | USB | U900 hub directly below, then J900 | Straight down |
| Left (columns 1–2) | MMC0, clocks | J700 on the back, U600, Y600 | Straight out |

Bus order was checked against the pin tables by reasoning, not by trial routing:

- **HDMI:** TFP410 rotated 90° so D12–23 enter its top side and D0–11 its left side, in the same top-to-bottom order as the balls. TMDS leaves its right side in the same order as the J1000 pins, heading down and right to the right edge.
- **Ethernet:** PHY rotated 90° so its RGMII side faces up, right under the balls, and its MDI side faces down. MDI0–3 run left to right in the same order as the RJ45 pin field, apart from the MDI1/MDI2 split noted below.
- **USB:** hub upstream side up, downstream down, directly above J900.

### Placement by block

| Block | Where | Measured |
|---|---|---|
| USB-C power | J100 on the left edge, U100 beside it | CC toward J100, VBUS and VSYS out of the top |
| LM61460 3.3 V | Lower left | SW to L100: 3.4 mm. VIN caps on both sides of the part |
| TPS63070 5 V | Left | L1/L2 to L101: 4.2 mm. Output caps below, input caps above |
| PMIC | SiP's lower-left corner | LX to inductors: 2.8–3.2 mm |
| 25 MHz oscillator | U1's left edge | U600 to R600 1.7 mm, R600 to ball G1 2.2 mm |
| 32 kHz crystal | U1's left edge | Y600 to ball H1 2.9 mm. Load cap `C603` 1.9 mm from its pad, `C602` 9.6 mm. Series `R602` 8.0 mm from Y600 and 14.0 mm from ball H2 |
| PHY crystal | Right of U800 | `C801` 1.7 mm and `C800` 2.7 mm from their pads |
| Debug | Upper left | J1500 on the left edge, FT4232, level shifters toward U1 |
| eMMC module | Back, against the SiP's left edge | Outline on Mechanical 13 |
| M.2 card | Back, socket right of the SiP at the height of the SDIO balls | Card runs right over low parts. Outline on Mechanical 13 |
| microSD, audio | Top edge, right of H1603 | Codec 50 mm and its oscillator 45 mm from the nearest switcher part |
| Buttons, LEDs | Bottom edge | In the strip a HAT doesn't cover |

The 32 kHz crystal and 25 MHz oscillator have to sit at the SiP, which is also near the PMIC. They are 5.7 and 9.6 mm from the PMIC body, and 8.3 and 12.2 mm from its nearest inductor. This is the closest any sensitive part gets to a switcher, so check it first if clock noise shows up.

### Rules the placer enforces

- **Decoupling:** every SiP cap is assigned a ball on its rail (the named ball where the schematic comment gives one). Ball-side parts get first pick of the ring around U1: first the slew parts, then the SiP's caps, beads and links, then other parts marked "at SoC".
- **Channels:** small parts have 0.3 mm around their courtyards on a 0.5 mm grid, which gives 0402s a 2.5–3 × 2 mm lattice with room for their vias.
- **Corridors:** no small parts on the top side where a whole bus leaves U1 (DPI, HDR/JTAG, USB, RGMII, TMDS, MDI, D12–23).
- **Back side:** small passives, small ICs and test pads, plus the M.2 socket and eMMC plugs. Nothing under the SiP or under exposed pads (thermal vias), and no test pads or IO-bank links under the M.2 card. Power-stage parts bigger than 0402 stay on top for short loops.
- **Through-hole tails:** none under the M.2 card or eMMC module (`placement.py check` tests this). HDMI sits low on the right edge for this reason.

### Placement notes from the schematic

| Note | Result |
|---|---|
| Sheet 14: 47 pF + 62 Ω within 5 mm of the SoC balls | Met: all eight I²C slew parts are 2.9–4.8 mm from their balls |
| Sheet 06: 25 MHz oscillator within a few mm of G1 | Met: see the table above |
| `R303`–`R310` IO-bank links next to their bank's caps | 4.3–7.8 mm from a bank ball, none under the M.2 card |
| `FB311`, `C361` near ball N7 | `FB311` 4.8 mm. **`C361` 9.3 mm is not close**; move it when routing if the ring has room |
| "At SoC" series parts | Clock series `R700`, `R729`, `R1000`, `R1321` are 2.9–4.8 mm from their balls. SDIO data 0 Ω options `R1300`–`R1304` are 7.8–10.5 mm, and `R1620`/`R1621` (LEDs) 11–15 mm |
| SiP decoupling | 62 caps, median 10.6 mm from the nearest ball on their rail; the worst is `C320` at 18.3 mm, then 15.8 mm. `C320` gave up its spot to the crystal's `C603`. Many rail balls are in the package's centre block, and the eMMC module and M.2 socket take two sides of the back |
| Parts on high-speed nets | The annealer scored these as wire, which left some far from the route. 45 were re-placed for the shortest stub, see [Stubs](#stubs) |

## Where routing will be hardest

1. **SiP fan-out.** 500 balls at 0.5 mm, with every bus converging on U1. A coarse demand estimate (RUDY) is over capacity on about 650 mm² around U1, peaking at the lower-right corner where DPI, RGMII and audio meet. RUDY overstates this right at a BGA edge, but this is where layers will run out first. Whole-board demand is about 35 % of capacity (L1, L3 and L6 at 0.30 mm pitch, 50 % usable).
2. **Lower-right corner of U1: RGMII ball order.** The ball order doesn't match the PHY's pin order, so RXC and TX need layer swaps in the 5 mm between U1 and the PHY. The series resistors sit in line on the top side, which leaves little room there.
3. **Inner DPI balls.** D0–D4, HSYNC, DE, VSYNC and PCLK sit on inner columns 25–26 (rows M–T), behind the outer DPI balls, so they need L3 or L6.
4. **Above the TFP410.** D12–D23, SD and audio share the 5.8 mm between the TFP410 and SW602. Expect SD and audio to use L3 there.
5. **HDR balls on the right side.** Rows F–L in columns 25–26 carry 7 header nets that must cross the DPI escape to go up.
6. **USB0.** It runs at least 47 mm from U1 to J100 through the choke on the back, and crosses USB1 once right at the balls, because USB0's balls are on the far side of USB1's.
7. **MDI1/MDI2 at the RJ45.** The jack's pin order splits MDI1 around MDI2, so one crossing near J800 is unavoidable. H1601 also sits in the MDI band's path; the band passes above it.
8. **TMDS at U1001.** The TPD12S016's TMDS pads face J1000, so the pairs can't reach them from the TFP410's side around the package. TI's Figure 20 (SLLSE96F p22) shows the answer for this TSSOP: enter over the top end of the package, run under its body on L1, and reach each pad from the inside. Pair order here matches that figure at all three parts.
9. **eMMC lengthening.** The module is so close to U1 that its host-side nets are 2.9–9.9 mm against a 10.66 mm minimum, which comes to about 36 mm of meander. The module blocks the back, so this probably goes on L3 beside the balls.
10. **CSI at its via limit.** Two vias per net: the balls are in row 3, so one is used to escape and one to return to L1. `CSI_CLK` must also cross D0 and D1.
11. **Power on L5.** Many rails must be split out under the SiP, and L6's high-speed runs need unbroken L5 copper above them. VDD_CORE is the one to plan first (2.7 A from L200).

## High-speed constraints on this placement

Every constraint in the README's table was compared with pad-to-pad Manhattan lengths on this placement. None is impossible on length. These are the ones that aren't met as placed, or that cost something:

| Constraint | Result |
|---|---|
| Pair to anything else ≥ 30 mil (`Clr_HS_<pair>`) | **Can't be met at some pins.** Tracks of neighbouring pairs can be at most 0.38 mm apart at J1000, 0.53 mm at U1001 and 0.63 mm at U900, against 0.76 mm. TI scopes the limit to after package escape and before the connector, so these are waivers |
| 0 stubs on USB (TI Table A-7) | **Can't be met while the schematic has DNP choke bypasses.** 1.3–4.6 mm per net. No DRC rule covers this |
| MMC0 minimum 10.66 mm | Met only with meanders on 9 of the 10 nets, about 36 mm in total and 6.3 mm at worst (Altium's estimate) |
| MMC1, MMC2 mismatch 8 ps | Meanders, up to 6.0 and 14.3 mm. Both nets must also use the same layers, because L1 and L3 differ by about 0.78 ps/mm |
| RGMII data skew 60 mil | Meanders up to 1.3 mm (TX) and 4.3 mm (RX), in the crowded 5 mm above the PHY |
| CSI ≤ 2 vias | No spare via on any net |
| DPI mismatch 100 ps | 0.6 mm spare before any routing detour |
| TMDS 0 vias, L1 only | Achievable, following TI's Figure 20. It takes the whole `TMDS` corridor |

### Stubs

| Parts | Before, mm | After, mm |
|---|---|---|
| `R900`, `R901` USB-C choke bypass | 11.2, 4.9 | Now straddle `L900`: 1.3–2.1 |
| `C801`, `C800` PHY crystal load caps | 13.9, 8.8 | 1.7, 2.7 |
| `C603` 32 kHz load cap | 32 | 1.9 |
| DPI boot straps `R629`–`R643` | 6.0–17.7 | 0.4–7.3 |
| SD pull-ups `R723`–`R732` | 0.1–3.0 | 0–1.9 |
| SDIO pull-ups `R1305`–`R1310` | 4.8–11.5 | 1.5–8.5 |
| **eMMC pull-ups `R701`–`R709`, `R712`** | 8.7–17.4 | **8.1–11.9** |

Lengths are from a pad to the nearest point on the straight line between the net's other pads. The eMMC pull-ups stay long because the module and the SiP's fan-out keepout take all the nearby space on the back, and the top side there is full of the SiP's own parts. No datasheet here gives a stub limit, so this is a judgement to make when routing.

## Checks

| Check | Result |
|---|---|
| Offline courtyards (`placement.py check`) | No overlaps, all pads inside the outline, no parts over through-holes on the far side, no tails under the module or card |
| Altium `check_placement`, 6 mil, all 717 parts | 14 pairs on the first full run. 12 were tight hand-placed spots, now fixed; those moved parts and their neighbours were re-checked, not the whole board. **2 remain and are accepted:** `H1602`/`J1400` and `H1603`/`J1400` courtyards touch because the Pi fixes both positions. Their copper is 0.92 mm apart. This predates the changes in the next row; the batch DRC below is the whole-board check of the final placement |
| Altium `check_orientation` | 549 parts checked: 172 suggestions, of which the 70 that were a pure 180° flip were applied. One batch failed on a file-permission error, so about 60 parts went unchecked. `R820` and `R821` moved to the top so RGMII stays on L1 and L3. 45 stub parts then moved |
| Pads against the offline model | 20 parts on both sides: all within 0.01 mil |
| Pads against the schematic (`build.py pcb report`) | 717 components, 458 nets, every pad net matches |
| Stack, profiles, classes, xSignals and rules (`pcbsetup.py verify`) | The saved file matches `pcbsetup.py`, including separate L1, L3 and L6 entries in each profile, 62 xSignals and 133 rules |
| Nothing routed (`get_board_summary`, file read-back) | 0 vias, 0 polygons. Copper layers hold no free objects. The only free objects are 10 notes on Mechanical 13 and 1 on Multi Layer (not a pad; probably the outline, not confirmed) |

### Batch DRC

7,245 violations and 1 warning, with no stop limit in effect. The per-rule counts add up to the total. The full list is in `hardware/Project Outputs for APE - Single Board Computer/Design Rule Check - PCB.html`.

| Rule | Count | What it is |
|---|---|---|
| **Un-Routed Net** | **1,968** | **Expected: nothing is routed** |
| Silk to Solder Mask | 3,289 | Silkscreen not cleaned up yet |
| Silk to Silk | 1,766 | Silkscreen not cleaned up yet |
| Component Clearance, 10 mil | 102 | No overlaps. `J1400` touches `H1602` and `H1603` (accepted, see above); the rest have courtyards 0.2–0.3 mm apart. The 10 mil is the Altium template's value, with no source, and it stays by decision. **These hits are still open.** The two `J1400` touches can't clear, because the Pi fixes both positions |
| Solder Mask Sliver, 0.10 mm | 61 | **A real footprint issue, not placement:** a 0.07 mm web between 0.4 mm pitch pads on `J700` (32), `J701` (28) and `J702` (1), under JLCPCB's 0.10 mm |
| Matched Lengths | 24 | Altium's estimate on unrouted xSignals: RGMII data 5, MMC0 9, MMC1 5, MMC2 5. These are the meanders listed above |
| Length | 13 | `MMC0` 9, below its minimum as above. `HS_MCASP` 4 read 0 mm only because they aren't routed |
| Board Outline Clearance | 22 | All on the overlays: reference designators and the outlines of connectors that overhang the edge. No copper |
| All others | 0 | Includes every clearance, width, via-count and short-circuit rule, which have no copper to test yet |

The warning is `H1300`, an unplated hole with net GND. That is how the footprint is drawn: the SMT standoff connects through its ring pad.

## What was not verified

- **Routability.** Nothing was trial-routed; density and demand figures are estimates.
- **M.2 standoff position.** Derived from TI's SK-AM62A (socket centre line to standoff hole 30.06 mm), whose socket has the same contact-row spacing. The LOTES drawing doesn't give it. Check it against a real card.
- **Heights under the M.2 card.** Assumed 1.5 mm clearance from the standoff. Parts under it are 0402, 0603 and 0805 caps, resistors and beads, using typical package heights rather than the chosen parts' datasheets.
- **eMMC module.** Its position and orientation come from the Radxa export in the footprint notes, not from a physical module.
- **3D fit.** The footprints have no 3D bodies, so HAT and case clearance is from footprint positions and drawing heights only.
- **Pad numbering.** The assumed numbering in open items B2–B11 is still open. A correction could change a connector's rotation or a bus's order.
- **Constraints on real copper.** Every length, skew, via and clearance rule has only been compared with pad-to-pad estimates. DRC can only test them once routes exist. A rule at 0 violations today says nothing yet about the routed board.
- **Orientation.** About 60 parts missed the orientation check because a batch failed.
- **Altium's own impedance.** Altium's calculated values for the profiles were never opened or compared with JLCPCB's. The file stores 0.000 until the Impedance tab is opened.
- **eMMC module length.** The 10.66 mm minimum assumes 10 mm of trace in the module, from the research note's 10–15 mm, not a measurement.
- **Propagation figures.** 6.88 and 6.1 ps/mm are calculated from the stack, not measured or taken from JLCPCB.
- **L6 reference.** No rule can check that L5 copper is unbroken under an L6 run, or that stitching vias are present.

## Not done yet

- **Silkscreen.** Reference designators are at default size and overlap heavily; Altium also holds silk-to-silk violations for this. It's the main reason the board looks so busy with overlays on.
- **Fiducials.** 3 global and 2 local at U1; they aren't in the schematic.
- **JLC panel.** J100, J1500, J800, J900, J1000 and J1100 overhang the board edges, so edge rails on those sides won't work. Ask JLC for tab-routing or rails on free edges only.
- **Double-sided assembly.** 469 parts are on the back (40 of them unassembled test pads), so this needs JLC's double-sided SMT option, which is already in the cost estimate.

## Re-running

Data is keyed by designator in `hardware/gen/placement.csv`; the floorplan is `FIXED` in `hardware/gen/placement.py`, whose header lists the commands. `STUB_PARTS` pins the 45 re-placed parts there too. After a netlist change: `build.py check`, `build.py pcb import classes`, `placement.py add`, `placement.py apply`.

Three things to know when driving this from scripts:

- **`place_components` doesn't update the ratsnest.** The file stores connection lines in `Connections6`, and reopening doesn't rebuild them. They keep pointing at the old positions, far off the board. `placement.py apply` and `refresh` run `PCB:UpdateConnectivity` for this reason.
- **Bottom-side rotation.** Through `place_components`, a bottom part is mirrored in y and then rotated. `placement.py` works in "mirror x, then rotate" and adds 180° on export. Pad positions were checked against the model after each apply.
- **`check_placement` on all parts at once** runs far past the bridge's timeout and locks Altium. `placement_check.py` sends batches.
