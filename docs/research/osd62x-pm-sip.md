# OSD62x-PM (OSD6254-1G-xPM) research notes for the SBC proposal

Research date: 2026-10-17. Scope: Octavo OSD62x-PM SiP (TI AM6254, 1 GB DDR4 x16, passives; 9 x 14 mm, 500-ball, 0.5 mm-pitch BGA).

Legend:
- **[C]**: Confirmed fact, read directly in the cited source.
- **[I]**: Inference or engineering judgement drawn from confirmed facts.
- **[?]**: Could not confirm, or the sources conflict.

Primary sources:
- **Datasheet Rev 2.0 (1/16/2026, current):** https://octavosystems.com/wp-content/uploads/2026/01/OSD62x-PM-Datasheet.pdf. This is a direct PDF. Octavo's own landing page (https://octavosystems.com/docs/osd62-pm-datasheet/) is gated behind a login or form. I extracted the text locally.
- **Datasheet Rev 0.4 (1/27/2025, preliminary):** https://octavosystems.com/wp-content/uploads/2025/01/OSD62x-PM-Datasheet.pdf
- **Datasheet Rev 1.0 (6/1/2025), Mouser copy:** https://www.mouser.com/pdfDocs/OSD62x-PM-DS.pdf. Mouser's bot protection blocked it, so I did not read it. Rev 2.0 says its only change from 1.0 is the VDDS_DDR capacitance in Table 4-3.
- **Product page:** https://octavosystems.com/octavo_products/osd62x-pm/
- **App notes:**
  - Power: https://octavosystems.com/app_notes/osd62x-pm-power-application-note/
  - Power Design and Budgeting: https://octavosystems.com/app_notes/osd62x-pm-power-design-and-budgeting/
  - Layout Guide: https://octavosystems.com/app_notes/osd62x-pm-layout-guide/
  - Schematic Checklist: https://octavosystems.com/app_notes/osd62x-pm-schematic-checklist/
  - Pin Mapping: https://octavosystems.com/app_notes/osd62x-pm-to-am62x-pin-mapping/
  - Thermal Guide: https://octavosystems.com/app_notes/osd62x-pm-thermal-guide/
  - Boot Chain and Debug: https://octavosystems.com/app_notes/osd62-pm-boot-chain-and-debug/

---

## 1. OSD62x-PM device details

### 1.1 Ordering and part numbers
- **[C]** Datasheet Rev 2.0, Section 2 lists exactly one value per designator:
  - Processor: 6254 (AM6254).
  - Memory: 1G (1 GB DDR4 x16).
  - Temperature: **I** only (-40 to 85 °C case).
  - Option: PM.
  - Suffix: blank for production, -ES for engineering sample.
  - The example part number is OSD6254-1G-IPM-ES. The Rev 0.4 example was "OSD6254-1G-BPM-ES", but even Rev 0.4 listed only "I" as a temperature designator.
