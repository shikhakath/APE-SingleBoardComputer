# SK-AM62B-P1 (PROC142B) Reference Design: Analysis Notes for an OSD6254 (OSD62x-PM) SBC

Sources (all under `reference/`):
- **Schematic:** `1_PROC142B/1_SCHEMATIC/2_PDF_Standard/PROC142B(002)_SCH_With_Design_Updates..Notes_V1.0.pdf`. It has 46 sheets, Rev B, revision-history ver 0.15 (23 Apr 2026), and was designed for TI by Mistral. **"p.N" below means schematic sheet N.**
- **BOM:** `1_PROC142B/2_BOM/PROC142B(002)_BOM.xlsx`. Two sheets: *Assembly_BOM* and *All_Parts_BOM*.
- **Stackup:** `7_LAYER STACKUP/...STACKUP.pdf`. This is a Polar SpeedStack "MISTRAL-AM62X SKEVM PROC114E3", dated 23-Apr-2022. It is byte-identical in the 142A and 142B folders.
- **FAB drawing:** `5_Gerber_PDF/FAB/PROC142B_FAB.pdf`, dated 25-Nov-2024.
- **Other board data:** the IDF outline `.emn` and the Altium ASCII `.alg`. Only the header, layer table, padstacks and netlist were read.
- **Power sequence:** `8_Voltage_Sequencing/...Power Sequence.pdf`. These are Mistral measurements on PROC142A.
- **Simulation scorecard:** `3_BoardFile/Simulation_Dashboard/AM62x_Simulations_Scorecard.pdf`. It is identical for 142A and 142B.
- **Readme:** `2_PROC142A/1_SCHEMATIC/Proc142A_Schematic_Revision_Readme.pdf` and the PROC142A design-update schematic, rev history p.2.
- **Datasheets cross-checked:** `datasheets/OSD62x-PM-Overview-2-Page-V1.pdf` and `datasheets/tps65219.pdf` (Table 4-1).

> **Correction to the brief.** SK-AM62B-P1 uses **DDR4**, not LPDDR4: one x16 Micron **MT40A1G16TB-062E IT:F**, 16 Gb = 2 GB (p.4, p.18, BOM U29). LPDDR4 is used on SK-AM62-LP (PROC124) and SK-AM62A/P-LP.
>
> So the SK memory technology **matches** the OSD62x-PM's internal DDR4. That makes the SK's PMIC NVM (TPS6521904 = DDR4 + 0.85 V core) directly relevant.

> **SoC.** The BOM fits **AM6254ATCGGAALW**: FCCSP "ALW", 425 balls, 13 × 13 mm, 0.5 mm pitch. The block-diagram text says AM6254ATC**GH**AALW. Both are -40 to 105 °C Tj OPNs; the BOM is authoritative.

> **SiP.** The OSD62x-PM overview gives: AM62 + DDR4 + passives in a 9 × 14 mm, **500-ball, 0.5 mm pitch** BGA. The TPS65219 is external; Octavo's OSD62PM-BRK carries its own TPS65219. OPNs are OSD6254-1G-BPM (0–85 °C) and OSD6254-1G-IPM (-40–85 °C).

---

## 1. Block diagram / feature list (p.1, p.4, p.5)

The board is "AM625/AM623 Starter Kit SK (EVM) with TPS6521904 PMIC", 85.0 × 150.1 mm, 10 layers, 1.6 mm thick.

| Function | Implementation | AM62 interface | Sheet |
|---|---|---|---|
| Power input | 2× USB Type-C via TPS65988 dual-port PD controller. J11 is a power-only sink; J13 is a DRP with USB0 data. | I2C0 (PD 0x38/0x3F) | p.10, p.37 |
| PMIC | TPS6521904RHBR (U14) | I2C0 0x30 | p.13 |
| Memory | 2 GB DDR4 x16, MT40A1G16TB-062E IT:F (U29) | DDR0 (DDR4) | p.18 |
| eMMC | 32 GB Micron MTFC32GAZAQHD-IT (U28), 8-bit | MMC0 (1.8 V, VDDSHV4) | p.20 |
| microSD | GCT MEM2051-00-195-00-A (J20), UHS-I with 3.3/1.8 V IO switching | MMC1 (VDDSHV5) | p.21 |
| OSPI NOR | 512 Mb Infineon S28HS512TGABHM010 (U9). Footprint-compatible with W35N01JWTBAG OSPI NAND. | OSPI0 (1.8 V, VDDSHV1) | p.22 |
| Wi-Fi/BT | M.2 2230 Key-E socket (TE 2199119-4, J2), intended for TI **M.2-CC3351** (Wi-Fi 6 + BLE). The module is not on the BOM. | MMC2 SDIO (1.8 V), UART1, McASP1, GPIOs, 32 kHz slow clock | p.19 |
| Gigabit Ethernet ×2 | 2× DP83867IRRGZ (U51, U49). RJ45 with integrated magnetics and LEDs: LINK-PP LPJG16314A4NL (J6, J4). | CPSW3G RGMII1/RGMII2 (3.3 V, VDDSHV2), MDIO | p.24–26 |
| HDMI | SiI9022ACNU parallel-RGB → HDMI transmitter (U10), TPD12S016 companion, HDMI-A connector FCI 10029449-001RLF (J5) | VOUT0 24-bit DPI (3.3 V, VDDSHV3), I2C1, McASP1 audio | p.43 |
| LVDS display | 40-pin 0.5 mm FPC, GCT FFC2A32-40-T (J21). Dual-link: 2 × (4 data + clock). Also carries I2C0 touch, TS_INT#, reset and 3.3 V. | OLDI0 | p.39 |
| Camera | 15-pin 1.0 mm FPC, TE 1-1734248-5 (J19), RPi-camera style, 2 data lanes + clock | CSI0 (lanes 0/1), I2C2 via switch | p.40 |
| Audio | TLV320AIC3106IRGZT codec (U66). 3.5 mm TRRS headset jack (CUI SJ-43514-SMT, J12). | McASP1 (muxed), I2C1 0x1B | p.41–42 |
| USB host | USB1 → single USB-A (Würth 629104151021, J7) behind a TPS2051BD 500 mA switch. **No USB hub.** | USB1 | p.38 |
| USB DRP | USB0 → Type-C DRP J13 (Molex 2012670005); CC handled by TPS65988 port 2 | USB0 | p.37–38 |
| Debug UART | FTDI FT4232HL quad UART (U46), micro-B J15 | MAIN_UART0, MAIN_UART1, MCU_UART0, WKUP_UART0 | p.33 |
| JTAG | On-board XDS110 (TM4C1294NCPDT, micro-B J16) plus a 20-pin cTI header (Samtec FTR-110-51-S-D-06, J17) with buffers/mux | JTAG, EMU0/1 | p.5, p.29, p.31–32 |
| 40-pin expansion | 2×20 2.54 mm (Sullins PEC20DAAN, J3), **Raspberry-Pi-style pinout** | I2C2, I2C0, UART5, SPI0, SPI2, ePWM, eCAP, GPIO, CLKOUT0 | p.35 |
| MCU header | 2×14 (J9), "compatible with AM64x SK" | MCU_SPI0, MCU_UART0, MCU_I2C0, MCU_MCAN0, MCU resets | p.36 |
| PRU header | 2×10 (J10) | PR0_PRU0_GPO0-7, I2C0 | p.34 |
| Boot config | 2× 8-position DIP (SW1/SW2, Würth 416131160808), 16 BOOTMODE bits through 2× SN74AVC8T245 buffers | BOOTMODE[15:0] (shared with GPMC) | p.28, p.34 |
| Board ID | AT24C512C-MAHM-T EEPROM (U26) | I2C0 0x51 | p.23 |
| Temperature | 2× TMP100NA (U11 at the SoC, 0x48; U33 at the DDR, 0x49) | I2C1 | p.23 |
| Power monitor | 5× INA231 (6th, for VDDR_CORE, is DNI) with 10 mΩ 4-terminal shunts | I2C1 | p.14 |
| GPIO expansion | TCA6424ARGJR (U70, 0x22) and TCA6408ARGTR (U110, 0x20) | I2C1 | p.41 |
| LEDs | TPIC2810D I2C LED driver (U38, 0x60) driving 8 LEDs, plus 2 user LEDs and power LEDs | WKUP_I2C0 | p.26 |
| Test automation | 40-pin FH12A FPC (J23) with I2C buffers and a boot-mode IO expander | I2C1 (buffered) | p.27, p.30 |

