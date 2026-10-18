# BOM pricing: Processor, Clock/Reset/Boot, Debug, Misc, SiP and generic passives

Prices checked 2026-10-17. Each line is priced at the break for 10 boards: order qty = 10 x the per-board count. When one C-number appears on several lines, the counts are summed before the break is looked up.

- **Primary source:** JLCPCB parts-library API, which gives the JLC assembly price, stock and Basic/Extended class. Raw JSON is in `scratchpad/price_core/`.
- **Other sources:** Digi-Key and Mouser product pages, read in a browser.
- **Output CSV:** `scratchpad/bom_core_debug_misc.csv`, 57 rows.
- **Generator script:** `scratchpad/scripts/build_core_bom.py`. Re-run it to refresh prices.

## Section subtotals (per board, at the qty-10-boards price)

| Group | Placements / board | Subtotal (USD) | Main cost |
|---|---|---|---|
| Processor | 1 | **44.06** | OSD6254-1G-IPM at Digi-Key, $44.062 @10 |
| Clock+Reset+Boot | 38 | **2.80** | 25 MHz oscillator $1.34, DIP switch $0.42 |
| Debug | 18 (plus the Tag-Connect footprint) | **14.40** | FT4232HL $12.60 (87 % of the section) |
| Misc | 14 parts + about 12 bare test pads | **1.06** | TMP102 $0.54, AT24C512C $0.42 |
| Passives (SiP + generic) | 176 | **0.91** | 0402/0603 MLCC and resistors, all JLC Basic except 62 Ω and 47 Ω |
| **Total parts** | **≈ 247 placements** | **63.23** | |
| JLC extended-part feeder fee (EST) | 18 unique Extended C-numbers × $3 per order | ≈ 5.40 / board | JLC's standard $3 per unique Extended part per order; confirm at quote |

The Tag-Connect cable (tool) is excluded: TC2070-IDC-NL costs $49.19 one-off at Digi-Key.

## Choices

### Processor
**OSD6254-1G-IPM**
- Digi-Key 1676-OSD6254-1G-IPM-ND: **$45.48 @1, $44.062 @10, 182 in stock**, Active, 18-week lead time. Rechecked today.
- **Mouser 415-OSD6254-1G-IPM:** $45.48 @1, **0 in stock**, 182 on order (expected 2026-10-27), 18-week factory lead time.
- **Avnet:** 0 stock, $44.06–50.36 (FindChips).
- **Octavo direct:** $22.50 list. The quantity basis is not stated, so treat it as a volume or quote price. Contact sales@octavosystems.com.
- **JLCPCB:** library part **C49026186** exists, marked Extended, "X-ray Inspection Required" and "Standard PCBA only", but has **no stock and no real price**. LCSC has no listing.
- **Assembly path:** JLC **Global Sourcing**, where JLC pre-orders the part from DK or Mouser into your JLC parts library, or **consignment**, where you buy at Digi-Key and ship the parts to JLC.
- Either way, budget about $44–46 per SiP plus handling.

### Clocks
- **25 MHz:** **ECS-2520MV-250-CN-TR** (C405464), $1.34. This is the exact oscillator fitted on the SK-AM62B-P1. It runs from 1.6–3.6 V, is ±25 ppm, and has 3477 in stock.
  - Cheaper option: YXC OT252025MJBA4SL (C717683) at $0.50, 1.8–3.3 V, ±20 ppm.
  - TI's D-note part, LMK6CE02500DDLFR (C22454733), costs $2.61 but has only 11 in stock.
- **32.768 kHz:** **Epson FC-135 Q13FC13500003** (C99010), 9 pF, 70 kΩ ESR, $0.20.
  - It has the same CL and footprint as the SK's ECS-.327-9-34QCS-TR, which LCSC sells at $1.44.
  - Load caps are 2 × 18 pF C0G, matching the SK rev-B update.
  - The JLC Basic 32 kHz crystal (C32346) is not used because its 12.5 pF CL is outside the 6–12 pF spec.

### Reset, boot and buttons
- **AND gates:**
  - 5 × SN74LVC1G08DBVR (C7666), $0.045 each.
  - 1 × SN74LVC1G11DCKR (C529281), $0.155, used as the MCU_PORz driver in the 1.8 V domain.
- **Button debounce:** 1 × SN74LVC2G17DBVR (C10429), covering RESET_REQz and the user button. The power button goes straight to the PMIC PB pin.
- **Boot DIP switch:** SHOU HAN 4-position SMD DIP switch (C6331176), $0.42.
- **Buttons:** 3 × TS-1187A-B-A-B (C318884, JLC **Basic**).
- **Button ESD:** 3 × TPD1E10B06DPYR (C48260).
- **Boot straps (20 resistors):**
  - 12 × 10 kΩ fixed straps.
  - BOOTMODE[6:3] through the DIP switch: 4 × 47 kΩ pull-downs and 4 × 1 kΩ pull-ups.

