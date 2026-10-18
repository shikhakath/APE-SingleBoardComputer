# APE-SBC: JLCPCB 6-layer stackup, BGA escape and PCB + assembly cost

Research date: 2026-10-17. The JLCPCB pages used here show "Last updated Sep 09, 2026" unless noted otherwise.

Fixed inputs:
- Board: 100 × 70 mm.
- Stackup: a JLCPCB standard stackup.
- Fab and assembly: JLCPCB PCB plus JLCPCB PCBA.
- Quantity: 5–10 prototypes.
- Main device: Octavo OSD6254-1G-IPM, a 9 × 14 mm BGA with 500 balls at 0.5 mm pitch, MSL 4, recommended reflow peak 245 °C (DS §8.3).

How the numbers were obtained:
- Every impedance width below comes from **JLCPCB's own impedance calculator**, run live on 2026-10-17. The calculator uses Polar Si9000 models (`CoatedMicrostrip1B`, `DiffEdgeCoupledCoatedMicrostrip1B`, `OffsetStripline1B1A`, `DiffOffsetStripline1B1A`).
- PCB prices come from the **live JLCPCB online quote** on the same date.
- PCBA prices come from JLCPCB's published PCBA price table. The PCBA quote cannot be run without uploading Gerbers.

---

## 1. JLCPCB capabilities that matter for 6 layers and a 0.5 mm BGA

Source: <https://jlcpcb.com/capabilities/pcb-capabilities>, unless another source is given.