---

## 2. Power

### 2.1 Input (p.10, p.6, p.7)

- **USB Type-C PD only. There is no barrel jack.**
  - TPS65988DHRSHR (U68) is a dual-port PD controller with integrated power paths.
  - **Port 1 (J11, "TYPE-C PWR")** is sink-only with no data role.
  - **Port 2 (J13, "TYPE-C DRP")** is DRP power and USB0 host/DRP data.
  - Both ports' PP_HV paths feed **VMAIN**. The power diagram labels this "VMAIN = 15 V / 3 A" (p.6).
  - Downstream converter limits: TPS630702 VIN ≤ 16 V, LM61460 4.5–24 V.
  - Recommended adapters are in SPRUJ40 (D-Note p.10).
- **PD controller support parts:**
  - Configuration lives in a W25Q80DVSNIG SPI flash (U39), with an optional 2×5 programming header (J22, DNI).
  - ADCIN straps are set to "BP_NoWait / Safe Configuration".
  - I2C2 (0x38/0x3F) goes to SoC I2C0; the I2C1/I2C3 masters go to test points.
- **VBUS protection:** TVS2200DRVR flat-clamp surge diodes on both VBUS inputs (U69, U78). TPD1E01B04 on each CC line (D2, D9, D4, D10).
- **Source capability on port 2:** an external power path sources 5 V / 0.5 A from VCC_5V0. Two CSD25310Q2 P-FETs (Q14, Q16) are gate-driven from PP_EXT2, and this is enabled by SoC_USB0_DRVVBUS (p.10).
- **VMON_VSYS:** VCC_5V0 is divided by 10 k / 1.1 k (R375/R108) to VDDA_SYS_MON. This feeds the SoC VMON_VSYS pin (H10) for early power-fail detection (p.15 D-Note). A 22 pF cap across R108 was added in the PROC142A update.

### 2.2 Power tree (p.6, p.7, p.11–13)

| Ref | Part | Input → Output | Rating | Notes / sheet |
|---|---|---|---|---|
| U68 | TPS65988DHRSHR | VBUS1/VBUS2 → VMAIN | ≤15 V / 3 A contract | p.10 |
| U76 | **TPS630702RNMR** buck-boost | VMAIN → **VCC_5V0** 5.0 V | 2 A (budget 1.21 A) | L13 XFL4020-152 (1.5 µH). EN = VCC_5V0_EN, pulled up 10 k to VCC_3V3_MAIN. The PMIC GPO1 path through R676 is **DNI**, despite the block diagram. p.11 |
| U67 | **LM61460AANQRJRRQ1** sync buck | VMAIN → **VCC_3V3_MAIN** 3.3 V | 6 A (budget 5.35 A) | L12 XAL6060-472 (4.7 µH). VIN 4.5–24 V. This is the "always-on" 3.3 V. p.12 |
| U104 | **TPS22965DSGT** load switch | VCC_3V3_MAIN → **VCC_3V3_SYS** | 6 A (budget 2.9 A) | ON = **PMIC GPO2** (TPS22965_EN). CT = 220 pF for the SoC IO slew requirement. p.13 |
| U14 | **TPS6521904RHBR** PMIC | VSYS / PVIN = VCC_3V3_MAIN (3.3 V) | Rails in §2.3 | p.13 |
| U21 | TLV75518PDBVR LDO | VCC_3V3_SYS → **VPP_1V8** (eFuse) | 0.5 A | EN = IO-expander VPP_LDO_EN (off by default). p.12 |
| U24 | TLV75510PDQNR LDO | VCC_1V8 → **VDD_1V0** (Ethernet PHY core) | 0.5 A (budget 2 × 216 mA) | p.12. D-Note: use the DBV (SOT-23) package because the QFN has manufacturing issues. |
| U113 | TLV75801PDBVT LDO (adjustable) | VCC_3V3_MAIN → **VDD_CANUART** 0.85 V | 0.5 A | Added in rev B for partial-IO / low-power. Change R781 to 274 k for 0.75 V. p.12 |
| U13 | TPS22996HQDYCRQ1 dual load switch | Ch1: VCC_3V3_SYS → VDD_MMC1 (SD card VDD). Ch2: PMIC LDO1 → VDDSHV_SDIO (SoC VDDSHV5 and SD pull-ups). | 4 A per channel | Replaced the single switch in rev B. EN uses AND logic (U22). p.21 |
| U34 | TPS2051BD | VCC_5V0 → USB-A VBUS | 0.5 A | OC flag goes to the IO expander. p.38 |
| U48 | TPS22902YFPR | VCC_3V3_SYS → VCC3V3_EXP (40-pin header) | 500 mA | EN from the IO expander; **off by default**. p.35 |
| U4 | TPS22946YZPR (current-limited) | VCC_5V0 → VCC5V0_EXP (40-pin header) | 150 mA max | EN from the IO expander; **off by default**. p.35 |
| U62 | TPS22902YFPR | VCC_3V3_SYS → VCC3V3_PRU | — | p.34 |
| U95 | TPS73533DRVR LDO | FT4232 USB VBUS → VCC_3V3_FT4232 | 0.5 A | Powers the UART bridge from its own USB port (partial-IO). p.33 |
| U79 | TPS79601DRBR LDO | XDS USB VBUS → VCC3V3_XDS | 1 A | XDS110 only. p.29 |
| — | 0 Ω | VCC_3V3_MAIN → VCC3V3_TA | — | Test automation. The p.7 diagram still shows a TPS62177 that is no longer fitted. |

Analog rails are filtered with ferrite beads (p.17):
- BLM15PX121SN1D (120 Ω, 2 A) on each 1.8 V analog rail: VDDA_1V8 → VDDA_1V8_CSIRX, _USB, _MCU, _OLDI, PLL0/1/2.
- BLM18SG260TN1D (26 Ω, 6 A) from VDD_CORE → VDDA_CORE_USB and VDDA_CORE_CSI.
- CAN_IO_3V3 (VDDSHV_CANUART) is fed from **VCC_3V3_MAIN** (always-on) through FL18.

### 2.3 TPS6521904 PMIC assignment (p.13, p.6, p.7)

PMIC I2C address 0x30 on SoC I2C0. The NVM is TPS6521904 (DDR4, VDD_CORE 0.85 V, VIN 3.3 V or 5 V; TRM **SLVUCL1**, datasheet Table 4-1). TPS6521903 is the 0.75 V-core variant.

