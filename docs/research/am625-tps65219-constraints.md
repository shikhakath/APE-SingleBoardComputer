# OSD6254 (AM6254 SiP) + TPS65219 SBC: Design-Constraint Notes

Scope: constraints extracted from vendor datasheets. Nothing here is a design. Use these notes as input to the Altium schematic/PCB work.

Sources (all in `C:\Users\Jay Li\Documents\apeproject\datasheets\`):

| Ref | Document | Rev | Notes |
|---|---|---|---|
| **[DS]** | `am625.pdf`: AM62x Sitara Processors datasheet, SPRSP58C | Rev C, Oct 2025 | Printed page numbers = PDF page numbers |
| **[PMIC]** | `tps65219.pdf`: TPS65219 PMIC datasheet, SLVSGA0D | Rev D, Apr 2026 | Printed = PDF page numbers |
| **[TRM]** | `spruiv7c.pdf`: AM62x TRM, SPRUIV7C, Ch. 5 "Initialization" only (pp. 432-491) | Rev C, Nov 2025 | Printed = PDF page numbers |
| **[OSD]** | `OSD62x-PM-Overview-2-Page-V1.pdf`: Octavo 2-page product brief | V01, 3/22/2024 | Not a full datasheet |

> **Critical caveat:** ball numbers, the package and any rails that are merged or decoupled inside the SiP come from the Octavo OSD62x-PM datasheet, which is **not in the folder**. Every AM625 ball number below (ALW/AMC) is for TI's bare-die packages, **not** the OSD6254 BGA. Section 0 lists the items to confirm with Octavo.

---

## 0. OSD6254 SiP facts and open items

From [OSD] p.1-2:
- The SiP integrates the TI AM62 + DDR4 + passives in a **9 mm x 14 mm, 500-ball, 0.5 mm-pitch BGA**. A 0.5 mm pitch BGA with 500 balls will very likely need HDI (via-in-pad or microvias). Check Octavo's layout guide.
- Part numbers:
  - OSD6254-1G-BPM: AM6254, 4x A53 @ **1400 MHz**, M4F, 3D GPU, PRU-SS, 1 GB DDR4, **0 to 85 °C case**.
  - OSD6254-1G-IPM: same, **-40 to 85 °C case**.
  - -ES: engineering samples.
- Octavo's OSD62PM-BRK reference board includes a TPS65219 and exposes USB-C (USB0), a microSD on MMC1, CSI, a USB2 host on USB1 and JTAG. The brief does not say which TPS65219 OPN it uses. **Check that schematic first**, because it is the closest reference design.

Open items to resolve from the Octavo datasheet or the BRK schematic:
1. **Ball map.** Which AM62x supply balls are tied together inside the SiP? Which DDR4 rails come out to balls (VDD/VDDQ 1.2 V, **DDR4 VPP 2.5 V**, VREFCA, ZQ)? Is VDDS_DDR merged with the DDR4 VDD/VDDQ?
2. **Integrated decoupling capacitance per rail.** It counts toward the TPS65219 maximum total output capacitance limits (§B.3). This matters most for the LDO rails, which are capped at 15-50 µF total.
3. Is the 25 MHz crystal or the 32.768 kHz crystal inside the SiP? It is probably external, because the brief only lists "passives".
4. The exact AM6254 orderable code inside the SiP: speed grade (must be **T** for 1.4 GHz), features code (C = PRUSS enabled), and the security option.
5. SiP thermal resistances (θJC/θJB). The values in [DS] §6.10 are for TI's ALW/AMC packages only.

---

# A. AM625 / AM62x datasheet [DS]

## A.1 Device variant, package, speed grades

**Feature matrix: Table 4-1, p.7-8**

AM6254 provides:
- **Quad Cortex-A53**, 512 KB L2 with ECC.
- **1x Cortex-M4F** (MCU domain, 256 KB SRAM).
- **WKUP_R5F** Device/Power Manager.
- **3D GPU** (OpenGL ES 3.1, Vulkan 1.2; AM6254/52/51 only).
- DSS with 1x DPI and 1x OLDI.
- 3x MCAN, 6x I2C, 3x McASP, 5x McSPI, 9x UART.
- 1x 8-bit eMMC plus 2x 4-bit SD/SDIO.
- OSPI0/QSPI0.
- CPSW3G Ethernet switch.
- 1x CSI-RX (4-lane D-PHY).
- 2x USB 2.0.
- 12 timers.
- Up to 168 GPIO.

**PRUSS (2x PRU @ up to 333 MHz)** is present only on orderables with **Features code "C"** (Table 4-1 note 3, p.8; naming convention, p.247).

**DDRSS** (p.1): 16-bit DDR4 or LPDDR4 with inline ECC, up to **1600 MT/s**, up to 8 GB (DDR4).

**Speed grades: Table 6-1, p.93**

| Grade | VDD_CORE | A53 max | GPU | PRU | M4F/DM R5F | DDR4 |
|---|---|---|---|---|---|---|
| G | 0.75/0.85 V | 300 MHz | 500 | 250 | 400 | 1600 MT/s |
| K | 0.75/0.85 V | 800 MHz | 500 | 250 | 400 | 1600 |
| S | 0.75/0.85 V | 1000 MHz | 500 | 333 | 400 | 1600 |
| **T** | 0.75/0.85 V | **1250 MHz @ 0.75 V; 1400 MHz only @ 0.85 V** | 500 | 333 | 400 | 1600 |

**Key design constraint: running the A53 at 1.4 GHz requires speed grade T *and* VDD_CORE = 0.85 V.** At 0.75 V the limit is 1.25 GHz. This choice drives the TPS65219 OPN selection (§B.2).

**Naming (p.247):** AM6254 **r Z f Y y t** ALW.
- r = A (SR1.0) or B (SR1.1).
- Z = speed grade (G/K/S/T).
- f = G (base) or C (with PRUSS).
- Y = G (non-safety) or F (functional safety).
- y = G (non-secure) or other (secure).
- t = A (-40..105 °C TJ), H (0..95 °C TJ) or I (-40..125 °C TJ).

**TI packages:** ALW is a 13x13 mm, 425-ball, 0.5 mm FCCSP. AMC is a 17.2x17.2 mm, 441-ball, 0.8 mm FCBGA (p.3). Neither applies directly to the SiP.

## A.2 Supplies

### A.2.1 Recommended operating conditions: Table 6.5, p.91-92

The voltage at the ball must stay within MIN/MAX at all times (note 1).

| Rail | Function | Nom | Min-Max |
|---|---|---|---|
| **VDD_CORE**, VDDA_CORE_CSIRX0, VDDA_CORE_USB, (VDDA_DDR_PLL0, AMC only; tied to VDD_CORE in ALW) | Core | **0.75 V** or **0.85 V** | 0.715-0.79 / 0.81-0.895 |
| VDD_CANUART | CANUART core | 0.75/0.85 | same as core |
| **VDDR_CORE** | RAM (SRAM) supply | **0.85 V always** | 0.81-0.895 |
| **VDDS_DDR**, VDDS_DDR_C | DDR PHY IO | **1.2 V (DDR4)** / 1.1 V (LPDDR4) | 1.14-1.26 / 1.06-1.17 |
| VDDS_OSC0 | MCU_OSC0 supply | 1.8 | 1.71-1.89 |
| VDDA_MCU | RCOSC/POR/POK/MCU_PLL0 analog | 1.8 | 1.71-1.89 |
| VDDA_PLL0/1/2 | PLL analog | 1.8 | 1.71-1.89 |
| VDDA_1P8_CSIRX0, VDDA_1P8_OLDI0, VDDA_1P8_USB | PHY 1.8 V analog | 1.8 | 1.71-1.89 |
| VDDA_TEMP0/1 | Temperature sensor analog | 1.8 | 1.71-1.89 |
| VMON_1P8_SOC | 1.8 V monitor input | 1.8 | 1.71-1.89 |
| **VDDA_3P3_USB** | USB 3.3 V analog | 3.3 | 3.135-3.465 |
| VMON_3P3_SOC | 3.3 V monitor input | 3.3 | 3.135-3.465 |
| VMON_VSYS | VSYS monitor (divider) | 0.45 V threshold | 0-1 V |
| USB0_VBUS / USB1_VBUS | Level-shifted VBUS | - | 0-3.465 V (external divider required) |
| VDDSHV_MCU, VDDSHV_CANUART, **VDDSHV0..VDDSHV6** | Dual-voltage IO | 1.8 or 3.3 | 1.71-1.89 / 3.135-3.465 |
| **VPP** | **eFuse programming supply (NOT DDR4 VPP)** | see §A.2.4 | **Leave floating or grounded in normal operation** |
| TJ | Junction temperature | - | Commercial 0..95, Ext-Industrial -40..105, Auto -40..125 °C |

**Rail-grouping rules (ROC notes, p.92):**
- VDD_CORE, VDDA_CORE_CSIRX0, VDDA_CORE_USB and VDDA_DDR_PLL0 **must come from the same source**. Keep VDD_CORE and VDDA_CORE_USB within ±1% of each other (layout: avoid IR-drop differences).
- VDD_CANUART must be on the same source as VDD_CORE, unless Partial-IO is used (in that case it must be always-on). The same applies to VDDSHV_CANUART: always-on for Partial-IO, otherwise any valid IO source.
- VDDS_DDR and VDDS_DDR_C must be on the same source.

**NAMING PITFALL.** The AM62x pin called **VPP** is the **1.8 V eFuse programming** pin. It is *not* the DDR4 2.5 V VPP. Use distinct Altium net names, for example `VPP_EFUSE` and `DDR4_VPP_2V5`.

### A.2.2 Absolute maximum ratings: §6.1, p.88-89

| Pin or group | Abs max |
|---|---|
| Core and VDDR rails | 1.05 V |
| VDDS_DDR | 1.57 V |
| 1.8 V analog rails, VPP | 1.98 V |
| VDDSHVx, VDDA_3P3_USB | 3.63 V |
| USBx_VBUS pin | 3.6 V |
| MCU_PORz (fail-safe) | 3.63 V |
| VMON_1P8_SOC | 1.98 V |
| VMON_3P3_SOC | 3.63 V |
| VMON_VSYS | 1.98 V |
| Non-fail-safe IO | IO supply + 0.3 V. **Never back-drive an unpowered IO domain** (note 6) |

Fail-safe pins are only: MCU_I2C0, WKUP_I2C0, EXTINTn, VMON_x and MCU_PORz (p.89).

### A.2.3 IO-domain map (from Pin Attributes Table 5-1, POWER column, pp.12-53)

These IO-group assignments come from the die, so they carry over to the SiP.

| IO supply | Key interfaces / pins on it |
|---|---|
| **VDDSHV0** | UART0 (boot UART), I2C0/I2C1, MCAN0, SPI0, McASP0, **MMC1_SDCD/SDWP**, USB0/1_DRVVBUS, **RESET_REQz, PORz_OUT, RESETSTATz**, EXTINTn, EXT_REFCLK1/CLKOUT0 (ball A18) |
| **VDDSHV1** | **OSPI0** (CLK, D0-7, CSn, DQS) |
| **VDDSHV2** | **RGMII1, RGMII2, MDIO0** |
| **VDDSHV3** | **GPMC0 / BOOTMODE[15:0]** (GPMC0_AD0-15), **VOUT0 (DPI)** |
| **VDDSHV4** | **MMC0 (eMMC)** |
| **VDDSHV5** | **MMC1 (SD card)** CLK/CMD/DAT |
| **VDDSHV6** | **MMC2 (SDIO)** CLK/CMD/DAT |
| VDDSHV_MCU | MCU_I2C0, **WKUP_I2C0**, MCU_SPI0, MCU_RESETz, MCU_RESETSTATz, JTAG (TCK...), EMU0/1, WKUP_CLKOUT0 |
| VDDSHV_CANUART | MCU_UART0, WKUP_UART0, MCU_MCAN0/1, **PMIC_LPM_EN0** |
| VDDS_OSC0 (1.8 V only) | **MCU_PORz**, **MCU_ERRORn**, MCU_OSC0_XI/XO, WKUP_LFOSC0_XI/XO |

**IO-voltage implications:**
- **HS200 eMMC needs 1.8 V IO**, so VDDSHV4 = 1.8 V (Table 6-81, p.180).
- **UHS-I SD needs VDDSHV5 to switch 3.3 V to 1.8 V.** There is **no internal SD LDO** on AM62x. The switching must be done externally, for example with TPS65219 LDO1 plus VSEL_SD.
- VDDSHV4/5/6 "support power-up, power-down, or dynamic voltage change without any dependency on other power rails", which is needed for UHS-I (Table 6-5 note 7, p.106).
- **If MMC2 drives a UHS-I SD card** (VDDSHV6 switching), its SDCD/SDWP must be muxed to VDDSHV0 pins (Table 5-46 note 2, p.72).
- MMC2 needs CTRLMMR_PADCONFIG71 set to RXACTIVE=1, TX_DIS=0 (note 1, p.72).
- RGMII IO level (VDDSHV2) must match the PHY IO voltage.
- OSPI IO level (VDDSHV1) must match the flash, typically 1.8 V for octal.
- BOOTMODE pull-ups go to **VDDSHV3** ([TRM] p.442).

**CAP_VDDSx pins** (Table 5-49 note, p.75): each needs a **0.8-1.5 µF (after derating), ≥6.3 V** cap to VSS if the matching VDDSHVx is **ever** at 3.3 V. If the rail is 1.8 V only, the pin may get the same cap, be left NC, or be tied to that 1.8 V source.

### A.2.4 VPP / eFuse (§6.9, p.99)

- In normal operation VPP is **NC (floating) or 0 V**. Apply it only while programming: 1.71-1.89 V, up to 400 mA, slew ≤ 6E4 V/s, TJ 0-85 °C.
- Ramp it only after the normal power-up sequence completes, and remove it after programming.
- For an SBC, either leave it unconnected or add an optional gated 1.8 V switch (DNP).

### A.2.5 Power-up sequence: §6.12.2.2.1, Table 6-5 / Fig 6-5, p.105-107

Slew-rate limit for **every** supply: **< 18 mV/µs** (§6.12.2.1, p.103). For example, a 1.8 V rail must take more than 100 µs to ramp.

| Waveform | Rails | Order |
|---|---|---|
| A | VSYS, VMON_VSYS | First |
| B | All **3.3 V** IO (VDDSHV_x at 3.3 V), VDDA_3P3_USB, VMON_3P3_SOC | After VSYS |
| C | All **1.8 V** IO (VDDSHV_x at 1.8 V), VDDA_MCU, VDDS_OSC0, VDDA_PLL0/1/2, VDDA_1P8_CSIRX0/OLDI0/USB, VDDA_TEMP0/1, VMON_1P8_SOC | After the 3.3 V group |
| D | VDDSHV4, VDDSHV5, VDDSHV6 | Any time after VSYS (no dependency) |
| E | VDDS_DDR, VDDS_DDR_C | After the 1.8 V group. The window overlaps the core ramps (Fig 6-5) |
| F | VDD_CANUART (only if always-on for Partial-IO) | Before VDD_CORE |
| G | VDD_CORE group **when 0.75 V** | Before VDDR_CORE |
| H | VDDR_CORE (and the VDD_CORE group **when 0.85 V**, **same source, ramps together**) | Last supply |
| I | VPP | Hi-Z / grounded throughout |
| J | MCU_PORz | Released after all supplies are valid. **Hold low ≥ 9.5 ms after supplies are valid when using the crystal** (Table 6-8 RST1, p.111). Hold ≥ 1.2 µs with an external LVCMOS clock that is already stable (RST2). Min low pulse 1.2 µs (RST3) |
| K | MCU_OSC0 | Starts once supplies are up |

**Inter-rail limits:**
- VDDR_CORE ≤ VDD_CORE + 0.18 V at all times (note 12).
- VDD_CORE ≤ VDD_CANUART + 0.18 V if VDD_CANUART is always-on (note 9).

**Re-power rule:** if **any** rail drops below its min, **all** rails must be turned off and decay below **300 mV** before a new power-up (p.105). The only exception is the Partial-IO CANUART rails.

### A.2.6 Power-down sequence: Table 6-6 / Fig 6-6, p.108-109

1. MCU_PORz is asserted (low) **first**.
2. Then VDDR_CORE and the 0.85 V core group ramp down, followed by the 0.75 V core group, then VDD_CANUART.
3. The IO, analog and DDR rails ramp down in parallel and end last.

The 0.18 V inter-rail rules still apply.

### A.2.7 Current / power data for sizing

- The datasheet gives **no rail currents**. §6.7 (p.93) points to the "AM62x Power Estimation Tool" app note. Use it to size VDD_CORE (Buck1, 3.5 A max) and the IO rails.
- §8.1.1.1 (p.236) states that the TPS65219 factory configs "support power rail load steps, supply voltage accuracies and maximum load currents with margins" and support DDR4 and LPDDR4.
- The only explicit number is VPP: 400 mA max during eFuse programming.
- PDN design is per "Sitara Processor Power Distribution Networks: Implementation and Analysis" (§8.1.1.2). TI only supports designs that follow it.

### A.2.8 Voltage monitors (§8.2.4, p.241-242; Table 5-74, p.86)

**VMON_VSYS:**
- Comparator with a 0.45 V ±3% threshold.
- Input leakage is 10 nA to 2.5 µA.
- Use 1% resistors.
- Worked example for 5 V VSYS: R_top = 40.2 kΩ, R_bot = 4.81 kΩ gives a trip at 4.013-4.517 V. Add a filter cap across R_bot.
- If unused, tie it **to VSS**.

**VMON_1P8_SOC** must connect directly to the 1.8 V rail. It must stay connected to a 1.8 V rail even when unused.

**VMON_3P3_SOC** connects directly to the 3.3 V rail, or to VSS if unused.

## A.3 Boot (detail in §C)

**BOOTMODE[15:0] balls** (Table 5-53, p.78-79):
- They share balls with GPMC0_AD0-15 (VDDSHV3).
- They are latched at the rising edge of PORz_OUT: setup 3x the 25 MHz period (~120 ns), hold 0 (Table 6-15, p.115).
- Each one must have an external pull-up (to VDDSHV3) or pull-down. **None may float**, including the reserved bits (Table 5-74, p.84).

**Boot devices supported** (p.3): UART, I2C EEPROM, OSPI/QSPI/xSPI/SPI, GPMC NOR/NAND, Serial NAND, SD, eMMC, USB host (MSC), USB device (DFU), and Ethernet.

## A.4 Clocking

### A.4.1 MCU_OSC0, 25 MHz (§6.12.4.1.1, Tables 6-22/6-23, p.120-122)

**Crystal requirements:**
- Fundamental mode, parallel resonant, **25 MHz**.
- Tolerance plus stability: **±50 ppm if RGMII/RMII uses a derived clock** (±100 ppm otherwise).

**Load capacitance:**
- C_L (crystal spec) must be 6-12 pF.
- C_L1 + C_PCBXI and C_L2 + C_PCBXO must each be 12-24 pF.
- C_XI ≤ 0.812 pF and C_XO ≤ 0.83 pF (ALW).
- Formula: C_L = [(C_L1+C_PCBXI+C_XI)(C_L2+C_PCBXO+C_XO)] / [sum].
- Worked example: C_L = 10 pF gives C_L1 ≈ 16.6 pF and C_L2 ≈ 15.8 pF.

**ESR versus shunt capacitance:**

| ESR | Max C_shunt |
|---|---|
| 30 Ω | 7 pF |
| 40 Ω | 5 pF |
| 50 Ω | 5 pF |

C_shunt ≥ C0 + C_PCBXIXO + C_XIXO.

**Start-up time:** typical 4 ms.

**External oscillator alternative** (Table 6-24, p.124):
- 1.8 V LVCMOS into XI, with XO grounded.
- 45-55% duty cycle, rise/fall ≤ 4 ns.
- Jitter: ≤ 20 ps RMS period, ≤ 300 ps peak-to-peak period, ≤ 10 ps RMS phase (100 Hz-1 MHz).
- Point-to-point with a series termination.
- No DC level is allowed on XI while the oscillator is powered (p.123).

**Layout** (§8.3.1, p.244):
- Put the parts on the outer layer, close to the balls.
- Use a solid GND plane on the adjacent layer.
- Run a ground guard ring and a **ground guard between XI and XO**. This is critical to minimize mutual capacitance.

### A.4.2 WKUP_LFOSC0, 32.768 kHz (optional; §6.12.4.1.3-5, Tables 6-25..6-27, p.125-127)

- Fundamental mode, parallel resonant, ±100 ppm.
- C_f1 = C_f2 in the 12-24 pF range.
- Shunt capacitance limits by ESR:

| ESR | Max C_shunt |
|---|---|
| 40 kΩ | 4 pF |
| 60 kΩ | 3 pF |
| 80 kΩ | 2 pF |
| 100 kΩ | 1 pF |

- Start-up time up to 96.5 ms.
- Recommended footprints: an optional R_bias across the crystal and R_d (0 Ω) in series on XO, for pre-production tuning.
- Software trim: CTRLMMR_WKUP_LFXOSC_TRIM i_mult = 3'b001 for C_L 6-9.5 pF, or 3'b010 (default) for 8.5-12 pF.
- **If unused: XI to GND, XO NC** (Fig 6-25).
- Can also take a 1.8 V LVCMOS clock.

### A.4.3 Clock outputs (§6.12.4.2, p.128)

- **CLKOUT0** (ball A18 on ALW, VDDSHV0) is MAIN_PLL2_HSDIV1 /5 or /10, which gives **25 MHz or 50 MHz**. It is "provided as an optional source to the external PHY".
  - In RMII mode, 50 MHz CLKOUT0 must also be routed back to RMII[x]_REF_CLK.
  - The ROM can enable 25 MHz (RGMII) or 50 MHz (RMII) on CLKOUT0 during Ethernet boot ([TRM] Tables 5-23/5-24).
- WKUP_CLKOUT0 is a general output.
- SYSCLKOUT0, MCU_SYSCLKOUT0 and OBSCLK are for test and debug only.
- AUDIO_EXT_REFCLK0/1 are McASP reference in or out.
- All clocks and strobes must have monotonic edges (p.129).

## A.5 Reset and PMIC interface

| Signal | Domain | Function / requirement (refs) |
|---|---|---|
| **MCU_PORz** | VDDS_OSC0 (1.8 V input, fail-safe to 3.63 V) | Cold reset of MCU+MAIN. Hold low ≥ 9.5 ms after supplies are valid (crystal). Input slew ≥ 0.0018 V/ns at 1.8 V (Table 6-7/6-8, p.111). VIH = 0.7 x VDDS_OSC0 (≈1.26 V), hysteresis 200 mV (§6.8.2, p.95). **Driven from TPS65219 nRSTOUT** (open-drain, needs a pull-up, max 3.4 V on the PMIC side) |
| MCU_RESETz | VDDSHV_MCU | MCU-domain warm reset input; ≥ 1.2 µs pulse (Table 6-10, p.113). Needs an external pull-up if a trace is attached (Table 5-74) |
| **RESET_REQz** | VDDSHV0 | MAIN-domain warm reset request input; ≥ 1.2 µs (Table 6-12, p.114). External pull-up if routed. This is the AM62x "WARMRSTn" |
| PORz_OUT / RESETSTATz / MCU_RESETSTATz | VDDSHV0 / VDDSHV_MCU | Reset-status outputs. Useful for resetting peripherals such as the eMMC RST_n, flash RESET# and PHY reset |
| **PMIC_LPM_EN0** | VDDSHV_CANUART | "Dual-function PMIC control output, Low Power Mode (active low) or PMIC Enable (active high)" (Table 5-58, p.80). Candidate connection: TPS65219 MODE/STBY (as STBY) or EN |
| MCU_ERRORn | VDDS_OSC0 | ESM error output. Needs an external pull-**down** if routed (Table 5-74, p.84) |
| EXTINTn | VDDSHV0, fail-safe open-drain input | Suitable for the PMIC nINT |
| WKUP_I2C0 / MCU_I2C0 | VDDSHV_MCU, fail-safe | Always-on-domain I2C. Natural choice for the PMIC I2C (TPS65219 address 0x30) |
| TRSTn / EMU0 / EMU1 | | Pull-**down** (TRSTn) or pull-up (TCK/TDI/TMS) if traced (Table 5-74, p.84). EMU[1:0] are sampled at MCU_PORz rising (Table 6-14) |

## A.6 High-speed / peripheral interface constraints

### USB 2.0 (USB0, USB1)

Sources: Tables 5-72/73 p.83; §8.2.3 p.241; Table 5-74 p.85-86.

- Both ports can be host, peripheral or DRD. Host supports HS/FS/LS; device supports HS/FS. Integrated VBUS detect, xHCI (p.235).
- **USBx_VBUS needs an external divider and clamp** (Fig 8-4):
  - Path: VBUS, then 3.48 kΩ 1%, then a node with a **6.8 V zener (BZX84C6V8 or equivalent, leakage < 100 nA at 5 V)** to GND, then 16.5 kΩ 1% to the USBx_VBUS pin, with **10 kΩ 1% from the pin to GND**.
  - Pin max 3.465 V. With this circuit, USB0_VBUS is fail-safe.
- **USBx_RCALIB: 499 Ω ±1% to VSS** (≤ 7.2 mW, no external voltage).
- USBx_DRVVBUS (VDDSHV0) is an active-high VBUS-switch enable for host mode.
- VDDA_CORE_USB, VDDA_1P8_USB and VDDA_3P3_USB must be powered if either port is used. If both ports are unused, tie them to VSS.
- For an unused port, leave DM/DP/VBUS NC.
- **USB boot (DFU/MSC) is on USB0 only** ([TRM] Table 5-1).
- Routing: TI "High Speed Interface Layout Guidelines" (§8.2.5, p.243). No numeric limits are given in the datasheet.

### MMC0: eMMC 8-bit, HS200 @ 200 MHz, 1.8 V

Sources: §6.12.5.16.1, Tables 6-81/6-82, p.180-181; Table 6-87/88, p.184.

- JEDEC eMMC 5.1 modes: Legacy SDR, HS SDR, **HS200**. HS200 needs the tuning algorithm.
- C_L ≤ 10 pF in HS200.
- **Trace propagation delay: 126-756 ps** for Legacy, HS SDR and HS200.
- **Trace mismatch across all MMC0 traces: ≤ 8 ps** for HS SDR, HS200 and SDR104. It is ≤ 20 ps for DDR50 and ≤ 100 ps for other modes.
- HS200 receive needs a 2.0 ns data-valid window.
- eMMC boot works only on MMC0 ([TRM] p.459).
- For warm-reset eMMC boot, connect the reset line to eMMC RST_n and set ext_csd[162] RST_n_ENABLE = 0x1 ([TRM] §5.4.4.2, p.460).

### MMC1: SD card, 4-bit, up to UHS-I SDR104

Sources: §6.12.5.16.2, Tables 6-100/101, p.192-193.

- Supported modes: DS, HS, SDR12/25/50, DDR50, SDR104 at 200 MHz. The UHS modes need tuning.
- C_L ≤ 10 pF.
- **Trace delay 126-1386 ps** (DDR50: 239-1134 ps).
- **Mismatch: ≤ 8 ps for HS and SDR104; ≤ 20 ps for DDR50; ≤ 100 ps otherwise.**
- VDDSHV5 must be 3.3 V at start and 1.8 V after switching to UHS. There is no internal LDO, so use PMIC LDO1/LDO2 with VSEL_SD.
- SD boot works only on MMC1. **The ROM requires MMC1_SDCD = 0 (card present)** or the boot fails. DAT3 card detect is not supported ([TRM] p.457-458).
- MMC1_SDCD and SDWP sit on VDDSHV0 (they do not switch with VDDSHV5).
- The SD socket must be powered before SD boot ([TRM] p.439).

### MMC2: SDIO, for example Wi-Fi

- Same mode support and routing limits as MMC1.
- On VDDSHV6, normally 1.8 V for SDIO modules.
- See the PADCONFIG71 and SDCD/SDWP notes in §A.2.3.

### OSPI0 / QSPI

Sources: §6.12.5.18, Table 6-114, p.203; §8.2.2, p.238-240.

- Tap mode: 50 MHz SDR / 25 MHz DDR.
- PHY mode: higher speeds, with data training.

**Routing:**
- 50 Ω traces, with a 0 Ω series placeholder at OSPI0_CLK (and at LBCLKO).
- **CLK delay (A to B) ≤ 450 ps** (about 7 cm stripline or 8 cm microstrip).
- **D[7:0] and CSn delay = CLK delay ± 60 ps.**
- External board loopback: LBCLKO to DQS delay = 2 x (CLK delay ± 30 ps).
- DQS mode (octal flash with DQS): DQS delay = CLK delay ± 30 ps.

**Other:**
- C_L 3-10 pF.
- For flash larger than 128 Mb, use a part **with a RESET# pin**, driven from the SoC reset, because the ROM uses 3-byte addressing ([TRM] p.443-444).

### Ethernet CPSW3G: 2 external ports, RGMII or RMII

Sources: §6.12.5.1.3, Tables 6-35..6-39, p.133-135; MDIO p.130.

- **TX: TXC is always delayed internally** ("This internal delay is always enabled", Fig 6-31 note A).
- **RX: RGMII[x]_RXC must be delayed externally relative to data** (Fig 6-30 note A). In practice, the PHY must add the RX clock delay and must **not** add a TX delay.
- **Trace mismatch ≤ 50 ps** within the RX group (RXC/RD[3:0]/RX_CTL) and within the TX group (TXC/TD[3:0]/TX_CTL).
- C_L 2-20 pF.
- MDIO: trace delay ≤ 5 ns, mismatch ≤ 1 ns, C_L 10-470 pF, MDC ≥ 400 ns period.
- Both RGMII ports and MDIO are on VDDSHV2.
- Ethernet boot runs on RGMII1/RMII1 with MDIO0 ([TRM] Table 5-27/5-28). The PHY must be strapped for the right delay mode at reset, because the ROM does not configure the PHY ([TRM] p.462).
- Crystal tolerance must be ±50 ppm if the PHY clock is derived from the SoC (Table 6-22).

### CSI-2 RX (CSIRX0)

Sources: §6.12.5.3, p.137; Table 5-7, p.56; Table 5-74.

- MIPI CSI-2 v1.3 with D-PHY v1.2. 1, 2, 3 or 4 lanes, ≤ 1.5 Gbps per lane.
- **CSI0_RXRCALIB: 499 Ω ±1% to VSS.**
- Unused lanes: leave NC.
- If CSI is unused and boundary scan is not needed, VDDA_CORE_CSIRX0 and VDDA_1P8_CSIRX0 may be tied to VSS.
- Routing: TI High Speed Interface Layout Guidelines.

### OLDI0 (LVDS, 2 links x 4 data lanes + CLK)

Sources: Table 6-113, p.201-202.

- Clock period ≥ 6.06 ns (≤ 165 MHz pixel clock).
- **Pair-to-pair skew ≤ 50 ps.**
- 100 Ω differential termination at the far end. Slow or fast drive modes.
- VDDA_1P8_OLDI0 is needed.
- If OLDI is unused, leave the pins NC.

### DPI / VOUT0 (24-bit parallel RGB, VDDSHV3)

Sources: Tables 6-44..6-46, p.139-140.

- PCLK ≥ 6.06 ns period (≤ 165 MHz).
- **Mismatch across all traces ≤ 100 ps.**
- C_L 1.5-5 pF.
- Note that VOUT0 shares VDDSHV3 with GPMC/BOOTMODE, so the boot straps must coexist with the display data lines.

### DDR4

DDR4 routing is inside the SiP. The AM62x DDR board guidelines (§8.2.1) apply to Octavo, not to us. The board still supplies VDDS_DDR (1.2 V) and possibly DDR4 VPP (2.5 V); see §0.

### Pin-state hazards (p.87)

- Any IO whose RX buffer is enabled must never float between VILSS and VIHSS.
- Use external pulls on all routed inputs.
- Configure pinmux with TI SysConfig (p.7).

## A.7 Thermal

- TJ ranges: commercial 0-95 °C, extended industrial -40-105 °C, automotive -40-125 °C (§6.5).
- Octavo rates the SiP at 0-85 °C case (B) or -40-85 °C case (I) ([OSD]).
- Power-on hours: 100k h for commercial and industrial (§6.4, p.90).
- Thermal resistance of TI's ALW package (not the SiP): θJC 4.3, θJB 7.1, θJA 19.3 °C/W still air (Table 6.10.1, p.100).
- On-die VTM accuracy ±5 °C (Table 6-3, p.101).
- No power numbers in the datasheet. Use the AM62x Power Estimation Tool and the "Thermal Design Guide for DSP and ARM Application Processors" (§8.2.6, p.243).

---

# B. TPS65219 PMIC [PMIC]

## B.1 Capabilities

**Rails** (p.1; §6.3 ROC, p.8-9; §6.6-6.9, p.11-19):

| Resource | VIN | Output range / step | IOUT max | Notes |
|---|---|---|---|---|
| **Buck1** | 2.5-5.5 V (PVIN ≤ VSYS) | 0.6-3.4 V; 25 mV ≤ 1.4 V, 100 mV above | **3.5 A** | Peak limit 4.6/5.7/6.9 A. Headroom 500 mV @ 2.5 A, **700 mV @ IOUT_MAX**. DC accuracy ±1.5% (PWM). DVFS supported. f_SW 2.3 MHz. Ramp 0.3-1.65 ms |
| **Buck2, Buck3** | 2.5-5.5 V | same | **2 A** each | Peak limit 3.1/3.9/4.7 A. Buck3 output can be hard-strapped by VSEL_DDR (high 1.35 V, **float 1.2 V**, low = register) |
| **LDO1, LDO2** | 1.5-5.5 V (LDO mode); **bypass mode 1.5-3.6 V** | 0.6-3.4 V, 50 mV steps | **400 mA** | **LDO, bypass or load-switch modes. Voltage change while enabled (SD card 3.3 to 1.8 V)**. Dropout ≤ 300 mV @ 400 mA. ±1% accuracy (≥ 1 V). Bypass/LSW R ≤ 200-250 mΩ. Max ramp slew 12 mV/µs. 3.3 to 1.8 V transition ≈ 2 ms. In bypass, PVIN_LDOx must be within VOUT..VOUT+200 mV |
| **LDO3, LDO4** | 2.2-5.5 V (needs VSYS ≥ VOUT + 150 mV) | 1.2-3.3 V, 50 mV steps | **300 mA** | LDO or load-switch. Low noise (15 µVrms), PSRR 71 dB @ 1 kHz. Fast ramp (≤ 660 µs, **up to 25 mV/µs**) or slow ramp (≤ 2.3 ms, 9 mV/µs) |
| GPO1, GPO2 | - | Open-drain, pull-up ≤ 5.5 V (≤ VSYS) | - | Sequencable to enable external rails or load switches |
| GPIO | - | Open-drain output, or the multi-PMIC sync input | - | - |

**Input and supervision:**
- **VSYS 2.5-5.5 V.** PVIN_Bx and PVIN_LDOx must **never exceed VSYS**: abs max +200 mV for the bucks, +20 mV for the LDOs. Digital pull-up rails must also never exceed VSYS (p.8, p.145).
- POR rising 2.2-2.5 V. UVLO falling 2.175-2.25 V. **OVP 5.9-6.1 V** (§6.5, p.10).
- VSYS ramp time 0.1 ms to 600 s.
- EEPROM programming needs VSYS ≥ 3.3 V.
- UV monitors at -5% or -10%. Thermal WARM at 120 °C, HOT (shutdown) at 140 °C.

**Digital pins** (§6.10, p.20-21; Table 8-4, p.141-142):

**EN/PB/VSENSE** has three NVM-selectable modes:
- **EN**: level. Rising deglitch 50 ms (slow) or 120 µs (fast).
- **PB**: ON press 600 ms or 200 ms; OFF press 8 s.
- **VSENSE**: 1.2 V ±10% threshold, power-fail.

Wiring: use a 100 kΩ pull-up to VSYS if not driven. **It must be externally driven** to recover from an I2C OFF request (p.141).

**nRSTOUT:**
- Open-drain reset to the SoC. Low until ACTIVE, high in ACTIVE and STBY (§7.3.4, p.34).
- Pull-up voltage ≤ 3.4 V (ROC 3.1.25). Use 10 kΩ.
- Goes to AM62x MCU_PORz.

**nINT:** open-drain, pull-up ≤ 3.4 V, 10 kΩ.

**MODE/STBY:** pin or I2C selects forced-PWM or auto-PFM, and/or the STBY low-power state (polarity configurable).

**MODE/RESET:** MODE, or a WARM/COLD reset input (edge, 120 µs deglitch).

**VSEL_SD/VSEL_DDR** (one function per NVM):
- VSEL_SD: toggles the selected LDO (LDO1 or LDO2) between its VOUT (3.3 V) and a hard-coded 1.8 V. **Polarity and state must give 3.3 V at start-up.**
- VSEL_DDR: hard-wired strap for Buck3 (float gives 1.2 V for DDR4).

**Thresholds for digital inputs:** VIH ≥ 1.26 V, VIL ≤ 0.4 V, so 1.8 V logic from the SoC is fine.

**I2C** (§7.3.12, p.49; §6.12 p.22):
- **7-bit address 0x30** by default (changeable).
- Standard, Fast and Fast+ (1 MHz) at VIO of 1.8 or 3.3 V.
- SCL/SDA ≤ 3.4 V. Bus capacitance ≤ 400 pF.
- Do not issue I2C commands before the EEPROM load completes (~2.3 ms after VSYS POR).

**Sequencer** (§7.3.1-7.3.2, p.29-32):
- 16 slots. Slot durations of 0, 1.5, 3 or 10 ms.
- Each rail is UV-gated. The PMIC retries twice and then stays in INITIALIZE.
- All rails are discharged before power-up (RV check).
- The power-down sequence is independent and is gated on discharge.

**Thermal pad / package:** RHB is 5x5 mm QFN-32 (θJA 31.3 °C/W); RSM is 4x4 mm QFN-32 (θJA 31.9 °C/W) (§6.4, p.10).

## B.2 Orderable NVM variants for AM62x (Table 4-1, p.3)

The datasheet lists the OPN-to-use-case mapping. The per-OPN NVM register defaults (rail voltages, slots, MFP config) are **only in the per-OPN TRMs** listed below, which are **not in the folder**. The AM62 apps note is **SLVAFD0** ("Powering the AM62x with the TPS65219 PMIC", also cited in [DS] §8.1.1.1).

| OPN | Target SoC | VSYS | Memory | VDD_CORE | NVM TRM | Packages in addendum |
|---|---|---|---|---|---|---|
| TPS6521901 | AM62x, **AM62x SIP**, AM64 | 5 V | **DDR4** | 0.75 V | SLVUCH3 | RHB, RSM |
| TPS6521902 | AM62x, AM62x SIP, AM64 | 3.3 or 5 V | LPDDR4 | 0.75 V | SLVUCL0 | RHB, RSM |
| TPS6521903 | AM62x, AM62x SIP, AM64 | 3.3 or 5 V | **DDR4** | 0.75 V | SLVUCJ2 | RHB, RSM |
| **TPS6521904** | AM62x, AM62x SIP, AM64, AM243 | **3.3 or 5 V** | **DDR4** | **0.85 V** | **SLVUCL1** | RHB, RSM |
| **TPS6521907** | AM62x, AM62x SIP, AM64, AM243 | **5 V** | **DDR4** | **0.85 V** | **SLVUCL9** | RHB |
| TPS6521908 | AM62x, AM62x SIP, AM64, AM243 | 3.3 or 5 V | LPDDR4 | 0.85 V | SLVUCM0 | RHB |
| TPS6521909 / 10 | AM62A, AM67 | 5 V | LPDDR4 | 0.85/0.75 | SLVUCZ4 / SLVUD09 | - |
| TPS6521914 | STM32MP135A | 5 V | LPDDR3 | - | SPMU420 | - |
| TPS652190C | i.MX 8M Plus | 3.3 V | DDR4 | 0.85 | SLVUCV3 | - |
| TPS6521940 | i.MX93 | 5 V | LPDDR4 | 0.85 | SLVUD41 | - |
| **TPS6521905** | User-programmable (all rails OFF by default) | any | any | any | "TPS65219 NVM Programming Guide" | - |

- Footnote: TI's **AM62B starter kit with PMIC ships with TPS6521904 (0.85 V core)**. It can be modified to 0.75 V with TPS6521903.
- **"TPS6521920" does not appear in this datasheet revision.**
- TPS6521906RSMR appears in the package addendum without a use-case row.

### Rail mapping documented in the datasheet (only for NVM-ID 0x01 = TPS6521901, AM62x + DDR4, 0.75 V core)

From Fig 7-2 (p.30) and Fig 7-3 (p.32):

| Order (power-up slot) | PMIC resource | Voltage | AM62x / system rail |
|---|---|---|---|
| Slot 0 (1.5 ms) | **Buck2** | 3.3 V | DVDD3V3 (3.3 V IO, VDDA_3P3_USB) |
| Slot 1 | **GPO1** | (enable) | DVDD1V8: an **external** 1.8 V regulator enabled by GPO1 |
| Slot 1 | **LDO4** | **2.5 V** | **DDR4 VPP** |
| Slot 1 | **LDO1** | 3.3 V / 1.8 V (VSEL_SD) | **VDDSHV5 (SD card IO)** |
| Slot 1 (slot 2 = 3 ms) | **LDO3** | 1.8 V | VDDA_1V8 (low-noise analog: PLL/PHY/OSC) |
| Slot 3 (1.5 ms) | **Buck3** | **1.2 V** | **VDDS_DDR** (+ DDR4 VDD/VDDQ) |
| Slot 4 (1.5 ms) | **Buck1** | 0.75 V | VDD_CORE group |
| Slot 5 (1.5 ms) | **LDO2** | 0.85 V | VDDR_CORE |
| Slot 9 (~11.5 ms after the last rail) | **nRSTOUT** | - | MCU_PORz (meets the ≥ 9.5 ms rule) |

- The power-down order is roughly the reverse: nRSTOUT, then Buck3, LDO2 and Buck1, then GPO1, LDO3 and LDO1, then LDO4 and Buck2, with 10 ms slots (Fig 7-3).
- The generic example in §8.2.1 (Fig 8-1, p.138) shows a **3.3 V VSYS** variant. There, Buck2 = 1.8 V feeds LDO2 = 0.85 V, the 3.3 V IO comes from an **external load switch enabled by GPO2** (which must have active discharge), and LDO1 runs in **bypass** for the SD card.

### Selecting the OPN for OSD6254 (AM6254 @ 1.4 GHz) + DDR4

**Constraints that drive the choice:**
- 1.4 GHz requires VDD_CORE = 0.85 V (§A.1).
- At 0.85 V, **VDD_CORE and VDDR_CORE must share one source** ([DS] Table 6-5 note 11-12). That frees one LDO compared with the 0x01 mapping.
- DDR4 needs **1.2 V** (VDDS_DDR and DRAM) and **2.5 V VPP**.

**Best fit:**

| VSYS | Recommended OPN |
|---|---|
| 5 V | **TPS6521904** or **TPS6521907** (both DDR4, 0.85 V) |
| 3.3 V | **TPS6521904** only |

TPS6521904 is the default on TI's AM62B-P1 starter kit, so it has the most reference collateral. **Get SLVUCL1 (and SLVUCL9) to confirm the exact rail map, the sequence, and whether VSEL is configured as SD or DDR.**

**Inferred mapping for TPS6521904 (unverified; check against SLVUCL1):**
- Buck1 = 0.85 V for VDD_CORE and VDDR_CORE together.
- Buck3 = 1.2 V for DDR.
- LDO4 = 2.5 V for DDR4 VPP.
- LDO1 = 3.3/1.8 V for the SD card.
- LDO3 = 1.8 V analog.
- Buck2 and the remaining LDO provide 3.3 V / 1.8 V digital IO.
- With a 3.3 V VSYS, a GPO-enabled load switch provides 3.3 V IO, because Buck headroom is ≥ 700 mV.

**If 1.25 GHz is acceptable:** TPS6521901 (5 V) or TPS6521903 (3.3/5 V) at 0.75 V core is the documented path (rail map above).

**Fallback:** TPS6521905 (user-programmable) if no factory NVM fits. EEPROM programming needs VSYS ≥ 3.3 V.

**Cross-checks to make against whichever OPN is chosen:**
- **Ramp slew.** AM62x requires < 18 mV/µs. LDO3/LDO4 in **fast-ramp** mode can reach 25 mV/µs, so any AM62 rail on LDO3/4 should be in slow-ramp mode. Bucks (≥ 0.3 ms to 3.3 V, about 11 mV/µs) and LDO1/2 (≤ 12 mV/µs) are within the limit.
- **Total capacitance.** SiP-internal plus board decoupling on each PMIC rail must stay within the limits in §B.3.
- **3.3 V from a buck needs VSYS ≥ ~4.0 V** (700 mV headroom at full load; §8.3, p.144). With a 3.3 V VSYS, 3.3 V must come from a load switch or LDO bypass.

## B.3 External components and layout (§8.2.3, p.139-141; §8.4, p.145-146; ROC p.9)

**Bucks:**
- **L = 0.47 µH** (range 330-611 nH), **DCR ≤ 50 mΩ**.
- **Isat ≥ 7.4 A for Buck1, ≥ 5.4 A for Buck2/3.**
- **C_in = 4.7 µF / 10 V per PVIN_Bx** (≥ 3.9 µF effective). PVIN_B1_1 and PVIN_B1_2 share one cap.
- **C_out (total local + POL, after derating, ESR ≤ 10 mΩ, X7x preferred):**

| BW mode | Total C_out |
|---|---|
| Low BW | 10-75 µF |
| High BW | 30-220 µF |

- **Buck BW mode is set by the NVM** (BUCKx_BW_SEL). BUCK_FF_ENABLE must never be changed.
- With more than 50 µF of load capacitance, the load during ramp must be ≤ ~25% of the rated current (p.37).

**LDO1/2:**
- C_in 2.2 µF (6.3 V or more).
- **C_out 2.2 µF local (≤ 4 µF local after derating).**
- **Total ≤ 20 µF in LDO mode; ≤ 50 µF in bypass or load-switch mode.**

**LDO3/4:**
- **Shared PVIN_LDO34 C_in 4.7 µF.**
- C_out 2.2 µF local (≤ 4 µF).
- **Total ≤ 15 µF in fast ramp; ≤ 30 µF in slow ramp.**

**VSYS and VDD1P8:**
- VSYS: 2.2 µF.
- VDD1P8: 2.2 µF, placed on the same layer as the IC with 2-3 GND vias. **No load allowed.**
- Optional 47 µF bulk on the input if the source is far away (§8.3). Prefer a pre-regulator **without** active discharge.

**Unused resources** (Table 5-1, p.4-7):
- Unused buck: FB_Bx to GND, LX floating, PVIN to VSYS.
- Unused LDO: VLDOx floating, PVIN to VSYS.
- Unused GPOs: floating.
- VSEL pin: GND if n/a.

**Layout:**
- Input caps right at PVIN_Bx. If they are on the back side, add a 0.1 µF cap on the top side.
- Use 3-4 vias per amp at the cap grounds.
- **Put the inductor on the same layer as the IC** (no vias in the switch node). Keep the switch node small and away from sensitive nets. An RC snubber is optional.
- **FB_Bx:** route it as a trace (not a pour) to the **local** output cap, with < 1 Ω. **There is no remote sense.** Keep it away from the switch node and inductor; an inner layer is allowed.
- Place the output caps close to the inductor.
- **Thermal pad: ≥ 9 vias to GND.**
- **AGND: do not connect it to the thermal pad.** Use a short trace to its own via to the GND plane.

---

# C. AM62x TRM: Initialization (Ch. 5, pp.432-491) [TRM]

## C.1 Boot flow essentials (§5.2.3, p.437-439)

- The SMS M4 ROM is the boot controller. The DM R5 ROM loads the image, the M4 verifies it, and the R5 restarts into the SBL. After that, the SBL must load TI SYSFW into the M4.
- **BOOTMODE[15:0] are latched into CTRLMMR_MAIN_DEVSTAT** after MCU_PORz release.
- The M4 ROM arms a **3-minute RTI watchdog** for the ROM stage, and again for the SBL stage.

**Conditions that must hold at POR or the boot fails (p.439):**
- The USB cable is plugged in (for USB boot).
- **The Ethernet PHY is powered and out of reset.**
- **The SD socket is powered** and a card is inserted.
- The eMMC, OSPI/QSPI/SPI flash, I2C EEPROM and NOR/NAND are all powered and out of reset.

## C.2 BOOTMODE pin map (Table 5-2..5-5, p.442-443)

| Bits | Function |
|---|---|
| [2:0] | PLL reference: **011 = 25 MHz** (the only listed value; Table 5-3) |
| [6:3] | Primary boot device |
| [9:7] | Primary boot config |
| [12:10] | Backup boot device |
| [13] | Backup config |
| [15:14] | Reserved |

**All 16 pins must have pull resistors.** Pull-ups go to **VDDSHV3**, pull-downs to GND. None may float, including the reserved pins (Note, p.442).

**Primary boot, [6:3]** (Table 5-4):

| B6..B3 | Mode | B9 | B8 | B7 |
|---|---|---|---|---|
| 0000 | Serial NAND | rsvd | Read Mode 2 | Read Mode 1 |
| 0001 | **OSPI** (1S-1S-8S, cmd 0x8B @ 50 MHz) | rsvd | Iclk (0 = ext / 1 = int loopback) | Csel (CS0/CS1) |
| 0010 | QSPI (1S-1S-4S, 0x6B @ 50 MHz) | rsvd | Iclk | Csel |
| 0011 | SPI (0x03 @ 6.25 MHz) | rsvd | Mode (0 = SPI mode 0 / 1 = mode 3) | Csel |
| 0100 | **Ethernet RGMII** | Clkout (1 = 25 MHz on CLKOUT0) | Delay, **must be 0** (internal TX delay) | Link info (0 = MDIO scan) |
| 0101 | Ethernet RMII | Clkout (1 = 50 MHz) | Clk src (0 = ext / 1 = int) | must be 0 |
| 0110 | I2C (EEPROM on I2C0) | Bus reset | rsvd | Addr (0 = 0x50 / 1 = 0x51) |
| 0111 | **UART** | rsvd | rsvd | must be 0 |
| 1000 | **MMCSD** (SD card or eMMC UDA) | **Port: 1 = MMC1 (SD); 0 = MMC0 (eMMC)** | rsvd | FS/raw (0 = FAT, 1 = raw) |
| 1001 | **eMMC boot partition** | rsvd | rsvd | rsvd |
| 1010 | **USB** | **Core Volt: 0 = 0.85 V, 1 = 0.75 V** | Mode: 0 = **DFU**, 1 = host MSC | Lane swap |
| 1011 | GPMC NAND | rsvd | rsvd | rsvd |
| 1100 | GPMC NOR | rsvd | rsvd | rsvd |
| 1101 | Reserved | | | |
| 1110 | xSPI | SFDP | Read cmd (0x0B/0xEE) | Mode (1S-1S-1S @ 50 MHz / 8D-8D-8D) |
| 1111 | No-boot / Dev-boot | rsvd | ARM/Thumb | No/Dev (0 = Dev boot) |

**Backup boot, [12:10] + B13** (Table 5-5):

| B12..B10 | Backup mode | B13 meaning |
|---|---|---|
| 000 | None | - |
| 001 | USB | Mode (DFU/MSC) |
| 010 | Reserved | - |
| 011 | UART | B13 must be 0 |
| 100 | Ethernet | IF (0 = RGMII, 1 = RMII) |
| 101 | MMCSD | Port |
| 110 | SPI | - |
| 111 | I2C | - |

**Backup MMCSD supports only filesystem mode, in 1-bit.** Backup USB does not support lane swap.

**Design notes for the strap network:**
- **Set the USB "Core Volt" bit (B9) to match the real VDD_CORE.** For a 0.85 V design, B9 = 0 when USB is primary. The datasheet does not say which voltage the ROM assumes for USB in *backup* mode; check this.
- The BOOTMODE balls are GPMC0_AD0-15 and are latched only at reset. If GPMC or VOUT functions share these nets, the straps must not fight external drivers during reset. Use DIP switches and resistor networks so modes can be changed at bring-up.

## C.3 Boot-device requirements useful for bring-up

**SD card (MMC1)** (§5.4.3, p.457-458):
- MMC1_SDCD must read **0** or the ROM declares no card.
- Raw mode (redundant image at 0x400000) or FAT16/32 mode.
- SDR, backward-compatible timing only. It starts at 3.3 V; UHS switching happens later in software.

**eMMC (MMC0)** (§5.4.4, p.459-460):
- UDA raw or FS through MMCSD mode with Port = 0, or the **boot partition** through mode 1001.
- MMC0 works at 1.8 V or 3.3 V.
- For warm-reset boot: wire eMMC RST_n and set ext_csd[162] = 0x1.

**OSPI/QSPI/SPI/xSPI/Serial NAND** (§5.4.1, p.443-456):
- The image is read from offset 0x0, with a redundant copy at 0x400000. Not XIP.
- **For flash larger than 128 Mb, a hardware RESET# is required** (3-byte-address ROM).
- xSPI and Serial NAND support CS0 only.

**Ethernet** (§5.4.5, p.461-465):
- RGMII1/RMII1 plus MDIO0.
- BOOTP/TFTP over IPv4: 4 s BOOTP timeout x 10 retries; TFTP 1 s x 10 retries.
- "Booting from RGMII requires that an attached PHY be configured for RGMII-ID Mode immediately upon exiting reset", which means PHY straps. The ROM enables the internal (TX) delay.
- MAC-to-MAC works with Link info = 1 (forced 1G full duplex).

**USB (USB0 only)** (§5.4.6, p.465-466):
- **DFU device: VID 0x0451, PID 0x6165.** The ROM tries to enumerate for **60 s**.
- MSC host mode boots from FAT32.
- Caution: in host-boot mode, do not connect a Type-AB connector to another host (two VBUS sources would be connected together).
- USB0_DRVVBUS is configured by the ROM even in DFU mode.

**UART (UART0, VDDSHV0 balls)** (§5.4.7, p.466-468):
- **115200 8N1, XMODEM-CRC** (128- or 1024-byte blocks).
- The ROM sends 'C' pings for a few seconds; send the image before they stop.
- Expose UART0 TXD/RXD on a header or a USB-UART bridge. This is also the Linux console path on TI SDKs.

**I2C** (§5.4.2): EEPROM at 0x50 or 0x51 on I2C0. A hung-bus reset is optional.

**GPMC NOR/NAND** (§5.4.8-9): NOR is 16-bit non-mux on CS0 (no CSn3). NAND is ONFI 1.0, 8-bit, on CS0, with 2K or 4K pages.

**No-boot / Dev-boot** (§5.4.10, p.471): useful for JTAG bring-up when no image is available.

**PLL setup by the ROM** (§5.5, p.472-473): the ROM programs only the PLLs the boot mode needs, for example MAIN_PLL0 for OSPI at 200 MHz and eMMC at 200 MHz, and PER1 for CPSW at 250 MHz.

**Suggested bring-up strap set** (an example of field usage, not a design decision):
- [2:0] = 011 (25 MHz).
- Primary = eMMC boot partition (1001) **or** MMCSD with Port = 1 (SD) for early bring-up.
- Backup = USB DFU (001, B13 = 0) or UART (011).
- [15:14] = 00 through pull-downs.

Make the primary and backup selections switchable with DIP switches.

---

## D. Top design-relevant flags (summary)

1. **1.4 GHz needs VDD_CORE = 0.85 V (T grade).** VDD_CORE and VDDR_CORE then come from one rail. Use TPS6521904 (3.3/5 V VSYS) or TPS6521907 (5 V VSYS), and confirm the rail map in SLVUCL1/SLVUCL9.
2. The AM62x **"VPP" is the 1.8 V eFuse pin** and must be NC or GND in normal operation. **DDR4 VPP 2.5 V** is a separate rail (TPS65219 LDO4 in TI's DDR4 configs).
3. Sequence: 3.3 V, then 1.8 V, then VDDS_DDR, then core, then VDDR. Slew < 18 mV/µs. **MCU_PORz must stay low ≥ 9.5 ms after rails are good** (TPS65219 nRSTOUT does this). On a brown-out, all rails must go below 300 mV before restarting.
4. **SD UHS-I uses external VDDSHV5 switching** (PMIC LDO1/2 plus VSEL_SD; must start at 3.3 V). eMMC HS200 needs VDDSHV4 = 1.8 V. **Routing mismatch is ≤ 8 ps** for HS200/SDR104 and trace delay ≤ 756 ps (HS200).
5. **RGMII: the TX delay is always internal; the PHY must provide the RX delay.** Mismatch ≤ 50 ps per group. Use ±50 ppm on the 25 MHz crystal if the PHY clock is derived from the SoC.
6. **USB VBUS divider and zener network** (3.48 k / 16.5 k / 10 k + 6.8 V zener). **499 Ω RCALIB** on USB0, USB1 and CSI.
7. **BOOTMODE[15:0] (GPMC0_AD) all pulled to VDDSHV3 or GND.** The USB-boot core-voltage bit must match 0.85 V. The ROM needs the SD card detect low, and the PHY and flash powered and out of reset at POR.
8. CAP_VDDSx caps (0.8-1.5 µF) are needed for any VDDSHVx that runs at 3.3 V.
9. TPS65219: 470 nH / ≤ 50 mΩ inductors (Isat 7.4 A / 5.4 A), 4.7 µF per PVIN, and output capacitance limits that **include SiP-internal and POL caps**. FB is local only. AGND stays isolated from the pad. nRSTOUT, nINT and I2C pull-ups must be ≤ 3.4 V and ≤ VSYS.
10. Still missing: the Octavo OSD62x-PM full datasheet (ball map, internal rail merges and capacitance, DDR4 VPP requirement) and the TPS65219 per-OPN TRM (SLVUCL1/SLVUCL9).