| Item | JLCPCB value (multilayer, 1 oz outer) | Note for this board |
|---|---|---|
| Min trace / space, outer 1 oz | **0.09 / 0.09 mm (3.5 / 3.5 mil)**. "3 mil is acceptable in BGA fan-outs." | 2 oz outer: 0.15 / 0.15 mm |
| Min trace / space, inner | Not listed separately; the multilayer 0.09 / 0.09 mm applies. The BGA guide allows "a few traces" at 0.076 mm (3 mil) on multilayer boards. | Inner copper is 0.5 oz by default, which etches finer |
| Track width tolerance | ±20 % | JLCPCB adjusts impedance lines to meet ±10 % |
| Min via hole / diameter | **0.15 / 0.25 mm** (pad 0.30 preferred). 0.10 / 0.20 mm only for boards ≤ 1.0 mm thick with ENIG or OSP. Preferred min hole is 0.20 mm. | 0.15 mm costs extra and automatically adds the 4-wire Kelvin test and FR4 ≥ Tg155 (quote page) |
| Via annular ring | Via diameter ≥ hole + 0.10 mm (+0.15 preferred), so the ring is ≥ 0.05 mm (0.075 preferred) | 2022 POFV note gives the same 0.05 / 0.075 mm |
| PTH annular ring (component holes) | Multilayer 1 oz: 0.20 mm recommended, 0.15 mm absolute | |
| Aspect ratio | **Not published.** The rules imply about 10–11:1: 0.15 mm is allowed in 1.6 mm, and 0.10 mm only up to 1.0 mm. | JLC06161H-3313 finishes at 1.54 mm, so 0.15 mm gives **10.3:1** |
| Via-in-pad | **Epoxy (or copper-paste) filled and capped, "POFV". This is the default for 6+ layers.** It is free on 6–20 (now 6–32) layer boards; it costs extra only on 4 layers. Compatible via sizes are 0.15–0.55 mm, and holes must be ≤ 0.5 mm to fill completely. | Verified in the quote: "Via Covering: Epoxy Filled & Capped **$0.00**" on 6 layers. Sources: [capabilities](https://jlcpcb.com/capabilities/pcb-capabilities), [POFV news](https://jlcpcb.com/blog/Free-Via-in-Pad-on-6-20-Layer-PCBs-with-POFV), live quote |
| BGA pad | **≥ 0.20 mm**; pads of 0.20–0.25 mm require ENIG | Octavo's 0.20 mm NSMD land is allowed with ENIG |
| BGA pad to trace | ≥ 0.10 mm (0.09 mm minimum on multilayer) | [BGA guide](https://jlcpcb.com/help/article/bga-design-guidelines---pcb-layout-recommendations-for-bga-packages): via copper to BGA pad ≥ 0.10 mm, trace to BGA pad ≥ 0.10 mm (4-layer table) |
| BGA pitch | Not stated for fabrication. The BGA guide says that with 0.09 / 0.09 rules a trace between pads needs **0.27 mm edge-to-edge**, so "0.5 mm pitch with 0.25 mm pads is not manufacturable". It recommends 0.25 mm pads with 0.15 / 0.25 mm filled via-in-pad, and 0.09 mm traces between holes on inner layers with the unused inner pads removed. | See §4 |
| Pad to track | 0.10 mm (0.09 mm locally for BGA pads) | |
| Via hole to track | 0.20 mm (drill edge). PTH to track 0.28 mm (0.35 recommended). NPTH 0.20 mm. | Outside the BGA |
| Inner layer: via hole to copper / PTH hole to copper | **0.20 mm** / 0.30 mm | Sets the plane anti-pads |
| Via hole-to-hole / pad hole-to-hole | 0.20 mm / 0.45 mm | |
| SMD pad to pad (different nets) | 0.15 mm | |
| Same-net track spacing | 0.25 mm | |
| Solder mask | LPI, LDI since Jun 2025. **1:1 opening allowed.** Keep ≥ 0.09 mm from an opening to a neighbouring trace. **Web (dam) ≥ 0.10 mm** for green, red, yellow, blue and purple; 0.13 mm for black and white; 0.20 mm at 2 oz. Dk 3.8, ≥ 10 µm thick. | |
| Surface finish | ENIG with 1 µ" Au by default (2 µ" option). **HASL is not offered on 6+ layers.** OSP is also offered. | ENIG adds $17.40 (q5) / $18.20 (q10) |
| Impedance control | **±10 % (±5 Ω when the target ≤ 50 Ω)**. ±5 % on special request. | Costs $33.08 per order |
| Thickness / copper | 6-layer impedance stackups at 1.2, 1.6 and 2.0 mm, thickness ±10 %. Outer copper 1 or 2 oz; inner 0.5 (default), 1 or 2 oz. | |
| Materials (quote page) | FR4 TG135 (default), TG155, NP-140F, NP-155F, KB-6165, S1000H TG155, **Shengyi S1000-2M TG170** | Proposal asks for Tg ≥ 170: S1000-2M costs +$4.41 (q5) / +$5.51 (q10) over the forced TG155 |
| Copper to board edge | 0.20 mm routed, 0.40 mm V-cut | |
| Legend | Line ≥ 0.15 mm, height ≥ 1.0 mm, pad to silk ≥ 0.15 mm | |
| HDI (new, Sep 2026) | 1- to 3-step, laser blind vias 0.075–0.15 mm, 3 / 3 mil | Not needed for this board |
| PCBA: BGA and package limits | Standard PCBA: 0.35 mm min lead pitch, BGA 0.3 mm center-to-center, 01005. Economic PCBA: BGA 0.5 mm center-to-center, 0402, **reflow fixed at 255 ± 5 °C**, standard stackups only, no SPI. | [PCBA capabilities](https://jlcpcb.com/capabilities/pcb-assembly-capabilities). **Use Standard PCBA**: its reflow is 240 ± 5 °C, within the SiP's 245 °C peak, and it has SPI. |

What limits a 0.5 mm-pitch fan-out at JLCPCB:
1. The smallest legal via pad is 0.25 mm. That leaves only 0.25 mm between two vias on the outer layers.
2. A 0.25 mm BGA land leaves no room for a trace between balls.
3. A solder-mask opening must stay ≥ 0.09 mm from any trace.
4. Inner-layer drill-to-copper is 0.20 mm. At 0.5 mm via spacing the plane anti-pads therefore merge.
5. The 0.15 mm via costs extra and forces the 4-wire Kelvin test.

§4 handles each of these.

---

## 2. Stackup choice

### 2.1 The 16 predefined JLCPCB 6-layer 1.6 mm stackups

Sources:
- Layer data: <https://jlcpcb.com/impedance>.
- Labels, charge flags and finished thicknesses: the impedance-calculator data.
- Stackup fees: the live quote at qty 10. The qty-5 fee is about 0.6 % lower.

Construction rules for all 16:
- Every stackup is TOP / prepreg / [L2 core L3] / prepreg / [L4 core L5] / prepreg / BOT.
- In "A/B/C/E" variants with a centre 0.7 mm core, that core is copper-free, so L3 and L4 end up about 0.93–1.13 mm apart.
- Outer copper is 0.035 mm (1 oz finished). Inner copper is 0.0152 mm (0.5 oz).
- Dielectric constants on the JLCPCB page: 7628 = 4.4, 3313 = 4.1, 2116 = 4.16, 1080 = 3.91, core = 4.6. The **calculator uses 4.3 / 4.2**.

| Stackup | JLC label | Stackup fee (q10) | L1–L2 | L2–L3 (core) | L3–L4 | L4–L5 (core) | L5–L6 | Finished thickness |
|---|---|---|---|---|---|---|---|---|
| **JLC06161H-3313** | **Standard** (only one with no charge flag) | **$0** | 3313 0.0994 | 0.55 | 2116 0.1088 | 0.55 | 3313 0.0994 | 1.54 mm |
| JLC06161H-7628 | – | $33.08 | 7628 0.2104 | 0.40 | 7628 0.2028 | 0.40 | 7628 0.2104 | 1.55 |
| JLC06161H-1080 | – | $33.08 | 1080 0.0764 | 0.55 | 7628 0.2104 | 0.55 | 1080 0.0764 | 1.59 |
| JLC06161H-7628D | – | $67.32 | 7628 + 7628 0.424 | 0.20 | 7628 0.2008 | 0.20 | 0.424 | 1.58 |
| JLC06161H-3313C | Special | $67.32 | 3313 + 1080 0.183 | 0.40 | 1080 × 2 0.153 | 0.40 | 0.185 | 1.45 |
| **JLC06161H-3313E** | Special | **$67.32** | 3313 0.0994 | **0.10** | 7628 + **0.7 core** + 7628 = 1.121 | **0.10** | 3313 0.0994 | 1.65 |
| JLC06161H-1080C | Special | $67.32 | 1080 0.0764 | 0.075 | 1.121 | 0.075 | 0.0764 | 1.56 |
| JLC06161H-7628B | Special | $67.32 | 7628 + 1080 0.294 | 0.35 | 1080 × 2 0.153 | 0.35 | 0.294 | 1.57 |
| JLC06161H-3313D | Special | $67.32 | 3313 + 1080 0.183 | 0.25 | 7628 + 2116 + 7628 0.545 | 0.25 | 0.183 | 1.54 |
| JLC06161H-2116C | Special | $67.32 | 2116 × 2 0.246 | 0.30 | 2116 × 3 0.366 | 0.30 | 0.246 | 1.59 |
| JLC06161H-2116A | Special | $102.72 | 2116 0.1164 | 0.13 | 2116 + 0.7 core + 2116 = 0.933 | 0.13 | 0.1164 | 1.56 |
| JLC06161H-1080A | – | $102.72 | 1080 0.0764 | 0.60 | 3313 0.0994 | 0.60 | 0.0764 | 1.57 |
| JLC06161H-1080B | Special | $102.72 | 1080 0.0764 | 0.10 | 7628 + 0.7 core + 7628 = 1.121 | 0.10 | 0.0764 | 1.60 |
| JLC06161H-2116B | Special | $102.72 | 2116 0.1164 | 0.50 | 1080 × 2 0.153 | 0.50 | 0.1164 | 1.52 |
| JLC06161H-2116 | Special, Tg170 | $102.72 | 2116 + 2313 0.223 | 0.30 | 7628 × 2 0.417 | 0.30 | 0.223 | 1.59 |
| JLC06161H-7628A | Special | $102.72 | 7628 × 2 + 1080 0.512 | 0.10 | 2116 × 2 0.233 | 0.10 | 0.512 | 1.59 |

All thicknesses are in mm. The calculator also lists 3313A (marked "duplicate, do not use"), 3313B and 7628E, which are not on the order page.

### 2.2 Recommendation: JLC06161H-3313 with the order TOP / GND / SIG / **GND / PWR** / BOT

In the free 3313 stackup the tight pairs are L1–L2, **L3–L4** (0.124 mm) and L5–L6. The loose pairs, L2–L3 and L4–L5, are 0.55 mm cores.

With the proposed order TOP / GND / SIG / PWR / GND / BOT on this stackup:
- L3 signals would reference the **PWR plane** at 0.124 mm, and GND only at 0.565 mm.
- PWR and GND (L4 / L5) would be separated by 0.55 mm.

**Swapping L4 and L5** fixes both problems at no cost:
- L1 is referenced to GND on L2.
- L3 is a GND-referenced asymmetric stripline (L4 GND at 0.124 mm, L2 GND at 0.565 mm).
- Both inner reference planes are GND.

The one compromise is the bottom layer. L6 microstrip is referenced to PWR (L5), so L6 should carry only short BGA escapes and low-speed nets. Any L6 route that crosses a split in the power islands must be avoided, or the PWR copper under it must be flooded with GND.

| # | Layer | Use | Material | Thickness (mm / mil) | Cu | Dk (page / calculator) |
|---|---|---|---|---|---|---|
| L1 | TOP | Components; SiP rows 1–2 escape; microstrip (50 Ω, 90 / 100 Ω pairs) | Cu, 1 oz finished | 0.035 / 1.38 (calc T = 1.6 mil plated) | 1 oz | – |
| | Prepreg | | 3313 × 1 (RC57 %) | 0.0994 / 3.91 | | 4.1 / **4.3** |
| L2 | GND | Solid ground; reference for L1 and L3 | Cu | 0.0152 / 0.60 | 0.5 oz | – |
| | Core | | Core H/H | 0.55 / 21.65 | | 4.6 / **4.3** |
| L3 | SIG | Stripline for high-speed routes; SiP rows 3–4 escape between holes | Cu | 0.0152 / 0.60 | 0.5 oz | – |
| | Prepreg | | 2116 × 1 (RC54 %) | 0.1088 / 4.28 (H = 4.88 mil incl. Cu) | | 4.16 / **4.2** |
| L4 | **GND** | Solid ground; main reference for L3 | Cu | 0.0152 | 0.5 oz | – |
| | Core | | Core H/H | 0.55 / 21.65 | | 4.6 |
| L5 | **PWR** | Power islands (VDD_CORE / VDDS_DDR from the SiP's bottom-left corner, 3V3, 1V8, …); GND flood in the spare area | Cu | 0.0152 | 0.5 oz | – |
| | Prepreg | | 3313 × 1 | 0.0994 / 3.91 | | 4.1 / 4.3 |
| L6 | BOT | Overflow SiP escape, low-speed nets, optional passives | Cu, 1 oz finished | 0.035 | 1 oz | – |

Finished thickness is 1.5384 mm ±10 %. The quote warns that this is not 1.6 mm; confirm that before ordering. Solder mask (calculator model): 1.0 mil over the substrate, 0.6 mil over the trace, Dk 3.8.

**Alternative if the proposed order must stay:** JLC06161H-3313E (+$67.32 per order).
- Its 0.10 mm L2–L3 and L4–L5 cores and 1.12 mm L3–L4 gap make TOP / GND / SIG / PWR / GND / BOT ideal: every signal layer, **including BOT**, sits next to GND, and L4 PWR is coupled tightly to L5 GND.
- Cost: +$13.35 per board at qty 5, +$6.73 per board at qty 10. The board is also "Special", with a 1.65 mm finished thickness.
- Widths are in §3.2.
- 2116A gives the same topology with wider traces, but costs +$102.72.

---

## 3. Impedance widths

Source: JLCPCB impedance calculator, 2026-10-17. W is the drawn (bottom) width; the top width is 0.5 mil smaller (trapezoid). S is the edge-to-edge gap.

### 3.1 Chosen stackup JLC06161H-3313: TOP / GND / SIG / GND / PWR / BOT

| Target | L1 TOP and L6 BOT microstrip (ref L2 / L5, H = 3.91 mil) | L3 stripline (ref L4 at 4.88 mil, L2 at 21.65 mil) | Use |
|---|---|---|---|
| **50 Ω single-ended** | **W 5.94 mil (0.151 mm)** | **W 5.59 mil (0.142 mm)** | RGMII, SDIO / eMMC, OSPI, DPI, clocks |
| **90 Ω differential** | **W 5.34 / S 6.0 mil (0.136 / 0.152 mm)** | **W 5.03 / S 6.0 mil (0.128 / 0.152 mm)** | USB 2.0 |
| **100 Ω differential** | **W 4.69 / S 8.0 mil (0.119 / 0.203 mm)** | **W 4.33 / S 8.0 mil (0.110 / 0.203 mm)** | Ethernet MDI, HDMI TMDS, CSI-2, OLDI |

Other calculated spacings:
- 90 Ω at S = 5: L1 4.86, L3 4.61. At S = 7: L1 5.77, L3 5.31.
- 100 Ω at S = 5: L1 3.68, L3 3.48 (too narrow). At S = 7: L1 4.44, L3 4.19.

L6 is the mirror of L1, so its widths are the same, but its reference is PWR on L5.

Inside the SiP courtyard, neck down to 0.09 mm (3.5 mil) for less than about 1 mm.

Sanity check: Hammerstad-Jensen for uncoated microstrip with W = 5.69 mil average, H = 3.91, T = 1.6 and εr = 4.3 gives 53.5 Ω. Solder mask lowers that by about 2–4 Ω, which agrees with JLCPCB's 50 Ω.

### 3.2 Alternative JLC06161H-3313E: TOP / GND / SIG / PWR / GND / BOT

| Target | L1 / L6 | L3 (ref L2 at 3.94 mil, L4 at 44.7 mil) |
|---|---|---|
| 50 Ω SE | 5.94 mil | 5.31 mil |
| 90 Ω diff | 5.34 / 6.0 | 4.75 / 6.0 |
| 100 Ω diff | 4.69 / 8.0 | 4.05 / 8.0 (4.44 / 7 on L1, 3.91 / 7 on L3) |

For comparison, 2116A gives:
- 50 Ω: 7.14 (L1) / 7.00 (L3).
- 90 Ω at S6: 6.19 / 5.73.
- 100 Ω at S8: 5.48 / 5.03.

---

## 4. SiP BGA escape: is Octavo's pattern buildable at JLCPCB?

Geometry:
- Pitch 0.50 mm. Octavo land 0.20 mm NSMD.
- A via centred between 4 balls sits 0.3536 mm from each ball centre (diagonal).

| Check | 0.15 / 0.25 mm through via (recommended) | JLCPCB rule | Result |
|---|---|---|---|
| Via copper to ball land | 0.3536 − 0.125 − 0.100 = **0.129 mm (5.1 mil)** | ≥ 0.10 (BGA guide "G"); 0.09 local | ✓ |
| Via drill edge to ball land | 0.3536 − 0.075 − 0.100 = 0.179 mm | Drill to BGA pad "D" = 0 on multilayer; via hole to track 0.20 applies to tracks | ✓ (POFV fills and caps it) |
| Trace between two balls (L1, rows 1–2) | Gap 0.30 mm. A 0.09 mm trace leaves **0.105 mm** each side; a 0.076 mm trace leaves 0.112 mm. | Trace to BGA pad ≥ 0.10 (0.09) | ✓ |
| Trace between two vias, **outer layer** (via pads 0.25, gap 0.25 mm) | A 0.076 trace leaves **0.087 mm**; a 0.09 trace leaves 0.080 mm | 0.09 general; "3 mil acceptable in BGA fan-outs" | ✗ at 3.5 mil, marginal at 3 / 3 mil. **Avoid on L1 / L6.** |
| Trace between two vias, **L3 with unused inner pads removed** (hole gap 0.35 mm) | A 0.09 trace leaves **0.130 mm** to the drill | JLCPCB's BGA guide explicitly recommends this. The generic "inner via hole to copper 0.20 mm" would forbid it. | ✓ per the BGA guide. **Flag it for JLCDFM or engineering review.** |
| Via-to-via | Hole-to-hole 0.35 mm, pad-to-pad 0.25 mm | ≥ 0.20 hole-to-hole | ✓ |
| Plane anti-pad (L2 / L4 / L5) | 0.15 + 2 × 0.20 = Ø 0.55 mm. Signal vias 0.5 mm apart: anti-pads merge (0.05 mm overlap). Diagonal web 0.157 mm. | Inner via hole to copper 0.20 | Acceptable. Planes under the SiP become a diagonal mesh; GND vias connect directly with no anti-pad. |
| Mask opening to between-ball trace | With 1:1 openings (0.20 mm): **0.105 mm**. With +0.025 mm expansion: 0.080 ✗. With +0.05: 0.055 ✗. | ≥ 0.09 | Use a **1:1 opening (expansion 0)** on the SiP lands. JLCPCB's LDI supports this. |
| Mask web between SiP openings | 0.30 mm | ≥ 0.10 | ✓ |
| Aspect ratio | 1.54 / 0.15 = 10.3:1 | 0.15 mm allowed in 1.6 mm; Kelvin test added automatically | ✓ (cost: §5) |

Other via sizes:
- **0.15 / 0.30 mm** (JLCPCB's "preferred" ring) leaves only 0.104 mm to the lands, and the outer-layer between-via gap drops to 0.20 mm. Use 0.25 mm pads under the SiP.
- **0.20 / 0.30 mm** is the same at the lands (0.104 mm). It removes the outer-layer between-via channel, and the inner hole gap shrinks to 0.30 mm. It still costs $18.28 plus the Kelvin test. Not worth it.
- **0.10 / 0.20 mm** (Octavo's 4 mil drill) would be comfortable: 0.154 mm to lands, 0.105 mm on the outer channels. JLCPCB allows it **only on boards ≤ 1.0 mm**, so it does not apply at 1.6 mm.

Via-in-pad compared with the dog-bone pattern (POFV is free here, so cost does not decide it):
- JLCPCB's own answer for 0.5 mm BGAs is 0.25 mm lands with a 0.15 / 0.25 mm via in every pad.
- On this board VIP *reduces* escape capacity:
  - At 0.25 mm lands no trace fits between balls on L1, since 0.27 mm is needed.
  - L6 has the same 0.25 mm pads at ball positions.
  - So only L3 (and L4 / L5) can route between holes, and only row 1 escapes on the outer layers.
- The dog-bone instead gives three escape layers:
  - L1 between balls: rows 1–2.
  - L3 between holes, inner pads removed: rows 3–4.
  - L6 for overflow and low-speed nets.
- It also keeps Octavo's footprint and validated layout unchanged.
- **Recommendation:**
  - Use Octavo "configuration 1" dog-bone with 0.15 / 0.25 mm through vias, filled and capped (POFV, the JLCPCB default on 6 layers).
  - Escape rows 1–2 on L1. Escape rows 3–4 on L3, where the row-4 trace runs between row-3 holes with unused inner pads removed. Use L6 for overflow and low-speed nets.
  - Use VIP (0.15 / 0.25 mm in a 0.25 mm land) only, if at all, for interior GND or power balls where an extra via helps the PDN or thermals. Treat any ball with VIP as a 0.25 mm land.

### Via padstacks

| Style | Hole / pad (mm) | Where | Notes |
|---|---|---|---|
| `VIA_BGA` | **0.15 / 0.25** | Under and immediately around U1 (SiP room) only | Filled and capped, tented both sides. Remove unused pads on L2–L5. |
| `VIA_SIG` | 0.20 / 0.40 (min 0.20 / 0.35) | General signal routing and fan-out of other ICs | Ring 0.10 mm. Already inside the 0.15 mm price tier. |
| `VIA_PWR` | 0.30 / 0.50 (0.25 / 0.45 is fine) | Power and thermal stitching, GND fence | Hole ≤ 0.5 mm so POFV fills it. |

---

## 5. Altium design-rule values

Rules must carry these values. Rule names are suggestions.

**Layer Stack Manager**
- Set it up as in §2.2: 3313 / core 0.55 / 2116 0.1088 / core 0.55 / 3313.
- To reproduce JLCPCB's widths, enter the calculator's Dk values: 4.3 (3313 and cores) and 4.2 (2116).
- Outer copper T 1.6 mil, inner 0.6 mil. Trapezoid top width = bottom − 0.5 mil.
- Solder mask 1.0 / 0.6 mil, Dk 3.8.
- Create impedance profiles with the §3.1 values.
- Prefer **positive copper pours** for L2, L4 and L5 rather than negative plane layers.

| Rule | Scope | Min | Preferred | Max | Comment |
|---|---|---|---|---|---|
| Clearance (all) | All | **0.10 mm** | 0.127 | – | JLCPCB absolute minimum is 0.09 |
| Clearance, SiP room | `WithinRoom('U1_SiP')` | **0.09 mm** | 0.10 | – | Track-to-land 0.105 and via-to-land 0.129 as built |
| Clearance, SiP room L1 / L6 track-to-via | Room and L1 / L6 | 0.076 (exception only) | – | – | Only if JLCPCB accepts the 3-mil BGA allowance; default is not to route between vias on outer layers |
| Width (default) | All | 0.10 mm | 0.15 | 3.0 | Power nets get their own widths |
| Width, SiP room | Room | **0.076 mm** | 0.09 | 0.15 | Neck-down inside the courtyard |
| Width, impedance classes | NetClass | per §3.1 ± 0 | §3.1 | §3.1 | SE50_L1L6 0.151, SE50_L3 0.142 |
| Diff pair 90 Ω (USB) | DiffPairClass | W 0.136 / gap 0.152 on L1 / L6; 0.128 / 0.152 on L3 | | | Neck to 0.09 / 0.09 inside the SiP room |
| Diff pair 100 Ω (MDI / TMDS / CSI / OLDI) | DiffPairClass | 0.119 / 0.203 on L1 / L6; 0.110 / 0.203 on L3 | | | |
| Routing via style | Default `VIA_SIG` 0.20 / 0.40; SiP room `VIA_BGA` 0.15 / 0.25; power `VIA_PWR` 0.30 / 0.50 | | | | |
| Hole size | All | **0.15 mm** | 0.20 | 6.3 | NPTH min 0.50 mm |
| Minimum annular ring | Vias | **0.05 mm** | 0.075–0.10 | – | |
| Minimum annular ring | Component PTH | 0.15 mm | 0.20 | – | |
| Hole-to-hole clearance | All | **0.20 mm** | 0.25 | – | Component pad holes: 0.45 mm |
| Hole-to-track (via) outside SiP room | Clearance rule on holes | 0.20 mm (drill edge) | | | For `VIA_SIG` (pad ring 0.10) that means pad-edge to track 0.10 mm |
| PTH hole to track | | 0.28 mm | 0.35 | | |
| Polygon / plane clearance to unconnected hole (inner) | L2–L5 | **0.20 mm from the drill** | 0.20 | | Anti-pad Ø 0.55 for `VIA_BGA` |
| Inner PTH (component) hole to copper | L2–L5 | 0.30 mm | | | |
| Polygon connect | GND / power vias direct; THT pads relief (4 × 0.25 mm spoke, 0.25 air gap) | | | | |
| Unused pad shapes | `VIA_BGA` on L2–L5 | Removed | | | Tools » Remove Unused Pad Shapes (vias only) |
| SMD-to-SMD (different nets) | All | 0.15 mm | | | SiP lands are 0.30 apart |
| Solder mask expansion | Default | 0.05 mm | 0.05 | | JLCPCB LDI also allows 0 |
| Solder mask expansion | SiP lands (`InComponent('U1')`) | **0 (1:1)** | | | Keeps opening-to-trace ≥ 0.09 |
| Solder mask sliver (min web) | All | **0.10 mm** | | | 0.13 mm for black or white mask |
| Via tenting | All vias | Tented top and bottom | | | Order "Epoxy Filled & Capped" (default, free on 6 layers) |
| Paste mask expansion | All | 0 | | | JLCPCB makes its own stencil. Ask for a 0.10–0.12 mm stencil and BGA apertures of about 0.25–0.27 mm. |
| Silk to mask / silk min | | 0.15 mm | | | Text height ≥ 1.0 mm, line ≥ 0.15 mm |
| Board outline clearance | | 0.30 mm | 0.5 | | JLCPCB minimum 0.20 mm routed; V-cut 0.40 mm |
| Same-net spacing | | – | 0.25 | | JLCPCB note |

Other layout notes:
- Standard PCBA needs edge rails and fiducials. Either add 5 mm rails (making the panel 100 × 80 mm, about +$0.45 per order) or let JLCPCB add them.
- Place 3 global fiducials of 1 mm, plus 2 local fiducials diagonal to U1.
- Keep components ≥ 5 mm from the rail edges, or let JLCPCB add rails.

---

## 6. Cost

### 6.1 PCB (live JLCPCB quote, 2026-10-17)

Settings: 100 × 70 mm, 6 layers, 1.6 mm, JLC06161H-3313, ENIG 1 µ", green, 1 / 0.5 oz, impedance ±10 %, Epoxy Filled & Capped vias, min via 0.15 / (0.25 / 0.3) mm, Confirm Production file (forced). Build time 8–9 days; no faster option is offered with these choices.

| Line | Qty 5 | Qty 10 |
|---|---|---|
| 6-layer base ("special offer") | $32.00 | $47.00 |
| Via covering: Epoxy Filled & Capped (POFV) | **$0.00** | **$0.00** |
| ENIG | $17.40 | $18.20 |
| Material: S1000-2M TG170 (TG155 is forced by the 0.15 mm via: $3.48 / $3.66) | $7.89 | $9.17 |
| Impedance control ±10 % | $33.08 | $33.08 |
| Min via 0.15 mm | $34.82 | $36.56 |
| 4-wire Kelvin test (forced by the 0.15 mm via) | $17.00 | $17.47 |
| Confirm production file (forced) | $1.05 | $1.05 |
| Stackup fee, JLC06161H-3313 | $0.00 | $0.00 |
| **PCB total** | **$143.24** ($28.65 / board) | **$162.53** ($16.25 / board) |
| Same with TG155 | $138.83 | $157.02 |
| Option: 3313E stackup fee (keeps the proposed layer order) | +$66.74 | +$67.32 |
| Option: 2116A / 1080B / 2116 / 7628A stackup fee | +$100.98 | +$102.72 |
| 0.20 mm via instead of 0.15 mm (not usable under the SiP; Kelvin test still selected) | ≈ −$17 (not quoted) | −$18.28 |
| DHL Express DDP to the US, bare PCBs (estimate) | $31.59 | n/a |

### 6.2 PCBA (Standard PCBA, top-side SMT plus THT)

Sources:
- [PCBA price page](https://jlcpcb.com/help/article/pcb-assembly-price) (updated 2026-09-09).
- Baking fee: [Global Sourcing T&C](https://jlcpcb.com/help/article/global-sourcing-parts-order-terms-conditions).
- Consignment handling: [consignment guide](https://jlcpcb.com/help/article/how-to-consign-parts-to-jlcpcb).

Assumptions:
- 70 unique parts, of which 35 are extended.
- About 400 placements, giving about **1,900 SMT joints** per board (the SiP alone is 500).
- About **70 THT joints**: 40-pin header 40, RJ45 about 14, USB-A dual about 12, HDMI shell 4.
- About **20 X-ray parts** per board. The sibling BOM drafts list 18 leadless parts: the SiP, PMIC, PHY, hub, PD controller, regulators and SON ESD parts.

| Fee | Rule | Qty 5 (order) | Qty 10 (order) |
|---|---|---|---|
| Setup (Standard, single side) | $25.56; double side $51.12 | 25.56 | 25.56 |
| Stencil (single side) | $8.21; double side $16.42 | 8.21 | 8.21 |
| Feeder loading | **$1.53 per unique part, basic or extended** (Standard) × 70 | 107.10 | 107.10 |
| SMT assembly | $0.0016 / joint × 1,900 | 15.20 | 30.40 |
| THT manual assembly | $0.0164 / joint × 70, plus $3.58 hand-soldering labor per order | 9.32 | 15.06 |
| X-ray | 51–200 pcs tier $0.49 / pc (100 pcs / 200 pcs) | 49.00 | 98.00 |
| Fixture, rigid (listed for Standard; 1–29 pcs = 2 × $8.21) | Conservative; confirm in the live quote | 16.42 | 16.42 |
| Packing ($0.50 + area) + confirm parts placement ($0.45) | | 0.95 | 0.95 |
| SiP MSL-4 bake | $8 per 48 h | 8.00 | 8.00 |
| SiP consignment: 2 % handling (min $10) + DHL inbound to the HK warehouse (about $45, estimate) | VAT and duty deposit (about $63) is refundable and excluded | 55.00 | 55.00 |
| **PCBA fees total** | (components excluded) | **$294.76** | **$364.70** |

Items not included above:
- **Double-sided assembly** adds $33.77 per order: setup +$25.56, stencil +$8.21. That is +$6.75 per board at qty 5 and +$3.38 at qty 10, plus bottom-side joints at the same rate.
- **Economic PCBA**, for comparison, would cost about $40 per order less: setup $8.18, stencil $1.53, $3.07 × 35 extended = $107.45, no fixture. It is **not usable** here: reflow is fixed at 255 ± 5 °C against the SiP's 245 °C recommended peak, there is no SPI, and special stackups are not supported.
- **Global Sourcing** of the SiP, instead of consignment, has no listed fee but carries a price difference compared with Digi-Key and Mouser, takes 9–15 days, and works only from in-stock distributor parts. The JLCPCB part is C49026186 (in the library, no stock). It would remove the $55 line.
- Global-sourced connectors attract a $20 commodity-inspection fee per part type. Use JLCPCB-library connectors to avoid it.
- Not modelled: stencil or fixture storage for reorders ($4.93 each), panel fee (only for more than one design), large-board fee (only above 650 cm²). The single-board surcharge does not apply because SMT costs $3.04 per board, above the $0.48 minimum. The Economic/Standard handling fee does not apply because the price gap is above $14.93.

### 6.3 Per-board PCB + assembly (components, shipping and duties excluded)

| | Qty 5 | Qty 10 |
|---|---|---|
| PCB | $143.24 | $162.53 |
| PCBA fees | $294.76 | $364.70 |
| **Order total** | **$438.00** | **$527.23** |
| **Per board** | **$87.60** | **$52.72** |
| With 3313E stackup (proposed layer order kept) | $100.95 / board | $59.46 / board |
| With double-sided SMT | +$6.75 / board | +$3.38 / board |

The largest fixed costs are feeder loading ($107 per order), the 0.15 mm via plus Kelvin test (about $52–54), impedance control ($33) and SiP consignment ($55). Reducing the number of unique parts saves $1.53 per part number removed.

Lead time: PCB 8–9 days, Standard PCBA ≥ 4 days, THT +1 day. Consignment customs or Global Sourcing arrival can add 1–2 weeks, so order the SiP now. Ship 11–12 SiPs to cover 10 boards plus attrition.

---

## 7. Open points to confirm with JLCPCB before freezing the layout

1. Run JLCDFM or an engineering pre-review on the SiP fan-out. Three items need explicit sign-off:
   - 0.09 mm traces between `VIA_BGA` holes on L3 with unused pads removed (0.13 mm to the drill, against the generic 0.20 mm rule).
   - 1:1 mask on the 0.20 mm NSMD lands.
   - 0.129 mm from via copper to land.
2. Fixture fee applicability, and the exact X-ray count. Both are visible only in the live PCBA quote after BOM and CPL upload.
3. The 1.54 mm finished thickness of 3313 (the quote shows a reminder). Check it against the connector stack heights and the 40-pin HAT standoffs.
4. MSL-4 handling for the consigned tray: request a bake of 34 h at 125 °C, or opening within 72 h of assembly.

## Sources

- JLCPCB rigid PCB capabilities: <https://jlcpcb.com/capabilities/pcb-capabilities>
- JLCPCB impedance stackups: <https://jlcpcb.com/impedance>
- JLCPCB impedance calculator, run live: <https://jlcpcb.com/pcb-impedance-calculator>
- JLCPCB online quote, run live: <https://cart.jlcpcb.com/quote>
- BGA design guidelines: <https://jlcpcb.com/help/article/bga-design-guidelines---pcb-layout-recommendations-for-bga-packages>
- Free POFV on 6+ layers: <https://jlcpcb.com/blog/Free-Via-in-Pad-on-6-20-Layer-PCBs-with-POFV>
- PCBA price: <https://jlcpcb.com/help/article/pcb-assembly-price>
- PCBA capabilities: <https://jlcpcb.com/capabilities/pcb-assembly-capabilities>
- Global Sourcing T&C (baking fee): <https://jlcpcb.com/help/article/global-sourcing-parts-order-terms-conditions>
- Consignment guide: <https://jlcpcb.com/help/article/how-to-consign-parts-to-jlcpcb>
- Consignment note (customs agent fees): <https://jlcpcb.com/help/article/important-note-before-you-consign-the-part-to-jlcpcb>
- MSL article: <https://jlcpcb.com/help/article/123-Moisture-Sensitivity-Level-MSL-for-Electronic-Parts>
- Octavo: OSD62x-PM datasheet Rev 2.0 §8 (land 0.20–0.25 mm, 245 °C peak, MSL 4, bake 34 h at 125 °C); repo `docs/research/osd62x-pm-sip.md` §1.10.