- **[C]** The product page lists one orderable part: **OSD6254-1G-IPM, $22.50** (Octavo direct; quantity not stated) (product page).
- **[C]** The Sept 2026 one-page flyer has an ordering table that lists only OSD6254-1G-IPM. Its BRK blurb still says "Features the OSD6254-1G-BPM" (https://octavosystems.com/wp-content/uploads/2026/09/US-Octavo-Systems-OSD62x-PM-1-Page-Flyer-V2.pdf).
- **[I]** The 0–85 °C **-BPM** grade in the 2024 2-page overview (local PDF) appears never to have become a production orderable. Plan on **OSD6254-1G-IPM**.
- **[?]** The marketing copy says "up to 2 GB". No 2 GB part number or other processor designator (for example AM6252 or AM623x) appears in any 2026 document.
- **[C]** Datasheet Section 5.3 says the 93 NC balls "may be used for other purposes in future versions".
- **[I]** That suggests future pin-compatible variants, but none are announced.

### 1.2 Package and ball map
- **[C]** Package: 9 x 14 mm, 500 balls, 0.5 mm pitch, 1.3 mm height. The Layout Guide says 18 rows (A–V) x 28 columns.
- **[?]** The datasheet text says a "14 x 28 Ball Grid Array", which looks like a typo for 18 x 28.
- **[I]** An 18 x 28 grid has 504 sites, so 4 sites are depopulated, apparently the A1/V1-type corners.
- **[C]** Ball counts:
  - VSS: about 104 balls (pin-mapping app note list; my count of the datasheet Table 5-6 list).
  - NC: 93 balls (my count of the Rev 2.0 Table 5-7 list). The datasheet says "must remain unconnected"; the pin-map note says "Do not connect or route through".
  - RSVD: 10 balls (AM62X_RSVD0–8 and DDR_RSVD0), all to be left unconnected.
  - Power: about 70 balls (Thermal Guide).
  - **[I]** That leaves roughly 220 signal balls.
- **[C]** The ball map is grouped by function for easy escape. In the extracted text, each group sits along one side or in one corner:
  - Corner and top edge (rows A–D): MCU/WKUP UART, CAN, SPI, I2C, JTAG, reset/PMIC, OSPI0, McASP0, MMC1/MMC2.
  - Left edge (columns 1–2): MMC0 (eMMC), OLDI0, MCU_OSC0 and LFOSC0.
  - Bottom rows (U/V): OLDI0, USB0/1, CSI0.
  - Right edge (columns 25–28): GPMC0 and VOUT0 (24-bit RGB is pin-muxed with GPMC).
  - Bottom-right: RGMII1/2 and MDIO.
  - Center block: core and DDR power.
  - The pdftotext layout of the ball-map tables is partly scrambled. **Use Octavo's pin-mapping spreadsheet (https://octavosystems.com/osd62x-pm-to-am625x-pin-mapping/) or the Altium library as the authoritative ball list, not these notes.**
- **[C]** Ball numbers confirmed by two sources: MCU_PORZ D6, EMU0 D8, UART0_TXD B10, GPMC0_AD0 G28, MDIO0_MDC V26, DDR_VPP N10, DDR_RSVD0 F10.

### 1.3 Which AM62x signals are exposed and which are consumed internally
- **[C]** The exposed AM62x (AMC/ALW-style) signals are:
  - MCU domain: MCU_* and WKUP_* (UART, I2C, CAN, SPI, OSC0, LFOSC0, CLKOUT0).
  - Reset and power control: MCU_PORZ, MCU_RESETZ, MCU_RESETSTATZ, RESET_REQZ, RESETSTATZ, PORZ_OUT, PMIC_LPM_EN0, EXTINTN, MCU_ERRORN.
  - JTAG: TCK, TMS, TDI, TDO, TRSTN, EMU0/1.
  - UART0, I2C0, I2C1, SPI0, MCAN0, McASP0, OSPI0, GPMC0, VOUT0_DATA0–15 plus sync and clock, RGMII1/2 and MDIO0.
  - MMC0 (8-bit), MMC1, MMC2.
  - USB0/1 (DP, DM, VBUS, DRVVBUS), CSI0 (4 lanes plus clock), OLDI0 (A0–A7 plus 2 clocks), EXT_REFCLK1.
  - VMON_1P8_SOC, VMON_3P3_SOC, VMON_VSYS, VPP.
  - Other peripherals (more UARTs and SPIs, ePWM, eCAP, eQEP and so on) come out through the usual AM62x pinmux on these balls. Sources: datasheet Table 5-7 and the pin-map note.
- **[C]** These signals are consumed internally and not pinned out:
  - All DDR0_* signals.
  - CAP_VDDS0–6, CAP_VDDS_CANUART and CAP_VDDS_MCU (1 µF each, internal).
  - CSI0_RXRCALIB, USB0_RCALIB and USB1_RCALIB (499 Ω ±1 % to GND, internal).
  - Sources: datasheet Tables 4-1 and 4-2; pin-map note.
- **[C]** These rails are merged:
  - OSD **VDD_CORE** = AM62x VDD_CORE + VDDA_DDR_PLL0.
  - OSD **VDDS_DDR** = AM62x VDDS_DDR + VDDS_DDR_C + DDR4 VDD + DDR4 VDDQ, forming "one input power rail" (Power app note).
  - OSD **VDDA_TEMP** = VDDA_TEMP0 + VDDA_TEMP1.
  - Sources: datasheet Table 5-6; Power app note.
- **[C]** "The two DDR power inputs [VDDS_DDR 1.2 V, DDR_VPP 2.5 V] are the only required external DDR4 connections" (Power app note). No VTT or VREF is mentioned.
- **[I]** The board does not supply DDR VTT or VREF.

### 1.4 Power rails the board must supply
- **[C]** No PMIC, LDO, EEPROM or oscillator is integrated. The TPS65219 is external (datasheet Section 7; pin-map note).
- **[C]** Rev 2.0 datasheet Tables 7-3 and 7-4 (min / nom / max):

| Rail(s) | Voltage | Notes |
|---|---|---|
| VDD_CORE, VDDA_CORE_CSIRX0, VDDA_CORE_USB, VDD_CANUART | 0.75 V (0.715–0.79) **or** 0.85 V (0.81–0.895) | Must come from one source; VDD_CORE and VDDA_CORE_USB within ±1 %. VDD_CANUART must be always-on if Partial-IO is used. The datasheet table labels the two modes in swapped order (typo). |
| VDDR_CORE | 0.85 V (0.81–0.895) | AM62x SRAM rail. "AM62x/DDR" in Table 4-2. |
| VDDS_DDR (1.2 V only) | 1.14–1.26 V, **600 mA max** (datasheet). The Power app note says 800 mA. | Powers SoC DDR IO and the DDR4 VDD/VDDQ. |
| DDR_VPP | 2.375 / 2.5 / 2.75 V, 60 mA max | DDR4 VPP. Absolute max -0.4 to 3.0 V. |
| VDDS_OSC0, VDDA_MCU, VDDA_PLL0/1/2, VDDA_1P8_CSIRX0, VDDA_1P8_OLDI0, VDDA_1P8_USB, VDDA_TEMP, VMON_1P8_SOC | 1.8 V (1.71–1.89) | |
| VDDA_3P3_USB, VMON_3P3_SOC | 3.3 V (3.135–3.465) | |
| VDDSHV_CANUART, VDDSHV_MCU, VDDSHV0–6 | 1.8 V or 3.3 V per bank | VDDSHV4/5/6 support dynamic switching. VDDSHV5 is MMC1/SD (UHS-I needs 3.3 V to 1.8 V switching); VDDSHV4 is MMC0/eMMC; VDDSHV6 is MMC2. |
| VPP (eFuse) | 1.8 V only during OTP programming, otherwise 0 V | Leave unconnected if not programming eFuses. Needs a GPIO-enabled LDO rated 400 mA; slew below 6E4 V/s. |
| VMON_VSYS | 0–1 V divider input (0.45 V ±3 % threshold) | Tie to VSS if unused. |
| USB0/1_VBUS | 3.465 V max at the pin | Needs an external divider; a single 20 kΩ resistor is enough if VBUS stays at or below 5.5 V (Schematic Checklist). |

- **[C]** Maximum currents (Power app note Table 2-2):
  - VDD_CORE 2700 mA, VDDR_CORE 150 mA, VDDS_DDR 800 mA.
  - VDDS_OSC0 5 mA, VDDA_MCU 30 mA, PLL group 150 mA, VDDA_3P3_USB 50 mA.
  - VDDSHV0–4 + 6 group 150 mA, VDDSHV5 30 mA, VDDSHV_MCU 30 mA, VDDSHV_CANUART 10 mA, VPP 400 mA.
- **[C]** Core voltage and frequency (Power app note):
  - AM62x has **no DVS**.
  - 0.75 V allows A53 up to 1.25 GHz.
  - **1.4 GHz requires booting at 0.85 V.**

### 1.5 Integrated decoupling and required external capacitors
- **[C]** Internal capacitors (datasheet Table 4-2):
  - CAP_VDDSx: 1 µF each.
  - VDD_CORE about 6 µF, VDDR_CORE about 6 µF, VDDS_DDR about 16 µF.
  - 0.01 µF on VDDA_CORE_*, VDD_CANUART, VDDA_1P8_*, VDDA_MCU, VDDA_PLL0–2 and VDDS_OSC0.
- **[C]** Recommended external capacitors (datasheet Rev 2.0, Table 4-3). I decoded the size columns from PDF word positions, so verify against the PDF:

| Rail | Total (µF) | Parts |
|---|---|---|
| VDD_CORE | 11 | 1 x 10 µF + 6 x 0.1 µF |
| VDDA_CORE_CSIRX0 / VDDA_CORE_USB / VDD_CANUART | 4.8 each | 1 x 4.7 µF + 1 x 0.1 µF each |
| VDDR_CORE | 0.4 | Size columns show 3 x 0.1 µF **[?]**, which does not add up to 0.4. |
| VDDS_DDR | 0.3 | 3 x 0.1 µF. Rev 2.0 changed this; Rev 0.4 said 0.2. |
| DDR_VPP | 0.1 | 1 x 0.1 µF |
| VDDA_1P8_OLDI0 | 1.1 | 1 x 1 µF + 1 x 0.1 µF |
| VDDA_1P8_CSIRX0, VDDA_1P8_USB | 4.8 each | 1 x 4.7 µF + 1 x 0.1 µF |
| VDDA_MCU, VDDA_PLL0/1/2 | "4.8" | Size columns show 1 x 1 µF + 1 x 0.1 µF **[?]**, which does not match the total. Lay out a 4.7 µF footprint. |
| VPP | 2.1 | 2 x 1 µF + 1 x 0.1 µF. Schematic Checklist: 2.2 µF at the LDO output and 0.1 µF at the ball. |
| VDDA_3P3_USB | 0.1 | 1 x 0.1 µF |

- **[C]** Table 4-3 footnotes:
  - If all core rails are tied together, only the VDD_CORE capacitors are needed.
  - If all 1.8 V analog rails are tied together, only the VDDA_1P8_OLDI0 and VDDA_1P8_CSIRX0 capacitors plus 1 x 1 µF are needed.
  - Octavo recommends extra unpopulated 0.1 µF footprints for EMI/EMC.
  - Capacitors may go on either side of the PCB.
  - The Layout Guide says no capacitors are required under the device.
- **[?]** Table 4-3 does not cover the VDDSHVx IO rails.
- **[I]** For the VDDSHVx rails, follow the TI AM62x guidance and the SK-AM62B design. The CAP_VDDS caps are already inside the package.
- **[I]** Net effect: the board needs no DDR decoupling, VTT or termination network, and no CAP_VDDS or RCALIB parts. External capacitors drop to roughly 30–40 parts.

### 1.6 Recommended PMIC configuration (TPS65219 NVM variant)
- **[C]** On the OSD62-PM-BRK, Octavo uses **TPS6521903**. Octavo states that TPS6521901, TPS6521904 and TPS6521907 also work, and suggests the blank, user-programmable **TPS6521905** if none fits. LPDDR4-oriented NVMs do not suit this module because it uses DDR4. Source: Power Design and Budgeting app note.
- **[C]** TPS6521903 rail mapping on the BRK (Power Design and Budgeting):

| PMIC output | Voltage | Rails |
|---|---|---|
| BUCK1 | 0.75 V | VDD_CORE, VDD_CANUART, VDDA_CORE_USB, VDDA_CORE_CSIRX0 |
| BUCK2 | 1.8 V | Feeds LDO2 only |
| BUCK3 | 1.2 V | VDDS_DDR |
| LDO1 | 3.3 V / 1.8 V via VSEL_SD | VDDSHV5. VSEL_SD is driven by MMC1_SDWP. |
| LDO2 | 0.85 V | VDDR_CORE. It cannot run from BUCK3 because of sequencing. |
| LDO3 | 1.8 V | All 1.8 V analog rails plus both oscillators |
| LDO4 | 2.5 V | DDR_VPP |
| GPO2 | n/a | Enables a TPS22965 load switch for the 3.3 V IO rail (VDDSHV0–4 and peripherals) |

- **[C]** Rest of the BRK power chain:
  - 5 V input from USB-C (requests 3 A) or the header.
  - TLV62595 buck converts 5 V to 3.3 V for the PMIC VSYS.
  - TPS22918 switches SD card power.
  - TLV75518 is an IO-controlled LDO for VPP.
  - The PMIC sits on AM62x I2C0 at address 0x30, which the SDK assumes. Source: Power Design and Budgeting; BRK device tree.
- **[C]** TI NVM variants (TI SLVAFD0C, https://www.ti.com/document-viewer/lit/html/SLVAFD0C/GUID-6B6DAB1D-D3AD-4717-9C43-AABBE47D6E5D and its sibling pages):
  - **TPS6521901:** 5 V VSYS, DDR4, BUCK1 0.75 V, BUCK2 3.3 V IO, BUCK3 1.2 V DDR, LDO4 2.5 V VPP. A 1.8 V IO domain needs an external buck. TRM SLVUCH3.
  - **TPS6521903:** 3.3 V VSYS (or 5 V with an external 3.3 V buck enabled by GPO2), DDR4, BUCK1 0.75 V, BUCK2 1.8 V, BUCK3 1.2 V. TRM SLVUCJ2.
  - **TPS6521904:** 3.3 V or 5 V, DDR4, **BUCK1 0.85 V shared by VDD_CORE and VDDR_CORE**. Used on TI SK-AM62B-P1. TRM SLVUCL1.
  - **TPS6521907:** like 01 but with VDD_CORE at **0.85 V**. TRM SLVUCL9. Per search-result summaries of TI SLVAFD0B/0C; I did not open the TRM.
  - LPDDR4 variants: 02 (0.75 V) and 08 (0.85 V). Not applicable to this module.
- **[?]** The BRK's Linux and U-Boot device trees set BUCK1 "VDD_CORE" to **0.85 V** and add a 1.4 GHz OPP ("Requires VDD_CORE to be at 0.85V"). The Power app note says the BRK BUCK1 is 0.75 V, but its bench table reports "1.4 GHz, VDD_CORE 0.85 V". So the BRK appears to raise BUCK1 over I2C after power-up. Sources:
  - https://github.com/octavosystems/osd62-pm-brk-tisdk, kernel patch 0001
  - U-Boot patch 0001 in the same repo
- **[I]** This conflicts with the "no DVS, select at boot" guidance.
- **[I] Recommendation:** for 1.4 GHz at power-up, choose **TPS6521904** (3.3 V VSYS) or **TPS6521907** (5 V VSYS), whose NVM already sets 0.85 V. Otherwise use TPS6521903 and accept 1.25 GHz, or ask Octavo or TI whether raising VDD_CORE in SPL is supported.
- **[I] Check before committing:** TPS6521904 drives VDDR_CORE from BUCK1, while the 03 design uses LDO2. Confirm the LDO2/LDO3/LDO4 mapping in SLVUCL1 before committing to 04.

### 1.7 Power sequencing
- **[C]** Requirements (Power app note Section 2.1.5; Schematic Checklist):
  - Release MCU_PORz more than 9.5 ms after all rails are valid. The release must be glitch-free and monotonic, with a rise time under 1 µs and a 22 pF filter capacitor. MCU_PORz is in the VDDS_OSC0 (1.8 V) domain and must not float.
  - VDDR_CORE must stay at or below VDD_CORE + 0.18 V. At 0.75 V, ramp VDD_CORE first; at 0.85 V they may ramp together.
  - VDD_CORE must stay at or below VDD_CANUART + 0.18 V.
  - Slew rate under 18 mV/µs on all rails; a 1.8 V rail must take at least 100 µs to ramp.
  - Residual voltage under 0.3 V before power-up, which the TPS65219 enforces (300 mV threshold).
  - Power-down order: VDDR_CORE off before or with VDD_CORE, then VDD_CORE before or with VDD_CANUART.
  - IO pins (except the fail-safe set) must not be driven before their VDDSHV rail is up.
  - The datasheet Section 7.1 defers to the AM62x datasheet and the Power app note.
- **[C]** On the BRK, the TPS6521903 NVM sequence satisfies these requirements. The load switch, controlled by GPO2, times the 3.3 V IO rail (Power Design and Budgeting, Figure 3; the figure is an image only).

### 1.8 Reset and clock requirements
- **[C]** Clocks:
  - MCU_OSC0 needs a **25 MHz** crystal or oscillator: ±50 ppm if RGMII/RMII is used, ±100 ppm otherwise. An oscillator must be powered from VDDS_OSC0, with XO tied to VSS.
  - The 32.768 kHz WKUP_LFOSC0 is optional, with CL 6–12 pF. If unused, tie XI to GND and leave XO open.
  - Boot-mode PLL bits must be set to 25 MHz (011).
  - Source: Schematic Checklist.
- **[C]** Reset pins:
  - MCU_RESETz and RESET_REQz (at least 1.2 µs low): pull-ups of 10 k or 47 k.
  - The status outputs may be left open.
  - Do not use MCU_RESETSTATz to reset other devices (erratum i2407).
- **[C]** Boot pins:
  - GPMC0_AD0–15 are latched at PORz_OUT. Each needs its own resistor to VDDSHV3 or VSS (10 k pull-up/pull-down, or 470 Ω/47 k with DIP switches).
  - eMMC boot uses MMC0 only. SD boot uses MMC1 only.
  - Ethernet boot: see erratum i2329. USB boot: see erratum i2328.

### 1.9 Thermal
- **[C]** Measured on the BRK (4-layer, 1.2 x 4 in, solid planes, 25 °C ambient): 1.4 W gives Tj of about 48.6 °C, so **θJA ≈ 16.9 °C/W** (Thermal Guide).
- **[C]** The Thermal Guide reports no θJC, θJB or Ψ values. The PCB is the main heat path, through about 100 GND balls and about 70 power balls. Use solid planes; a heatsink is not normally used.
- **[C]** Power numbers (Power Design and Budgeting):
  - Board-level worst case: 12.4 W, which Octavo says is not realistic.
  - Nominal: about 2.5 W at 5 V.
  - Bench at 5 V: Linux idle 1.5 W (1.4 GHz), stress-ng 2.25 W, deep sleep 0.25 W.
- **[C]** Case temperature rating: -40 to 85 °C (datasheet).
- **[I]** The 85 °C case limit, not Tj, is the binding constraint in an enclosure.

### 1.10 Layout guidelines
Source for all items: Layout Guide (rev 10/03/2025) and the BRK Getting Started guide.
- **[C] Board:** the reference is **4 layers**: 1.6 mm FR4 (Tg175), 1 oz copper, components on one side only.
  - L1: signals and escape.
  - L2: solid GND.
  - L3: power plane with 3.3 V as reference. VDDSHV5 is routed separately because it switches.
  - L4: escape, power routing and a GND flood.
- **[C] Rules used on the BRK:** 3/3 mil trace and space; via with 4 mil drill and 3 mil annular ring, giving a **10 mil (0.254 mm) finished pad**. Alternative: 6 mil drill with 2 mil annular ring. Landing pad 0.20 mm (NSMD, IPC-7351A minimum).
- **[C] Escape:** one via centered between 4 balls ("configuration 1"; other configurations are not recommended). The outer two rows escape on top and the inner two rows on the bottom. One 3/3 trace fits between balls, and a row-4 trace passes between two row-3 vias.
- **[C]** At least 1 via per GND ball.
- **[C]** VDD_CORE and VDDS_DDR enter from the bottom-left corner. Avoid bottlenecks on power rails.
- **[C]** The 25 MHz crystal goes close to the device.
- **[C]** High-speed routing follows TI SPRAAR7J and SCAA082A. The Schematic Checklist adds: USB 90 Ω differential with no series parts on DP/DM.
- **[C]** Via-in-pad, HDI and microvias are **not mentioned**. The design intent is through-vias only: "designed to minimize the number of PCB layers".
- **[I]** A 4 mil (0.1 mm) mechanical drill through 1.6 mm is a 16:1 aspect ratio, beyond most fabs' standard capability.
- **[I]** The 6 mil drill / 10 mil pad option (0.15 / 0.25 mm) is within advanced-standard capability at many prototype fabs. Alternatively, use a thinner board. Confirm with the chosen fab.
- **[I]** For an SBC with Ethernet PHYs, HDMI or other bridges, USB hubs and so on, 6 layers gives better reference planes for RGMII, USB and OLDI. The SiP itself does not require more than 4 layers.
- **[?] Footprint discrepancies:**
  - The datasheet says the nominal ball is 0.30 mm with a 0.25 mm IPC nominal land, but Octavo footprints use the 0.20 mm minimum.
  - The Layout Guide says the ball is 0.25 mm.
  - Confirm against the mechanical drawing, which is an image in the datasheet and not text-extracted.
- **[C] Assembly:** MSL 4. Floor life 72 h at ≤30 °C / 60 % RH. Bake 34 h at 125 °C. Lead-free reflow with 245 °C peak (datasheet Section 8).

### 1.11 Errata
- **[C]** No Octavo-specific errata document was found (product page, forums, search).
- **[C]** The AM62x silicon errata apply (TI SPRZ487, https://www.ti.com/lit/pdf/sprz487). The Schematic Checklist cites i2407, i2328 and i2329.
- **[?]** Which AM62x silicon revision (SR1.0 or SR1.1) is inside current OSD6254 lots is not stated.

---

## 2. OSD62-PM-BRK reference design and other Octavo boards

- **[C] Board:**
  - 101.6 x 30.48 mm, **4 layers**, single-sided SMT (only the LVDS connector is elsewhere). Fitted with OSD6254-1G-IPM and a TPS6521903 PMIC.
  - Interfaces:
    - 2 x USB-C: a UFP for power and USB device, and a DFP for host.
    - µSD with UHS-I support.
    - 15-pin Raspberry-Pi-style CSI FPC.
    - 40-pin LVDS FPC for the TI SK-LCD1 panel.
    - Tag-Connect JTAG.
    - UART0 header.
    - 2 x 2x40 100-mil headers with 2 MikroE Click sites.
  - Other parts: 2 x ADC121C, a 4 KB EEPROM (AT24C32 at 0x50), and 25 MHz and 32 kHz oscillators.
  - Controls: power button, 4 LEDs.
  - **No Ethernet PHY and no eMMC on the board.** The Debian image uses RNDIS over USB.
  - Sources:
    - Product page: https://octavosystems.com/octavo_products/osd62-pm-brk/
    - Getting Started guide: https://octavosystems.com/app_notes/osd62-pm-brk-getting-started-guide/
    - BRK device tree
  - **[C]** Price: $115.00. Digi-Key had 40 in stock on its product-highlight page (https://www.digikey.com/en/product-highlight/o/octavo-systems/osd62x-system-in-package).
- **[C] Design files:**
  - Schematic PDF, rev 1D: https://octavosystems.com/docs/osd62-pm-brk-schematics-pdf/
  - Design files, **Eagle format, ZIP**, rev 1D: https://octavosystems.com/wp-content/uploads/2025/08/OSD62-PM-BRK-3.zip. The files page (https://octavosystems.com/files/osd62-pm-brk-design-files-eagle/) links an older .../2025/07/OSD62-PM-BRK.zip.
  - Both are marked "Must Be Logged In" (a free Octavo account).
  - Header pinout spreadsheet: https://octavosystems.com/files/osd62-pm-brk-header-configuration/
  - **No Altium or KiCad native files are offered.**
- **[I]** Altium Designer can import Eagle .sch/.brd through its Import Wizard, so the BRK can serve as a starting point.
- **[?]** I did not open the ZIP (it needs a login), so its contents (gerbers, BOM spreadsheet, stackup drawing) are unverified. CNX and Mouser say the BOM and layout are included.
- **[C] BOM highlights** (from the app notes):
  - TPS6521903 PMIC.
  - TLV62595 buck (5 V to 3.3 V).
  - TPS22965 and TPS22918 load switches.
  - TLV75518 VPP LDO.
  - ADC121C x2.
  - AT24C32 EEPROM.
  - 25 MHz and 32.768 kHz oscillators.
  - Exact BOM line items not verified.
- **[C] Other Octavo boards:**
  - The Octavo product menu lists RED and BRK boards for **OSD32MP1** (OSD32MP1-RED, OSD32MP1-BRK), **OSD3358-SM-RED**, and **OSDZU3-REF**.
  - **No OSD62 "RED" or other OSD62x reference board exists.** The OSD62-PM-BRK is the only OSD62 board (Octavo site navigation; OSD62 family page https://octavosystems.com/osd62-family/).
  - The larger **OSD62x** (21 x 21 mm, 437-ball, 1.0 mm pitch) integrates the TPS65219 PMIC, EEPROM and oscillators, and runs from a single 3.3 V input. TI calls it OSD62X-MI and the PM part OSD62X-SO. Its product page still shows "Beta sign-up/Request sample", with no part number or board (https://octavosystems.com/octavo_products/osd62x/, https://www.ti.com/tool/OCTVO-3P-OSD62X).

---

## 3. Availability, pricing, lifecycle and ECAD (checked 2026-10-17)

- **[C] Digi-Key** (https://www.digikey.com/en/products/detail/octavo-systems-llc/osd6254-1g-ipm/26728725): 1676-OSD6254-1G-IPM-ND, **Active**, **182 in stock**, 18-week manufacturer lead time, tray. **Price: $45.48 (qty 1), $44.062 (qty 10).**
  - Older 2025 Digi-Key prices were about $29 (qty 1), $27.54 (qty 10) and $24.68 (qty 100) (CNX Aug 2025; FindChips cache).
  - **[I]** The price has risen by about 55 %, plausibly with DDR4 cost inflation. Budget at about $45 or more per unit at low volume.
- **[?] Mouser** (https://www.mouser.com/ProductDetail/Octavo-Systems/OSD6254-1G-IPM?qs=sqEgtWRSLJ2VduLeVFZOhQ%3D%3D) blocked automated access, so current stock and price are not confirmed. In Aug 2025 Mouser listed $35.58 at qty 1 (CNX, https://www.cnx-software.com/2025/08/28/octavo-osd62x-pm-sip-combines-texas-instruments-am62x-soc-with-up-to-2gb-ddr4-in-a-tiny-14x9mm-bga-package/).
- **[C] Other sources:**
  - Avnet: 0 stock, $44.06–$50.36 (FindChips, https://www.findchips.com/search/OSD6254-1G-IPM).
  - Octavo direct: $22.50 list on the product page, quantity not stated.
  - **[I]** The Octavo direct price is presumably a volume price.
- **[C] OSD6254-1G-BPM:** no distributor listing found; not in the Rev 2.0 datasheet. Treat as not orderable.
- **[C] Lifecycle:**
  - Production and "Active". Octavo describes the part as "in full production".
  - Octavo's longevity statement promises "commercially reasonable steps" for 10+ year lifecycles and die banking, with no fixed EOL date (https://octavosystems.com/statement-of-product-longevity/).
- **[C] ECAD:**
  - Octavo offers an **Altium library v12.0 (Jul 1, 2025)** (form-gated: https://e3vd4.share-na2.hsforms.com/28BnH2PazQa-5VpYDE2P3Rw), an Eagle library v16.0, and STEP 3D models v1.0 (Jul 31, 2025).
  - The datasheet points to the product page's "#Symbols" section for the OSD62x-PM footprint and symbol.
  - **[?]** Not verified because of the form gate: that v12.0 actually contains the OSD62x-PM, and its land size (expect 0.20 mm).
- **[C]** No SnapEDA or SnapMagic model was found. The Digi-Key page shows no Ultra Librarian or SnapEDA links. Ultra Librarian needs a login and was not checked.
- **[C]** A community Flux.ai part exists (https://www.flux.ai/silicon-yard/osd6254-1g-ipm). Its own thread says the 500 pins have not been audited, so do not use it. It also wrongly describes the part as containing "power management circuitry".
- **[?]** The Altium 365 Manufacturer Part Search could not be checked.

---

## 4. Linux and BSP support

- **[C] Octavo TI-SDK BSP** (https://github.com/octavosystems/osd62-pm-brk-tisdk, branch v10, BSD-2-Clause):
  - Patches against **TI Processor SDK 10.01.10.04**: ti-u-boot 2024.04, ti-linux-kernel 6.6.58, TF-A 2.11.
  - Board files: `k3-am625-osd625-brk.dts`, overlays for the Microtips panel and OV5640 camera, U-Boot `board/octavo/osd62x`, defconfigs `am62x_osd62x_r5_defconfig` and `am62x_osd62x_a53_defconfig`.
  - Shared `k3-am62x-osd62x-pm-common.dtsi` (memory node: 1 GB at 0x80000000).
  - Prebuilt images are form-gated: TI SDK 10.01 and Debian 12.7 (Sep 2025).
- **[C] Yocto:** meta-octavo-osd62 (https://github.com/octavosystems/meta-octavo-osd62), **scarthgap**, branch scarthgap-v10.1.10, MACHINE `osd62-pm-brk`, built on meta-ti, meta-arago and meta-tisdk 10.01.10, MIT licence.
- **[C] Debian:** a BeagleBoard.org-based image and Robert C. Nelson's guide on the Digi-Key forum (Oct 2025): https://forum.digikey.com/t/debian-getting-started-with-the-osd62-pm-brk/61216.
  - U-Boot: `RobertCNelson/ti-u-boot-octavo`, tag `v2024.04-ti-10.01.10-am625-osd625-brk`.
  - Kernel: ti-linux-kernel-dev 6.6.y.
  - Root filesystem: Debian 13.1.
- **[C] DDR parameters:** https://github.com/octavosystems/osd62-pm-ddr provides `k3-osd62x-ddr-config-800MHz.dtsi`, included from the R5 SPL device tree, and `board_ddrReginit.h`.
  - The device is DDR4 x16, 800 MHz (1600 MT/s) maximum (Power app note).
  - **[?]** The BRK U-Boot patch includes **k3-osd62x-ddr-config-850MHz.dtsi** in its R5 device tree, while the repo README and Octavo docs say 800 MHz. Confirm which is validated.
- **[C] Upstream:**
  - I found no mainline Linux or U-Boot board support for OSD62x.
  - Octavo's GitHub was last updated Oct–Nov 2025.
  - TI's current AM62x SDK is 12.01.00.05 (July 31, 2026, https://www.ti.com/tool/download/PROCESSOR-SDK-LINUX-AM62X).
- **[I]** A custom SBC will need its own device tree. Start from `k3-am625-osd625-brk.dts` plus `k3-am62x-osd62x-pm-common.dtsi` and the Octavo DDR dtsi, and port forward to SDK 11 or 12 yourself. The SoC side behaves "identically to an AM62x standalone device" (datasheet Section 6.1), so TI SK-AM62B-P1 support is a good second reference.
- **[I]** The Octavo U-Boot board file is not TI's EEPROM board-detect flow. An ID EEPROM is optional, but cheap to keep.
- **[C] Debug consoles:**
  - MAIN_UART0: U-Boot and Linux (ttyS2, 115200).
  - MAIN_UART1: TIFS.
  - WKUP_UART0: Device Manager firmware.
  - MCU_UART0: MCU+ SDK.
  - Sources: Boot Chain and Schematic Checklist app notes.

---

## 5. Open items to confirm before committing the design
1. VDD_CORE strategy for 1.4 GHz: TPS6521904 or 07 versus 03 with a software raise (Section 1.6).
2. DDR4 clock: 800 MHz or 850 MHz parameters (Section 4).
3. The authoritative footprint (land size, ball diameter) from the Octavo Altium v12 library; check it against the mechanical drawing.
4. VDDA_MCU/PLL and VDDR_CORE capacitor counts in Table 4-3, which do not add up (Section 1.5).
5. Current Mouser stock and price, and quantity-100 pricing (contact Octavo sales@octavosystems.com).
6. Contents of the BRK Eagle ZIP (gerbers, BOM, stackup); needs a free Octavo login.
