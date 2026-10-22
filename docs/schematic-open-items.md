# Schematic v0.1: open items for review

The schematic is generated from `hardware/gen` (16 sheets, 729 placed parts, 451 nets, 65 footprints). `build.py check` passes: no single-node nets, no accidental connections, no overlapping parts. All 16 sheets are built in Altium AD26, and every pin lands on its wire (pin-map check). The PCB import matches the netlist: 720 footprints, 451 nets.

ERC has 0 fatal errors, 7 errors and 329 warnings, all expected:
- The 7 errors are floating inputs, and the 259 "unconnected" warnings are on pins deliberately left NC with a No-ERC marker. The 7 inputs are the unused DP83867 JTAG pins and codec MIC1 inputs. All 259 pins were checked against the generator's NC list.
- 66 nets have only passive or input pins, so they have no driver.
- 4 nets join an IO pin with an output or power pin: SoC pads driven by a peripheral, and MCU_OSC0_XO tied to GND for the LVCMOS oscillator.

On 2026-10-21 the whole design was reviewed:
- against the Octavo OSD62x-PM schematic checklist (rev 07/07/2025, all 129 items);
- pin by pin against each part's datasheet;
- every footprint against its manufacturer drawing.

Fixes from that review are listed at the end.

Priority: **A** = must resolve before layout, **B** = confirm at footprint/PCB stage, **C** = confirm at bring-up.

## Decisions for you

| # | Sheet | Question | Default in the schematic |
|---|---|---|---|
| A1 | 07 | eMMC-module connector GB042-34P is broker-only (see `docs/bom`). Buy from a broker, or solder an eMMC chip? | Connector, as decided |
| A2 | 09 | Switch each USB-A port's power separately? This would mean TPS2041B plus a buffer. | Both ports switched together from USB1_DRVVBUS |
| A3 | 13 | Wire the M.2 USB pins to hub port 3, so USB-Bluetooth cards work? (M2-CC3351 uses UART.) | Not connected |
| A4 | 13 | Route BT `UART_WAKE#` and `VIO_CFG` to spare 1.8 V GPIOs? | Test points only |
| A5 | 14 | Fit the on-board HAT-ID EEPROM? It would collide with a HAT's own EEPROM at 0x50. | DNP |
| A6 | 15 | The TI-14 Tag-Connect pinout has no reset pin. `JTAG_SRST_N` sits on pad 6, the key position, which TI XDS probes leave unconnected. A custom adapter is needed. | KEY pad, pulled up on sheet 06 |
| A11 | 01 | L100 (MWSA0603S-4R7MT) saturates at 9 A, below the LM61460 high-side current limit (10.3 A typ, 11.5 A max). The datasheet asks for Isat ≥ the limit. The part is molded powder with a soft saturation curve, and the regulator has hiccup protection. Bourns SRP7028A-4R7M (10 A) is still short of 11.5 A. | Accept (risk 6 in `docs/research/bom/power.md`) |
| A12 | 14, 12 | Checklist 62_ALL_7 asks for ESD protection on off-board connectors. The 28 header signals have only their 33 Ω series resistors, and the camera FPC has none. The Raspberry Pi has none on its header either. Header protection would take 7 × TPD4E05U06. | None |
| A13 | 07 | The SD card is not power-cycled on a warm or watchdog reset. RESETSTATz is low for about 162 µs, but card VDD takes about 0.53 ms to discharge, so it only dips to about 2.4 V. A UHS-I card left in 1.8 V signalling then fails ROM SD boot. The SK has the same topology. Fixes: reboot through the Linux vmmc regulator (software), route watchdog/ESM resets to the PMIC as a cold reset, or delay the SD power enable. | Software fix (vmmc); sheet note |
| A14 | 08 | HR911130A ties all four PHY-side centre taps together inside the jack. TI DP83867 Fig 9-2 wants them separate, each with its own 0.1 µF. Most MagJack designs accept this. The alternative is a jack or discrete magnetics with separate taps, as on the DP83867 EVM. | Accept |
| B1 | 11 | Headphone coupling caps: 47 µF gives a 211 Hz corner into 16 Ω. Fit 100–220 µF? | 47 µF |

## Footprint checks