| PMIC rail | Rating | Configured output | Net | SoC loads | Budget (p.6) | Sequence slot (p.7) |
|---|---|---|---|---|---|---|
| BUCK1 | 3.5 A | 0.85 V | VCC_CORE → VDD_CORE | VDD_CORE, and VDDR_CORE through a 0 Ω (R699; LDO2 path R123 DNI). Also VDDA_CORE_USB/CSI through 26 Ω beads. | 2.7 A | 6 (last) |
| BUCK2 | 2 A | 1.8 V | VCC_1V8 → SoC_DVDD1V8 | VDDSHV1/4/6, VDDS_OSC0, VMON_1P8_SOC, OSPI, eMMC VCCQ, PHY 1.0 V LDO input, codec 1.8 V, clock buffer | 995 mA | 2 |
| BUCK3 | 2 A | 1.2 V | VDD_1V2 → VDD_DDR4 | SoC VDDS_DDR/VDDS_DDR_C, DDR4 VDD/VDDQ, **HDMI SiI9022 1.2 V** (AVCC/CVCC) | 936 mA | 5 |
| LDO1 | 400 mA | 3.3 V ↔ 1.8 V (VSEL_SD pin) | PMIC_VDDSHV_SDIO | SoC VDDSHV5 (MMC1/SD IO) through TPS22996 ch2 | 50 mA | 3 |
| LDO2 | 400 mA | (NVM) | VDD_LDO2 | **Not used**: R123 to VDDR_CORE is DNI. It is meant for VDDR_CORE = 0.85 V when VDD_CORE = 0.75 V (TPS6521903 config). PVIN_LDO2 = VCC_1V8. | 150 mA | — |
| LDO3 | 300 mA | 1.8 V | VDDA1V8 → VDDA_1V8 | VDDA_1V8, VDDA_MCU, PLLs, CSI/USB/OLDI 1.8 V analog, VDDA_TEMP | 200 mA | 2 |
| LDO4 | 300 mA | 2.5 V | VDD_2V5 | DP83867 VDDA2P5 (×2) and **DDR4 VPP** (through FL23, 120 Ω) | 300 mA | 4 |

PMIC control pins (p.13):
- **Input supplies:**
  - VSYS = VCC_3V3_MAIN.
  - PVIN_B1/B2/B3, PVIN_LDO1 and PVIN_LDO34 = VCC_3V3_MAIN.
  - PVIN_LDO2 = VCC_1V8.
- **Output stage:** each buck uses a 0.47 µH Murata DFE201612E-R47M inductor (L5, L7, L8) and 47 µF output caps. 10 mΩ shunts sit after the buck outputs.
- **nRSTOUT → PMIC_PGOOD:** this feeds the SoC_PORz/MCU_PORz logic.
- **nINT → EXTINTn** (SoC D16, open-drain) through the RC slew limiter.
- **EN/PB/VSENSE:** configured as **push-button (active low)**. Driven by SW5 and the test-automation TEST_POWERDOWN.
- **GPO1:** VCC_5V0_EN option, DNI. **GPO2:** TPS22965_EN, which holds VCC_3V3_SYS off until sequence slot 1. **GPIO:** test point only.
- **VSEL_SD/VSEL_DDR:** from SoC **GPMC0_CLK / GPIO0_31 (ball P25)**, pulled up 10 k so SD starts at 3.3 V.
- **MODE/RESET:** not driven from RESETSTATz (R615 DNI). Warm reset does not touch the PMIC.
- **MODE/STBY:** goes to a test point. The SoC → PMIC_STBY link was removed in the 142A update.
- **SoC PMIC_LPM_EN0 (B7):** goes to TP124 only.

### 2.4 SoC supply / IO-domain map (p.15)

| SoC pin group | Rail |
|---|---|
| VDD_CORE | 0.85 V (BUCK1) |
| VDDR_CORE | 0.85 V, tied to VDD_CORE through 0 Ω. The D-Note recommends the same source so they ramp together. |
| VDDS_DDR, VDDS_DDR_C | VDD_DDR4 1.2 V |
| VDDSHV0 (general), VDDSHV2 (RGMII), VDDSHV3 (VOUT/GPMC/PRU) | SoC_DVDD3V3 = VCC_3V3_SYS |
| VDDSHV1 (OSPI), VDDSHV4 (MMC0), VDDSHV6 (MMC2/SDIO-WLAN) | SoC_DVDD1V8 |
| VDDSHV5 (MMC1/SD) | SoC_VDDSHV5_SDIO (switched 3.3/1.8 V) |
| VDDSHV_MCU | 3.3 V |
| VDDSHV_CANUART | CAN_IO_3V3 (from always-on VCC_3V3_MAIN) |
| VDD_CANUART | 0.85 V from TLV75801 |
| VDDS_OSC0 | 1.8 V |
| VDDA_* (PLL0-2, MCU, TEMP, OLDI, CSIRX, USB 1.8 V) | VDDA_1V8 (LDO3) through beads |
| VDDA_3P3_USB | 3.3 V |
| VMON_1P8_SOC, VMON_3P3_SOC | 1.8 V and 3.3 V rails |
| VMON_VSYS | 5 V divider |
| VPP | VPP_1V8 (switched LDO). R-Note: **never tie 1.8 V permanently to VPP.** |

### 2.5 Discrete load switches (summary)

- TPS22965 (U104): the 3.3 V SYS rail, sequenced by the PMIC.
- TPS22996-Q1 (U13): SD card VDD and SD IO supply.
- TPS2051B (U34): USB-A VBUS.
- TPS22902 (U48, U62): expansion 3.3 V and PRU 3.3 V.
- TPS22946 (U4): expansion 5 V.
- P-FETs CSD25310Q2 (Q14, Q16): Type-C port-2 5 V source path.

### 2.6 Power budget (p.6)

- VCC_3V3_MAIN: 5.35 A.
- VCC_3V3_SYS: 2.9 A.
- VCC_5V0: 1.21 A, split across:
  - USB-A: 500 mA.
  - Type-C source: 500 mA.
  - Expansion 5 V: 155 mA.
  - HDMI 5 V: 55 mA.
- Larger 3.3 V loads:
  - M.2 Wi-Fi: 800 mA on 3.3 V plus 200 mA on 1.8 V.
  - DDR4: 666 mA VDD plus 33 mA VPP.
  - Ethernet PHYs: 274 mA on 2.5 V and 2 × 216 mA on 1.0 V.
  - CSI connector: 250 mA.
  - SD: 200 mA.
  - PRU header: 200 mA.
  - OSPI: 156 mA.
  - eMMC: 120 + 140 mA.
  - MCU header: 100 mA.
  - HDMI TX: 70 + 10 mA.

### 2.7 Power sequence (p.7 and the sequencing PDF, PROC142A measurement)

PMIC slot order: (1) GPO2 → VCC_3V3_SYS; (2) BUCK2 1.8 V + LDO3 VDDA_1V8; (3) LDO1 VDDSHV5; (4) LDO4 2.5 V; (5) BUCK3 1.2 V DDR; (6) BUCK1 0.85 V core. After that, nRSTOUT/PGOOD releases MCU_PORz.

| Rail | Power-up t (ms from PMIC_PBn) | Power-down t (ms) |
|---|---|---|
| SoC_DVDD3V3 | 0.65 | 10.75 |
| SoC_DVDD1V8 / VDDA_1V8 | 10.05 | 10.75 |
| MCU_OSC0_XI clock | 10.15 | 10.8 |
| VDD_DDR4 1.2 V | 13.0 | 0.3 (first off) |
| VDD_CORE / VDDR_CORE 0.85 V | 14.3 | 10.8 |
| VDD_CANUART 0.85 V | 14.65 | 10.8 |
| MCU_PORz released | **28.45** | asserted at 0 |

D-Notes:
- Do not change the core voltage dynamically after reset release.
- If core is turned off, ramp everything down per the power-down sequence and wait until all rails are below 300 mV before re-powering (p.15).

### 2.8 Supervisory / reset (p.44, p.45, p.7)

- **SoC_PORz** = AND2(PMIC_PGOOD, JTAG_EMU_RSTn) from SN74LVC1G08 (U90, 3.3 V).
- **MCU_PORz** = AND3(SoC_PORz, TEST_PORZn, CONN_MCU_PORz) from SN74LVC1G11 (U72, 1.8 V). It has a 22 pF glitch filter and a pull-down.
  - D-Note: drive MCU_PORz from a fast-edge logic gate/buffer, **not** a slow open-drain PGOOD.
  - MCU_PORz is fail-safe and 3.3 V tolerant.