### Debug
- **USB-UART:** **FT4232HL-REEL** (C56742), **$12.60 @10, 3109 in stock at LCSC**.
  - Mouser and Digi-Key list it at $6.25 @10, but both have **0 stock**. Mouser shows it on order; Digi-Key quotes a 50-week lead time with 1000 due 2027-01-18.
  - **FT4232HL vs FT4232HQ:**
    - At Mouser both are about $6.25 @10 (on order).
    - At JLC/LCSC the HQ costs $59.72 (REEL, 1676 in stock), and the HQ-TRAY ($23.14) has no stock.
    - **The HL (LQFP-64) is cheaper and easier to inspect, so it is chosen.**
- **Supporting parts:**
  - 12 MHz crystal X322512MSB4SI (C9002, **Basic**) with 2 × 33 pF load caps.
  - 93LC46BT-I/OT EEPROM (C2649426), $0.44.
  - 2 × BLM18PG121SN1D ferrite beads (Basic).
  - 12 kΩ 1 % REF resistor.
- **LDO:** **AP2112K-3.3TRG1** (C51118), $0.17, 600 mA, Vin up to 6 V. It replaces the TPS73533, which costs $0.94–0.97 and has only 100 in stock in the DRV package.
- **Connector:** **USB-C 16-pin TYPE-C-31-M-12** (C165948), $0.19, plus 2 × 5.1 kΩ Rd resistors. A micro-B (U254-051N-4BH806) is only $0.06 cheaper, so I kept USB-C.
- **USB ESD:** TPD2E001DRLR (C150526) on D+/D− and TPD1E10B06 on VBUS, as on the SK.
- **Level buffers: 2 × SN74AVC4T245PWR** (C81461), $0.24 each.
  - **No voltage translation is needed.** MAIN_UART0/1, MCU_UART0 and WKUP_UART0 are all 3.3 V (VDDSHV0, VDDSHV_MCU/CANUART), and FT4232 VCCIO is 3.3 V.
  - **The buffers are still required for power-domain isolation.** The FT4232 runs from debug-USB VBUS so the console survives SoC power cycles, but AM62x IOs are not fail-safe. Without isolation, FT4232 TXD (idling high) would back-power an unpowered SoC.
  - The AVC4T245 has Ioff/VCC isolation: both ports go Hi-Z when either supply is off. It splits into two 2-bit halves with independent DIR, so one chip carries TX+RX for two UARTs.
  - **Two chips cover all four UARTs with TX/RX only.** The SK used 4 because it also routed RTS/CTS.
  - Dropping the buffers is not recommended. Doing so would require powering the FT4232 from VCC_3V3_SYS (losing the console across power cycles) or relying on series-resistor current limiting, which is outside TI guidance.
- **JTAG:**
  - Tag-Connect **TC2070** footprint, 14-pin, TI-14 pinout including TRSTn/EMU0/EMU1. No BOM cost.
  - 2 × TPD4E05U06DQAR ESD arrays (C138714), $0.08 each.
- **Tools (not BOM):**
  - **TC2070-IDC-NL** cable, $49.19 at Digi-Key, 410 in stock. It needs an XDS110 cTI-20 to TI-14 adapter.
  - TC2050-IDC-NL costs $39.00 but uses the ARM-10 pinout, which has no TRSTn/EMU0/EMU1. TRSTn is pulled low on the board, so a 10-pin cable cannot release JTAG. **I recommend the TC2070.**

### Misc
- **Board-ID EEPROM:** **AT24C512C-SSHD-T** (C12371), $0.42, at I2C0 address 0x51 as on the SK, for TI U-Boot board detect.
  - Drop-in cheaper option: ST M24C32-WMN6TP (C7998) at $0.30. Octavo's BRK uses an AT24C32 at 0x50. TI's AM6 EEPROM reader handles 2-byte-address parts.
- **Temperature sensor:** **TMP102AIDRLR** (C99269), $0.54. The cheaper TI TMP1075DGKR costs $0.32. The SK used TMP100 at $0.95.
- **LEDs:** 4 × green KT-0805G (Basic; the Basic library has no 0603 green) and 2 × red KT-0603R (Basic), with 330 Ω / 1 kΩ 0402 resistors.
  - Green: power, heartbeat, user1, debug-USB power.
  - Red: user2, 5 V input.
- **No BOM parts for:**
  - Test points: about 12 bare pads.
  - Fiducials: copper only. Three are recommended for the 0.5 mm BGA.
  - Mounting hardware: none.