The footprints are in `hardware/gen/fplib/`. Section 10 of `hardware/gen/README.md` lists what each one assumes. All 65 footprints were checked against their manufacturer drawings and compared pad by pad with the LCSC EasyEDA footprints; USB-C, HDMI, USB-A and TC2070 were also compared with KiCad. Where EasyEDA disagrees with the drawing, the library follows the drawing. Those cases: microSD shell tabs, TE FPC row pitch, USB-A contact rows, M.2 tab length, RJ45 LED holes.

| # | Part | Status |
|---|---|---|
| B2 | J100/J1500 USB-C (HRO TYPE-C-31-M-12) | Confirmed against the drawing, KiCad and EasyEDA |
| B3 | J1000 HDMI-A (XFCN) | Confirmed: pin 1 position backed by three sources |
| B4 | J1100 TRRS jack PJ-320DB | Confirmed from the drawing's schematic; the sheet wiring is CTIA |
| B5 | J1200 CSI FPC (TE) | Confirmed. Pick the cable type so conductor 1 lands on circuit 1. |
| B6 | J700/J701 GB042 | Confirmed by the Radxa eMMC module's own board export: socket rows 1–17 / 18–34, 34 opposite 1, no hold-downs. Face to face this gives the plug numbering used here. The same file fixes placement: J701's centre is 13.0 mm from J700's, on J700's 1–17 side, both turned the same way. |
| B7 | J702 microSD TF-01A | Footprint confirmed. **Still open:** the drawing does not show the card-detect polarity. The ROM needs SD_CD_N low with a card in. Check on a sample. |
| B8 | J900 dual USB-A (Bossie) | VBUS position confirmed (KiCad, EasyEDA). Lower port = front row is reasoned only; a swap would be harmless. |
| B9 | J1300 M.2 socket | Confirmed |
| B10 | J1400 header | Confirmed |
| B11 | SW602 DIP switch | Confirmed |
| B12 | All | Done: one name per package, every pad checked against its symbol pin by `build.py check` |
| B20 | J100, J1000 | Front silk lies 0.49 mm (USB-C) and 0.96 mm (HDMI) past the board edge. Cosmetic only. |
| B21 | Diodes, LEDs | Pad 1 = anode, matching the symbols (IPC puts the cathode on pad 1). Check D101–D103, D902 and LED1600–LED1603 rotation in the JLC placement preview. |
| B22 | U1 SiP | 0.20 mm paste apertures (area ratio 0.50). A `Paste_SiP` rule adds +0.03 mm in `pcbsetup.py`. |
| B23 | J700 GB042 | The 0.4 mm pitch leaves a 0.07 mm solder-mask web, so expect no mask between those pads. |

## Electrical items to confirm