- **Warm reset:** the SW3 push button goes through an SN74LVC3G17 Schmitt-trigger debounce (U82) to RESET_REQz (F20), with a 22 pF glitch filter near the SoC. SW4 is a user-interrupt button to MCU_GPIO0_15. SW5 is the PMIC on/off button.
- **Errata i2407:** MCU_RESETSTATz is unreliable when MCU_RESETz is asserted, so Q2 and C156 are DNI (p.45).
- **Peripheral resets:** each is an AND of RESETSTATz (or PORz_OUT) and a GPIO/IO-expander line.
  - eMMC: U58.
  - OSPI: U6.
  - PHY1/PHY2: U40/U41 (3-input).
  - SD load switch: U22.
  - OLDI: U105.
  - Audio: U71.
  - PORz_OUT and RESETSTATz have pull-downs so attached devices stay in reset during power-up.
- There is no separate supervisor IC. PMIC nRSTOUT is the power-good.
- On-board observability: INA231 current monitors on VDD_CORE, DVDD1V8, VDDA_1V8, DVDD3V3 and VDD_DDR4 (VDDR_CORE unit is DNI), plus 2× TMP100.

---

## 3. Peripheral subsystems

### 3.1 Ethernet (p.24–26, p.46)

- **PHYs:** 2× **DP83867IRRGZ** on CPSW3G **RGMII1 → U51 (J6)** and **RGMII2 → U49 (J4)**. RGMII IO is 3.3 V (VDDSHV2).
- **PHY supplies:** three-supply configuration. VDDIO 3.3 V (VCC_3V3_SYS), VDDA2P5 2.5 V (PMIC LDO4), VDD1P0 1.0 V (TLV75510). VDDA1P8 pins go to decoupling only.
- **PHY clock:** 25 MHz LVCMOS. A 1.8 V ECS-2520MV-250-CN-TR oscillator (U53) feeds an **LMK1C1103PWR** 1:3 buffer (U52), which drives PHY1 XI, PHY2 XI and the SoC MCU_OSC0.
  - D-Note: the PHY XI amplitude is 1.8 V max; use a cap divider if the clock is 3.3 V.
- **MAC side:** series resistors (22 Ω) on the TX lines near the SoC. Shared MDIO/MDC with a 2.2 k pull-up.
- **Interrupt:** shared CPSW_RGMII_INTn/PRU_INTn → EXTINTn, with an RC of 62 Ω + 47 pF (changed from 620 Ω + 10 pF in rev B).
- **Reset:** IO expander GPIO AND RESETSTATz.
- **RBIAS:** reduced from 11 k, with a parallel cap added, for compliance performance (D-Note).
- **Magnetics:** integrated in the RJ45, LINK-PP **LPJG16314A4NL** (14-pin, LEDs). For discrete magnetics, follow the DP83867ERGZ-R-EVM.
- **Strap configuration:** see the "Strap configuration of Ethernet PHYs" sheet of the SK-AM64B schematic (R-Note p.46).

### 3.2 USB (p.10, p.37, p.38)

- **USB0 → Type-C DRP (J13).**
  - CC and VBUS are handled by TPS65988 port 2.
  - D+/D− go straight to the SoC through a common-mode choke (Murata DLW21SZ900HQ2B, L10) with a 0 Ω bypass option, plus **ESD122DMXR** (D5) on the data lines.
  - VBUS goes to SoC USB0_VBUS through a divider with a BZX84C6V8 zener clamp (D1).
  - **USB0 is the DFU boot port.**
- **USB1 → USB-A host (J7).**
  - TPS2051BD 0.5 A switch, CMC L9, **TPD4S012DRYR** ESD (U114, added in rev B), VBUS divider with D14.
  - USB1_DRVVBUS enables the switch (pull-down R650 DNI).
- **No USB hub, and no USB-PHY or Type-C mux chip.** USB2.0 only (AM62 has no USB3).
- **D-Note:** the USBx_DRVVBUS external pull-down is DNI to allow deep-sleep wake. Populate it if wake is not used.

### 3.3 HDMI (p.43)

- **Transmitter:** **SiI9022ACNU** (Lattice/Silicon Image, QFN72, U10) fed from **VOUT0 24-bit RGB DPI**. That is DATA0–23, PCLK (0 Ω reflection option), DE, HSYNC, VSYNC, on VDDSHV3 at 3.3 V.
- **Control and audio:** I2C1 (addresses 0x3B/0x3F/0x62). Audio is I2S from McASP1 (muxed). MCLK is a 12.288 MHz oscillator (U7). Reset and interrupt go through the IO expander.
- **Supplies:** 1.2 V from VDD_1V2 (**the same rail as DDR4**) and 3.3 V IO. REXT_SWING is 7.5 k (changed for radiated-emission testing).
- **Companion:** **TPD12S016PWR** handles DDC/HPD level-shift, 5 V and ESD; it has internal pulls. The connector is FCI 10029449-001RLF.

### 3.4 OLDI / LVDS (p.39)

- **Connector:** J21, GCT FFC2A32-40-T, 40-pin 0.5 mm FPC.
- **Signals:** dual-channel OLDI0. CH1 and CH2 each carry A0-A3 + CLK, i.e. the SoC OLDI0_A0-A7 + CLK0/CLK1.
- **Panel interface:** I2C0 for touch, TS_INT# (pull-up to 3.3 V), and OLDI_RESETn (AND of GPIO_TS_RSTn and RESETSTATz).
- **Power:** 3.3 V only, through FL10 with a 1 µF bulk cap after the bead (D-Note). The shield goes to GND through FL21.
- **Analog supply:** VDDA_1P8_OLDI0 through a bead.
- The same sheet holds the UART1 FET mux (SN74CB3Q3257, U63) and the 1.8 V BT buffer (SN74AVC4T245, U3).

### 3.5 CSI camera (p.40)

- J19 is a TE 1-1734248-5, 15-pin 1.0 mm FPC (RPi camera pinout).
- It carries CSI0 RX lanes 0 and 1 plus the clock. **Only 2 of the 4 lanes are used.**
- Camera control: CSI_I2C2 through TCA9543A I2C switch channel 1 (U100, 0x71). CSI_GPIO1/2 come from the IO expander. 3.3 V supply.
- The scorecard shows CSI SI simulated and passing.

### 3.6 Audio (p.41, p.42)

- **Codec:** TLV320AIC3106IRGZT on I2C1 at 0x1B. Supplies: VCC_3V3_AUD (filtered 3.3 V) and VCC_1V8_AUD. MCLK is a 12.288 MHz oscillator (Kyocera KC2520Z, U59).
- **McASP1 is shared** between the codec, the HDMI transmitter and BT:
  - SN74CB3Q3257 FET mux (U65) between codec and HDMI.
  - TXB0104 1.8 V buffer (U60) to the M.2 BT PCM.
  - Selected by IO-expander lines and jumper J24.
- **Jack:** 3.5 mm 4-pole TRRS (mic + headphone), CUI SJ-43514-SMT.
- D-Notes: add a 10 k pull-down at the clock input, and add pulls on McASP lines that can float.

### 3.7 microSD (p.21)

- **Interface:** MMC1, 4-bit. **UHS-I** support needs LDO1 3.3/1.8 V switching (VSEL_SD) plus the TPS22996 dual switch, so card VDD and host IO supply can be power-cycled together.
- **Resets:** AND logic (SN74LVC1G11, U22) of RESETSTATz and MMC1_SD_EN.
- **Pull-ups:** 47 k to the **switched** IO rail. The MMC1_CLK pull-up is DNI.
- **Card detect:** MMC1_SDCD has a 100 Ω series resistor and a 47 k pull-up (R96 changed from 10 k).
- **ESD:** TPD6E001RSER (U15) and TPD2E001DRLR (U18).
- **Connector:** GCT MEM2051-00-195-00-A.

### 3.8 eMMC and OSPI (p.20, p.22)