### Passives (SiP + generic)
- **SiP Table 4-3 set: 39 caps**
  - 26 × 0.1 µF
  - 9 × 4.7 µF (0402)
  - 3 × 1 µF
  - 1 × 10 µF (0603)
  - VDDR_CORE is counted as 4 × 0.1 µF to match the table's 0.4 µF total.
- **Table 4-3 shortcut:** the table allows dropping the three core-analog sets when all core rails are tied, as they are here on Buck1. I kept them; the saving would be about $0.08.
- **IO and auxiliary rails not in Table 4-3: 26 caps (EST count)**
  - Rails: VDDSHV0–6, VDDSHV_MCU, VDDSHV_CANUART, VDDS_OSC0, VMON and VDDA_TEMP.
  - 16 × 0.1 µF and 10 × 1 µF.
- **Generic passives for clock/reset/boot/debug/misc: 111 parts (EST count; breakdown in the CSV `function` column)**
  - 44 capacitors and 67 resistors.
  - Includes I2C0/MCU_I2C0/WKUP_I2C0 pull-ups with the SK rev-B 62 Ω + 47 pF slew limiters, the EXTINTn RC, JTAG pulls, reset pulls and FT4232 support.
- **Extended passives:** only 62 Ω (C4962) and 47 Ω (C25118, "Preferred") are Extended. Substituting Basic 49.9 Ω (C25120) would save about $6 per order in feeder fees, provided the I2C fall-time check passes.
- **Not counted here:** rail bulk capacitors, the VMON divider and per-peripheral passives belong to the other sections.

**Reference unit prices for other agents (JLC Basic, at the lowest break):**

| Part | C-number | Price |
|---|---|---|
| 0402 100 nF | C1525 | $0.0051 (below 1k); $0.0041 (1k and up) |
| 0402 1 µF | C52923 | $0.0068 |
| 0402 2.2 µF | C12530 | $0.0054 |
| 0402 4.7 µF | C23733 | $0.0206 |
| 0603 4.7 µF | C19666 | $0.0218 (below 100); $0.0174 (100 and up) |
| 0603 10 µF | C19702 | $0.0271 |
| 0805 10 µF | C15850 | $0.0438 |
| 0603 22 µF | C59461 | $0.0312 |
| 0805 22 µF | C45783 | $0.1935 |
| 0402 resistors | e.g. 10 kΩ C25744 | $0.0011–0.0035 |
| 0603 120 Ω ferrite bead | C14709 | $0.0152 |

## Risks

1. **SiP supply (highest risk).**
   - Digi-Key's 182 pieces (one factory tray) are the only stock in the channel today. Mouser has 0, with 182 due on 10/27; Avnet has 0. Factory lead time is 18 weeks.
   - The price is up about 55 % from 2025 (about $27.54 → $44.06 @10).
   - Buy 10 + 1–2 spares now, or get an Octavo direct quote (the $22.50 list price suggests a large volume discount).
   - The JLC library entry has no stock, so the order will use Global Sourcing or consignment. The part is MSL4 with a 72 h floor life, so confirm JLC's dry-pack and bake handling.
   - JLC marks the part as needing X-ray inspection and Standard PCBA.
2. **FT4232H supply.**
   - FTDI is backordered at both Western distributors (Digi-Key 50-week lead time). LCSC holds 3109 at about 2× the price.
   - If the user later revisits the debug choice, a CP2105 dual UART (the design proposal's original recommendation) would cut about $12 and remove the buffers.
3. **Single-source and low-stock notes.**
   - The 93LC46BT-I/OT has 1081 in stock: fine for 10 boards, thin for 100.
   - The LMK6C oscillator is not stocked at JLC; the ECS part is used instead.
4. **Count uncertainty.**
   - The generic passive counts are engineering estimates. Expect ±20 % once the schematic exists.
   - Cost impact is under $0.25 per board.

## Decisions for the user

1. **FT4232HL source:** accept the in-stock LCSC/JLC price ($12.60), or wait for Mouser/Digi-Key restock (about $6.25, months away). JLC Global Sourcing can only buy what DK or Mouser have in stock.
2. **SiP procurement:** buy 10–12 from Digi-Key now (≈ $441–529) and consign them, or let JLC Global Sourcing buy them, or request an Octavo direct quote.
3. **Debug-port buffers:** 2 × AVC4T245 (TX/RX only, as priced) or 4 × (adds RTS/CTS on UART1, MCU_UART0 and WKUP_UART0, +$0.49).
4. **Optional cheaper swaps, about $1.6 per board in total:**
   - YXC oscillator ($0.84 saved)
   - M24C32 EEPROM ($0.12)
   - TMP1075 ($0.23)
   - 49.9 Ω Basic resistors (−2 Extended fees)