| # | Sheet | Item |
|---|---|---|
| A8 | 01 | TPS25730 strap decoding is "firmware controlled": verify 5–9 V and 1.5/3 A on the EVM or the first boards. Its I2C address 0x20 collides with TCA64xx defaults (none on this board). |
| A9 | 06 | Ethernet boot puts 25 MHz on header **pin 7** (ball D16, CLKOUT0), because BOOTMODE bit 9 is fixed at 1. Booting from the eMMC UDA through MMCSD is unreachable; use the eMMC boot partition. |
| A10 | 07/08 | SD power-enable and PHY reset follow RESETSTATZ through resistors so the ROM can boot SD and Ethernet. R611 is now 1 kΩ to GND, which holds the net low against the PHY's 9 k internal pull-up while the pad is Hi-Z. Fallback: R816 DNP. |
| B13 | 06 | 25 MHz oscillator rise time: ≤ 7 ns at 15 pF specified, against ≤ 4 ns required at the SoC input. Confirm with ECS or measure. Alternative: TI LMK6CE025000. |
| B14 | 10 | TFP410 latches on the falling edge (ti-tfp410 default). Setup at 1080p60 is 1.12 ns against the TFP410's 1.2 ns. DNP straps R1012–R1016 can add 350 ps of de-skew (fit R1013, R1014, R1016; remove R1005), giving 1.47 ns setup and 1.87 ns hold. Decide at bring-up from a 1080p60 margin test. |
| B16 | 11 | AUDIO_EXT_REFCLK1 (G26) must be configured as an **input** to McASP1, because the 12.288 MHz oscillator drives it. Confirm in the TRM. |
| B17 | 11 | Codec supply order: VDD_1V8 comes up before 3.3 V, but the datasheet wants AVDD ≥ DVDD. The codec is held in reset as on the SK. |
| B18 | 01/09 | Total capacitance on VCC_5V0, including 2 × 150 µF USB-A bulk, must be ≤ 470 µF effective for the TPS63070 |
| B19 | 03/08 | Capacitance on the LDO4 (DDR4_VPP_2V5) rail must be ≤ 30 µF including the SiP's internal caps. About 14.5 µF is on the board. |
| C1 | 08 | PHY RESET_N low level with its ~9 k internal pull-up and R611: measure. |
| C2 | 15 | The FT4232 consoles go Hi-Z while the USB host suspends the bridge (PWREN# drives the buffers' OE# through R1530). For always-on consoles, remove R1530 and fit R1506. |
| C3 | 14 | The 5 V header pins stay live while the SoC is off. Only the 33 Ω resistors limit back-drive from a HAT into SoC pads. |
| C4 | 07 | eMMC reset is a GPIO with a pull-up only, so a warm reset does not reset the module (checklist 62_EMMC_9 allows it). The SK ANDs RESETSTATz with the GPIO. |
| C5 | 02 | Optional upgrades: a Buck1 inductor rated ≥ 7.4 A (TI recommendation; DFE252012F-R47M is 6.7 A, the SK uses 4.5 A), and a VMON divider of 40.2 k / 4.87 k (trip 3.97–4.47 V instead of 4.33–4.79 V). |
| C6 | 02/06 | nRSTOUT rises through 2.2 k (R201) into U601, which is slow for its input. Fit 1 k if the gate output chatters. |

Closed in this review: **A7** (TI SLVUCL1A confirms the TPS6521904 rail map, sequence and SD_VSEL polarity) and **B15** (the 1.3 A bead carries the TFP410's 250 mA).

## Fixed in the 2026-10-21 review

| Sheet | Change | Reason |
|---|---|---|
| 01, 02, 16 | R1620/R1621 47 Ω at the SoC's I2C0 balls. Every I2C0 device now sits on `I2C0_SCL_BUS`/`I2C0_SDA_BUS`. | SK p.44: emulated open-drain pad |
| 01 | C100 4.7 µF 25 V 0805 | TPS25730 CVBUS max 10 µF |
| 02 | R208 MODE/STBY, R209 MODE/RESET, R210 LPM_EN0 pull-ups | Pins left floating; Octavo 62_CONFIG_9 |
| 03 | FB310 from VDDA_1V8 feeds a new `VDDS_OSC0_1V8` rail (SiP VDDS_OSC0, U600, U601) | VDDS_OSC0 was on the noisy Buck2 rail; Octavo 62_POWER_4, 62_CLOCK_2 |
| 03 | C322/C324/C326/C328 4.7 µF → 1 µF | 32 µF on LDO3 exceeded its 30 µF slow-ramp limit |
| 03 | TP300–TP312 on 13 rails | Octavo 62_ALL_2 |
| 06 | R611 1 kΩ | See A10 |
| 07 | R732 SD CLK pull-down | Octavo checklist |
| 09 | R913 fitted (USB1_DRVVBUS pull-down) | TPS2051B EN floated while the SoC IO rail is off |
| 10 | R1012–R1016 de-skew straps (DNP) | See B14 |
| 11 | D1100–D1102 ESD at the jack | 62_ALL_7 |
| 13 | R1321 SDIO CLK series link, R1322/R1323 BT UART pull-ups | Octavo checklist |
| 14 | R1433 47 k UART5 RX pull-up | 62_UART_2 |
| 15 | R1530 links PWREN# to OE#; C1506 10 µF | PWREN# is a driven output (R1506 alone would short it); VREGOUT needs ≥ 3.3 µF effective |
| Footprints | QFN28 (CH335F) paste windows; silk clearance 0.20 mm; SiP paste rule | IPC-7525, JLC silk-to-mask rule |

## Software notes for the device tree

- `ti,vbus-divider` on both USB wrappers (09).
- McASP1 high-speed clock from AUDIO_EXT_REFCLK1 as an input (11).
- The TFP410 runs in strap mode, with PD# on `HDMI_PD_N` (10).
- CC3351 over SDIO (MMC2) + UART6 for Bluetooth. The card's reset is on WLAN_EN (W_DISABLE1#).
- PMIC at 0x30, TPS25730 at 0x20, TMP102 at 0x48 and the board-ID EEPROM at 0x51, all on I2C0.
- SD card: give MMC1 a `vmmc-supply` on the SD power-enable GPIO, so a reboot power-cycles the card (A13).