- **eMMC:** MTFC32GAZAQHD-IT on MMC0, 8-bit, 1.8 V IO (VDDSHV4). VCC = 3.3 V, VCCQ = 1.8 V.
  - Reset: AND(GPIO_eMMC_RSTn, RESETSTATz) via U58. RST_n must be enabled in the eMMC's EXT_CSD.
  - 0 Ω reflection option on CLK.
  - External pulls are optional (the SoC enables internal pulls).
  - The p.6 power diagram still says MTFC16GAPALBH-AAT, which is stale.
- **OSPI:** S28HS512TGABHM010, 1.8 V, BGA24, 512 Mb octal Semper NOR.
  - Uses DQS. The external loopback-clock series resistors are DNI when DQS is used.
  - 0 R arrays select QSPI vs OSPI.
  - Reset: AND(GPIO_OSPI_RSTn, RESETSTATz) via U6.
  - D-Notes: do not put multiple devices on OSPI0. W35N01JWTBAG OSPI NAND is footprint-compatible.

### 3.9 Wi-Fi / BT M.2 (p.19, p.9)

- **Connector:** M.2 Key-E 2230 (J2), with standoff and screw.
- **Wi-Fi:** SDIO on MMC2 (1.8 V, VDDSHV6) with 47 k pull-ups. WLAN_EN = GPIO0_71, WLAN_IRQ = GPIO0_72. R6 pull-up was **re-mounted in rev B because the production M.2-CC3351 needs it**.
- **BT:**
  - UART1 4-wire at 1.8 V, muxed with an FT4232 channel.
  - PCM from McASP1 through TXB0104.
  - BT_EN = MCU_GPIO0_1 (3.3 V), level-shifted by TXS0104 (U2).
- **Slow clock:** 32.768 kHz from SoC WKUP_CLKOUT0 (A12 "HFOSC0_CLKOUT_32K"). The ASDK2 oscillator option (U1) is DNI.
- **Other:** USB D+/D− on the M.2 go to test points only. The 3.3 V supply is VCC_3V3_SYS.

### 3.10 Debug UART and JTAG (p.5, p.29–33)

- **USB-UART:** FT4232HL (U46), 12 MHz crystal (Y3), 93LC46B EEPROM (U87), micro-B (J15).
  - Its 4 channels go to MAIN_UART0 (Linux console), MAIN_UART1 (muxed with BT), MCU_UART0 (muxed with the MCU header via U17) and WKUP_UART0.
  - SN74AVC4T245 buffers sit between the FT4232 and the SoC.
  - The FT4232 is powered from its own USB VBUS via TPS73533 ("partial IO" support, rev B).
  - D-Note: follow SK-AM62P-LP for the latest FT4232 implementation.
- **JTAG:**
  - Onboard **XDS110**: TM4C1294NCPDTT3R, 16 MHz crystal, TPS79601, TPD4E004 ESD, micro-B J16.
  - Plus a **20-pin cTI header** (J17) for an external pod.
  - Mux/level-shift buffers: SN74AVC4T245 (U85, U88), SN74AVC2T244 (U83, U96) and others, selected by presence-detect (SEL_XDS).
  - TRSTn is pulled low.
  - D-Notes: follow SK-AM62P-LP for XDS110 updates, and add ESD on any external debug connector.

### 3.11 40-pin user expansion connector J3 (p.35). Raspberry-Pi-style pinout (from netlist)

| Pin | Net | Pin | Net |
|---|---|---|---|
| 1 | VCC3V3_EXP (switched, 500 mA) | 2 | VCC5V0_EXP (switched, 150 mA) |
| 3 | I2C2_SDA | 4 | VCC5V0_EXP |
| 5 | I2C2_SCL | 6 | GND |
| 7 | EXP_CLKOUT0 (DANTE option) | 8 | UART5_TXD |
| 9 | GND | 10 | UART5_RXD |
| 11 | SPI2_CS1 | 12 | SPI2_CS0 / EHRPWM0_A |
| 13 | GPIO0_42 | 14 | GND |
| 15 | GPIO1_22 | 16 | GPIO0_38 |
| 17 | VCC3V3_EXP | 18 | GPIO0_39 |
| 19 | SPI0_D0 | 20 | GND |
| 21 | SPI0_D1 | 22 | GPIO0_14 |
| 23 | SPI0_CLK | 24 | SPI0_CS0 |
| 25 | GND | 26 | SPI0_CS1 |
| 27 | **SoC I2C0_SDA** (HAT ID; same bus as PMIC and EEPROM) | 28 | **SoC I2C0_SCL** |
| 29 | GPIO0_36 | 30 | GND |
| 31 | GPIO0_33 | 32 | GPIO0_40 / PR0_ECAP0 |
| 33 | EHRPWM1_B | 34 | GND |
| 35 | SPI2_D1 / ECAP2 | 36 | SPI2_CS2 |
| 37 | GPIO0_41 | 38 | SPI2_D0 |
| **39** | **EXP_HAT_DETECT (RPi has GND here)** | 40 | SPI2_CLK |

Notes:
- The I2C2 bus goes through a TCA9543A switch (0x71) whose outputs are disabled by default.
- McASP0 pins are muxed as SPI2/ePWM.
- U111 (SN74LVC1G3157) and U112 (TXU0101) exist only for the DANTE daughter card and can be deleted.
- **The 5 V and 3.3 V pins are outputs; the header IO is not fail-safe.**
- **SBC design consideration:** PMIC and board-ID EEPROM share SoC I2C0 with HAT pins 27/28. A misbehaving HAT can disturb the PMIC bus. Consider isolating them.

### 3.12 Other headers

- **MCU header J9 (2×14, p.36):** MCU_SPI0, MCU_UART0 (with RTS/CTS), MCU_I2C0, MCU_MCAN0, MCU_GPIO0_15/16, MCU_RESETz, MCU_PORz, MCU_RESETSTATz and MCU_SAFETY_ERRORz.
- **PRU header J10 (2×10, p.34):** PR0_PRU0_GPO0-7, I2C0, PRU_DETECT, PRU_RESETz, PRU_INTn and switched 3.3 V.

### 3.13 GPIO expanders, EEPROM, sensors (p.9, p.23, p.41)

- **TCA6424ARGJR (U70, I2C1 0x22).** 24 bits:
  - PHY1/PHY2 resets, PRU detect, SD enable, VPP LDO enable.
  - Expansion 3V3/5V enables, HAT detect.
  - M.2 alert/wake, UART1 mux select, Wi-Fi level-translator enable.
  - HDMI reset/interrupt, CSI GPIO1/2, PRU 3V3 enable.
  - Test GPIO2, audio and BT buffer enable/direction, touch interrupt, user test LED 2.
- **TCA6408ARGTR (U110, I2C1 0x20):** WLAN SDIO reset, OLDI touch reset, audio reset, eMMC reset, McASP1 mux control, AUDIO_EXT_REFCLK_EN, EXP_CLKOUT0_SEL, USB-A OC.
- **A third TCA6424 (U74, 0x22)** sits on a separate test-automation bus and controls boot mode.
- **Board ID EEPROM:** AT24C512C at **0x51 on I2C0**. TI's U-Boot board detection reads it; decide whether to keep a compatible EEPROM for SDK board detection.
- **Temperature:** TMP100 at 0x48 (SoC) and 0x49 (DDR).
- D-Note p.41: if the IO expanders are optimized away, re-assign those signals to SoC GPIOs.

### 3.14 Boot mode (p.28, p.34)

- **Configuration:** 16 BOOTMODE pins (shared with GPMC AD lines). Two 8-position DIP switches (SW1: BMODE0-7, SW2: BMODE8-15) with 1 k pull-up (switch ON = 1) and 100 k pull-down per pin.
- **Isolation buffers:** 2× SN74AVC8T245 (U73, U75), enabled by BOOTMODEON (AND of RESETSTATz and TEST_GPIO3) so the alternate functions are isolated after latch. Jumper J14 enables the SYSBOOT buffer.
- **Supported boot sources:** OSPI, MMC1-SD, UART, eMMC, USB0 DFU, and a backup boot option.
- **D-Notes for a custom board:**
  - Buffers and DIP switches are optional. Use pull-up/pull-down resistors with provision for both on configurable bits.
  - Never leave a bootmode pin open, including reserved pins.
  - Don't short several bootmode pins together, and don't tie them directly to rails. Use about 10 k per pin.
  - If DIP switches are used, use 47 k / 1–2 k dividers and consider ESD.
  - Connect pull-ups to SoC_DVDD3V3 (VCC_3V3_SYS) when test automation is not used.
  - Add a 0 R in series where a bootmode pin is used for an alternate function.

### 3.15 Clocks (p.34, p.36, p.44, p.26)

- **MCU_OSC0 (25 MHz):** driven as LVCMOS from the U53 oscillator through LMK1C1103 (SoC_CLKIN). XO is grounded when an external clock is used.
  - The crystal option Y4 (ABM11W-25.0000MHZ-8-D1X-T3, 13 pF caps, updated in rev B) is **DNI**.
  - D-Note: the recommended oscillator is **LMK6CE02500DDLFT**. If using a crystal, connect it directly to XI/XO with no series/parallel R.
  - Only 25 MHz is supported.
- **WKUP_LFOSC0:** 32.768 kHz crystal Y1 (ECS-.327-9-34QCS-TR, 9 pF load). If LFOSC0 is unused, ground XI through 0 R.
- **Other clocks:**
  - 12.288 MHz oscillators U59 (codec) and U7 (HDMI audio).
  - 12 MHz crystal Y3 (FT4232).
  - 16 MHz crystal Y2 (XDS110).
  - EXT_REFCLK1 (A18) is used as CLKOUT0 to the expansion header.
- **Observation clocks:** OBSCLK (B16, T25) and MCU_OBSCLK (B8). Add test points with isolation (D-Note p.4).

### 3.16 LEDs / buttons

- **LEDs:**
  - TPIC2810D (WKUP_I2C0 0x60) drives 8 LEDs: 4 green, 2 red, 2 amber (LD2–LD9).
  - User LED 1 on SOC GPIO1_49; user LED 2 on IO-expander P27.
  - Power/VBUS indication LEDs (LD10, LD12, LD16, LD17, LD1, LD11) and debug-bridge LEDs (LD13–LD15).
- **Buttons:** SW3 warm reset, SW4 user interrupt (MCU_GPIO0_15), SW5 PMIC on/off (PB). SW1/SW2 are the boot DIPs.

### 3.17 ESD protection (summary)

| Location | Part(s) |
|---|---|
| Type-C VBUS | TVS2200 |
| Type-C CC | TPD1E01B04 ×4 |
| USB0 D+/D− | ESD122 |
| USB-A | TPD4S012 |
| HDMI | TPD12S016 |
| SD card | TPD6E001 + TPD2E001 |
| FT4232 USB | TPD2E001 + TPD1E10B06 |
| XDS110 USB | TPD4E004 + TPD1E10B06 |
| Jumper headers J25/J26 | TPD1E10B06 (D16/D17, added rev B) |
| Push buttons | TPD1E10B06 (D12/D13) |
| PMIC button | TPD1E10B06 (D15) |

Not protected:
- **Ethernet:** relies on the magnetics.
- **40-pin header, CSI and OLDI:** no TVS.

---

## 4. Impact of using the OSD62x-PM (OSD6254-1G) SiP

**Removed or absorbed by the SiP:**
- **DDR4 device and routing.**
  - The U29 DDR4 device and all DDR0 routing (fly-by-free point-to-point x16) are gone.
  - Also gone: the DDR_VREFCA divider and its 4 caps, the ZQ resistor, the DDR_RESET/ALERT/TEN pulls, the DDR_VPP bead (FL23) and its caps, and the DDR-side VDD_DDR4 decoupling (about 23 caps on this net).
  - The DDR4 SI/PDN simulation (scorecard) is no longer the board designer's job.
  - Memory drops from 2 GB to **1 GB**.
- **SoC decoupling (p.16–17).** Very likely reduced because Octavo integrates "passives".
  - The SK has about 20 caps on VDD_CORE, 8 on VDDR_CORE, ≈3 per VDDA_* rail, plus the CAP_VDDSx caps.
  - **Confirm in the OSD62x-PM datasheet which caps and beads are internal.** Bulk caps and the PMIC output caps stay external.
- **DDR-related monitoring (optional):** TMP100 #2 (DDR, 0x49) and INA231 on VDD_DDR4.

**Still needed outside the SiP:**
- **TPS65219 PMIC.** TPS6521904 matches: DDR4, VDD_CORE 0.85 V, 3.3 V or 5 V VSYS. Confirm Octavo's recommended OPN; the OSD62PM-BRK uses a TPS65219.
- **BUCK3 1.2 V** still feeds the SiP's DDR (VDDS_DDR plus DDR4 VDD/VDDQ).
- **LDO4 2.5 V** is still required for the **internal DDR4 VPP**. Verify the SiP exposes a VPP/2V5 ball. If no Ethernet PHY uses 2.5 V, LDO4's load is just DDR VPP.
- **VDDR_CORE strap:** keep VDDR_CORE = VDD_CORE through 0 Ω at 0.85 V, or route LDO2 to VDDR_CORE if you choose a 0.75 V-core NVM. Check whether the SiP ties these internally.
- **Other SoC support circuits still needed:**
  - 25 MHz MCU_OSC0 source and 32.768 kHz crystal (unless the SiP integrates them; the overview says passives only).
  - VPP 1.8 V eFuse LDO (only if eFuse programming or secure boot keys are needed in the field).
  - VMON_VSYS divider.
  - BOOTMODE resistors.
  - All reset/AND logic and every peripheral block.
- **Ball map:** IO-domain rails (VDDSHV0-6, MCU, CANUART) are presumably all brought out on SiP balls. Plan the IO voltages per §2.4.

**PCB implications:**
- **Layer count and impedances.** The SK's 10-layer, 40 Ω SE / 80 Ω diff structures were driven mainly by DDR4 plus the 0.5 mm ALW fan-out. With the SiP, only 50 Ω SE, 90 Ω (USB) and 100 Ω (Ethernet MDI, HDMI TMDS, CSI, OLDI) controlled impedances remain. 6–8 layers may be feasible.
- **Fan-out risk.** The SiP is a **full 500-ball 0.5 mm array**. The SK used only 8-mil-drill / 18-mil-pad through-vias; the AM62 ALW has via-channel depopulation designed for that. **Check Octavo's OSD62x-PM layout guide** for whether it needs via-in-pad or laser microvias (HDI). That can dominate PCB cost and the stackup decision.

**SK features that are EVM-only and candidates for removal on an SBC:**
- **Test automation:** p.27/p.30, J23, U42/U106/U107 I2C buffers, U74 TCA6424 bootmode expander, U73/U75 bootmode buffers, U43.
- **On-board XDS110** (p.5, p.29): keep a cTI-20 or Tag-Connect JTAG footprint plus ESD instead.
- **INA231 current monitors and shunts** (p.14). The rail names change across shunts; see D-Note p.14.
- **DANTE support** (U111, U112), the MCU header and the PRU header.
- **FT4232HL:** replace with a single-channel bridge or a 3-pin UART0 header.
- **TPS65988 dual-port PD:** a single sink-only PD controller may suffice. If only one RGMII PHY is used, a crystal can replace the LMK1C1103 clock buffer.
- **LM61460 6 A buck:** can be downsized once the load budget shrinks (no XDS, test automation or second PHY).
- **SiI9022A HDMI transmitter:** legacy Silicon Image / Lattice part; check availability (see §7) or consider an OLDI→HDMI or DPI→HDMI alternative.

---

## 5. PCB stackup (stackup PDF, FAB drawing, .alg header, IDF)

- **10 layers.** Finished thickness 0.062" ± 10%: 61.94 mil without mask and 63.94 mil with mask (Polar); .alg reports 62.44 mil.
- **Material:** Iteq **IT180A**, Tg 170, Dk 3.79–4.45.
- **Fabrication:** IPC-6012 Class 2, **ENIG**, green LPI mask.
- **Board:** 85.0 × 150.1 mm. Min trace/space **3.2 / 3.2 mil**.

| Layer | Name (.alg) | Use | Cu (Polar processed) | Dielectric below |
|---|---|---|---|---|
| L1 | TOP | Signal + components | 12 µm foil + plating = 1.85 mil (FAB: 1 oz finished) | 2× 106 prepreg = 3.56 mil (Dk 3.79) |
| L2 | L02_GND1 | GND plane | 1.26 mil (1 oz) | 4 mil core (Dk 4.40) |
| L3 | L03_SIG1 | Inner signal (stripline) | 1.26 | 2× 2113 prepreg = 6.60 mil (Dk 4.13) |
| L4 | L04_GND2 | GND plane | 1.26 | 5 mil core (Dk 4.21) |
| L5 | L05_PWR1 | Power plane | 1.26 | 106 + 7628 + 106 prepreg = 9.82 mil |
| L6 | L06_PWR2 | Power plane | 1.26 | 5 mil core |
| L7 | L07_GND3 | GND plane | 1.26 | 2× 2113 = 6.62 mil |
| L8 | L08_SIG2 | Inner signal (stripline) | 1.26 | 4 mil core |
| L9 | L09_GND4 | GND plane | 1.26 | 2× 106 = 3.56 mil |
| L10 | BOTTOM | Signal + components | 1.85 | — |

**Impedance targets** (Polar, ±10%; widths and spaces in mil):

| Target | Outer L1/L10 (ref L2/L9) | Inner L3/L8 (ref L2+L4 / L7+L9) | Likely use |
|---|---|---|---|
| 40 Ω SE | 9.05 | 5.80 | DDR4 address/command/data |
| 50 Ω SE | 5.80 | 3.60 | General: RGMII, SDIO, OSPI, DPI |
| 80 Ω diff | 6.02 / 4.80 | 4.20 / 4.30 | DDR4 CK/DQS |
| 90 Ω diff | 4.20 / 4.40 | 3.70 / 6.00 | USB2 |
| 100 Ω diff | 4.25 / 7.15 | 3.20 / 7.50 | Ethernet MDI, HDMI TMDS, CSI-2, OLDI |
| 120 Ω diff | 4.10 / 5.75, referenced to L3 (L2 voided); L10 refs L8 | — | Not labeled |
| 50 Ω coplanar with ground | 16 w / 14 gap, ref L3 (L1 only) | — | Not labeled; probably RF or a specific net |

The FAB drawing table repeats these, with some cell offsets in the text.

**Vias:**
- **Only one via padstack: VIA18D8, an 8 mil drill / 18 mil pad through-via spanning L1–L10.** About 2768 vias.
- **No blind, buried or laser microvias.**
- Vias are resin-filled and covered with solder mask. FAB note 17 says "**via on pad shall be Type-VI filled**", so filled via-in-pad is allowed where used.
- Teardrops on all layers.
- Note: the stackup file name says "Proc142A" but the internal stack name is PROC114E3 (original SK-AM62). The same stackup carries through 142A and 142B.

**Simulation scorecard (PROC142A):** OLDI, DDR4, CSI, VDD_CORE PDN and LDO decap (CAP_VDDSx) were all completed and passed. With the SiP, DDR4 drops out, but CSI, OLDI and core-PDN still need checking on the new board.

---

## 6. Design-update notes and errata to heed

**From the PROC142A readme:**
- Use the **"…With_Design_Updates..Notes_V1.0"** schematic for reuse.
- The plain `PROC142A(002)_sch` matches the shipped SK and its layout, but it contains known component-value and mounting errors. **Do not copy it.**
- Track TI E2E FAQ 1332316 ("design and review notes for reuse of SK-AM62B-P1 schematics") for updates.

**Rev A → B / design-update changes** (p.2 rev history, plus the PROC142A1 design-update rev history):
- **PMIC NVM:** TPS6521903 → **TPS6521904** (0.85 V core). R699 mounted (VDDR_CORE from VDD_CORE), R123 DNI. The PMIC_STBY link from the SoC was removed.
- **Memory parts:** DDR4 MT40A1G16KD → **MT40A1G16TB-062E IT:F**. eMMC 16 GB → **MTFC32GAZAQHD-IT**.
- **Open-drain I2C and EXTINTn RC slew limiters:** MCU_I2C0, WKUP_I2C0 and EXTINTn now use **62 Ω + 47 pF** (were 620 Ω + 10 pF). These open-drain fail-safe buffers have a slew-rate spec when pulled to 3.3 V. The emulated-open-drain I2C0/1 use a 47 Ω series resistor for fall time.
- **SD card:** U13 changed to a **dual-channel load switch** (SD VDD plus a switched VDDSHV5 IO supply, needed for UHS-I).
- **Low power and partial IO:** U113 LDO added for **VDD_CANUART** (partial-IO / low-power). FT4232 partial-IO buffering and its own USB-powered LDO.
- **USB-A:** U34 changed to TPS2051BD; **TPD4S012 USB ESD** (U114) added.
- **Clocks:** Y4 crystal changed to ABM11W-25.0000MHZ-8-D1X-T3 with 13 pF caps (still DNI; oscillator used).
- **Wi-Fi:** R6 (WLAN IRQ pull-up) re-mounted for the production M.2-CC3351.
- **Other value changes:**
  - C232 (VDD_1V2) 22 µF → 4.7 µF.
  - R96 (SDCD pull-up) 10 k → 47 k.
  - R304 (OSPI_CS pull-up) 47 k → 10 k.
  - R330 (MDIO pull-up) 1.5 k → 2.2 k.
  - R614/R617 1 k → 470 Ω; R88/R188 220 Ω → 470 Ω.
  - Several pull resistors relaxed from 1% to 5%.
- **Extra ESD and pulls:** ESD added on jumper headers. Pull-downs added on the AUDIO_EXT_REFCLK and EXP_CLKOUT0 lines.
- **From the 142A update:**
  - HDMI REXT_SWING 7.5 k.
  - 2× 47 µF added on VCC_5V0; C415 → 4.7 µF.
  - 22 pF across the VMON divider.
  - DNI R222, R650, C305, C303, C156, Q2 and Y4.
  - Many decap value corrections, e.g. C75/C79 (LFOSC load) 9 pF → 18 pF.

**Key D-Notes (design rules) to carry into the new design:**
1. **PMIC:**
   - Separate bulk caps per DC/DC input, plus 0.1 µF.
   - Tie buck feedback **after** the output bulk caps (CAD note).
   - Add 0 Ω or a jumper at buck outputs on pre-production boards.
   - Follow the PMIC review checklist (p.13).
2. **VDD_CORE and VDDR_CORE:** use the same source at 0.85 V. Never change the core voltage after reset. After a core-off, ramp all rails below 300 mV before restart (p.14–15).
3. **VPP (eFuse):**
   - Use a fast-transient LDO, not a load switch or FET. Use a low-inductance path to the VPP pin.
   - Enable it only when programming, under GPIO control.
   - Never tie 1.8 V permanently to VPP (p.12, p.15).
   - Alternative LDO: TPS7A21-Q1.
4. **VMON_VSYS:** use it as an input power-fail monitor, with the threshold well below nominal (p.15).
5. **IO slew:** the 3.3 V IO supply load switch needs a CT cap (SoC IO supply slew-rate spec, p.13).
6. **MCU_PORz:**
   - Drive from a fast logic gate, not a slow open-drain PGOOD.
   - 22 pF glitch filter.
   - Slew requirements apply (p.44).
7. **Warm-reset inputs:** Schmitt-trigger debounce for buttons/RC, plus a 22 pF glitch filter (p.45).
8. **Errata i2407:** do not rely on MCU_RESETSTATz when MCU_RESETz is asserted (p.45).
9. **LVCMOS IO (p.17):**
   - Most SoC IOs are **not fail-safe**, so drive no inputs before the supplies ramp. This applies to the expansion, PRU and MCU headers.
   - Inputs have minimum slew-rate specs.
   - IO buffers are off during reset, so add pulls at the attached-device inputs.
   - Any trace that is not actively driven needs a pull.
   - Leave unused IOs unconnected with the default PADCONFIG.
10. **Drive strength:** do not change it from default; timing closure assumes the default (p.4).
11. **I2C pull-ups:** pull up the open-drain I2C (MCU_I2C0, WKUP_I2C0) even if unused, with an RC slew limiter. EXTINTn also needs a pull-up and RC (p.8, p.34, p.36, p.44).
12. **Peripheral resets:** use AND(RESETSTATz, GPIO) so a single peripheral can be reset. Watch IO-level mismatch in the AND gates, which can cause leakage and residual voltage (p.20, p.22, p.24).
13. **eMMC:** enable RST_n in the eMMC. 47 k pull-ups are good practice. Pull-downs on clocks are intentional (p.20).
14. **SD:** UHS-I needs both card power cycling and IO-supply switching done together. Pull-ups go to the switched rail. 100 Ω series on SDCD (p.21).
15. **OSPI:**
   - Only one device on OSPI0.
   - Prefer a QSPI/OSPI device with a reset pin.
   - DQS pull-down near the SoC.
   - Place the loopback resistor R52 near the LBCLK pin. Use a tripad for R53/R320 to avoid stubs (p.22).
16. **DDR (moot with the SiP):** DQ swap within a byte is allowed. Single-device DDR4 needs no VTT. BG1 and NC pins are reserved for expansion (p.18).
17. **Ethernet:** follow the DP83867 EVM for caps and magnetics, and follow the 2-supply vs 3-supply power-sequence requirements. The PHY XI amplitude is 1.8 V. Add series-R provision on RX at the PHY and on TX at the SoC (p.24–26).
18. **Clocks:**
   - The 25 MHz crystal connects directly to XI/XO; no R is needed because of AGC. Match SoC and PHY crystal specs.
   - Only 25 MHz is validated for MCU_OSC0.
   - Ground LFOSC0 XI through 0 R if unused.
   - Change only the BP_C, PD_C and LFXOSC_TRIM bits (p.34, p.36).
19. **CLKOUT:** route point-to-point only; use a fan-out buffer for multiple loads (p.44).
20. **USB:** leave the DRVVBUS pull-down DNI if deep-sleep wake is needed. Follow the datasheet VBUS-divider guidelines. Provide CMC bypass provision. If USB is unused, ground the USB supplies per pin connectivity (p.15, p.38).
21. **CSI0 unused:** connect the supplies per the pin-connectivity table (p.15).
22. **Capacitors:** use ESR < 1 Ω, loop inductance < 2.5 nH, and 0201 where possible (p.15). On CAP_VDDSx, place 0.1 µF at the SoC pins.
23. **Boot mode:** see §3.14.
24. **Debug:** add ESD on external JTAG/debug connectors; keep TRSTn pulled low (p.32).

---

## 7. BOM (PROC142B(002)_BOM.xlsx)

**Totals:**
- *Assembly_BOM*: **235 line items**. 193 populated lines and 42 DNI lines. **1,226 placed parts**: 476 capacitors, 545 resistors, about 110 IC/oscillator/crystal/MOSFET lines' worth of parts, and 95 other. 59 IC line items.
- **About 608 placements are 0201.** This matters for assembly-house capability.
- *All_Parts_BOM*: 216 lines including DNI parts. 1,473 parts if everything were fitted.
- Columns: Item, Qty, Mistral P/N, RefDes, Value, Description, Mfr, Mfr P/N, Footprint. **There are no price, stock or lead-time columns**, so the cost and lead-time ranking below is an engineering estimate.

**Highest-cost or supply-risk items (estimated):**

| Part | Ref | Why |
|---|---|---|
| AM6254ATCGGAALW | U12 | SoC; replaced by the OSD6254 SiP, which carries its own SiP pricing and pre-release availability risk |
| MT40A1G16TB-062E IT:F (2 GB DDR4) | U29 | Micron DDR4 x16 lifecycle and allocation risk; eliminated by the SiP |
| MTFC32GAZAQHD-IT (32 GB eMMC) | U28 | Micron eMMC generations turn over quickly; check lifecycle and alternates |
| S28HS512TGABHM010 (Infineon Semper octal NOR) | U9 | Premium-priced flash |
| SiI9022ACNU | U10 | Legacy Silicon Image/Lattice HDMI TX; **lifecycle and availability risk** |
| TPS65988DHRSHR + W25Q80 | U68, U39 | Dual-port PD controller; needs a configuration image |
| TM4C1294NCPDTT3R | U45 | 128-TQFP MCU for the XDS110; EVM-only cost |
| FT4232HL | U46 | Quad UART bridge; cost |
| DP83867IRRGZ ×2 | U49, U51 | Industrial gigabit PHYs |
| TLV320AIC3106IRGZT | U66 | — |
| TPS6521904RHBR | U14 | Specific NVM OPN; ensure availability of this exact suffix |
| Automotive-grade power parts | U67 (LM61460-Q1), U13 (TPS22996H-Q1) | Overkill for an SBC |
| Coilcraft inductors | L12 (XAL6060-472MEB), L13 (XFL4020-152MEB) | — |
| Murata DFE201612E-R47M | L5, L7, L8 | — |
| Connectors | — | TE 2199119-4 M.2-E, Molex 2012670005 USB-C ×2, FCI 10029449-001RLF HDMI, LINK-PP LPJG16314A4NL RJ45-with-magnetics ×2 (single-source Chinese vendor), GCT FFC2A32-40-T, Hirose FH12A-40S-0.5SH(55), Samtec FTR-110-51-S-D-06, TE 1-1734248-5, GCT MEM2051 |
| Vishay 293D 150 µF tantalum | C371 | — |

The M.2-CC3351 Wi-Fi module is **not on the BOM**; it is sold separately.

---

## 8. Open items to verify for the OSD6254 design

1. **OSD62x-PM datasheet:**
   - Which supplies are exposed: separate VDDR_CORE? VPP_DDR (2.5 V)? VDDS_DDR?
   - Which decoupling is internal.
   - Whether MCU_OSC0 / LFOSC are external (assumed yes).
   - Ball-map IO domains.
2. **Octavo-recommended TPS65219 OPN and sequence:** is TPS6521904 OK, and is any VDDR_CORE / LDO2 change needed? Also EN vs PB mode and first-supply-detection behavior from the NVM (TRM SLVUCL1). On the SK, EN/PB/VSENSE is PB mode with SW5.
3. **Octavo PCB fan-out rules** for the 500-ball 0.5 mm array: via-in-pad, HDI, minimum layers. Compare with the SK's through-via-only 10-layer stack.
4. **Software:** is a board-ID EEPROM at I2C0 0x51 wanted for TI SDK compatibility? Octavo's BSP may have its own scheme.
5. **Rail sharing:** decide whether to keep HDMI on VDD_1V2 (shared with DDR) or give the HDMI bridge its own rail.
6. **Boot-mode defaults:** settle the SBC's default boot order (e.g. SD vs eMMC vs OSPI vs USB DFU) and the bootmode resistor straps. The SK's DIP defaults are in user's guide SPRUJ40; they are not on the schematic.
