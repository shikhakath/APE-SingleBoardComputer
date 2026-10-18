# Schematic v0.1: open items for review

The schematic is generated from `hardware/gen` (16 sheets, 687 designators, 443 nets). `build.py check` passes: no single-node nets, no accidental connections, no overlapping parts. **It has not been compiled in Altium yet.** These items came up while drawing the sheets and need a decision or a check.

Priority: **A** = must resolve before layout, **B** = confirm at footprint/PCB stage, **C** = confirm at bring-up.

## Decisions for you

| # | Sheet | Question | Default in the schematic |
|---|---|---|---|
| A1 | 07 | eMMC-module connector GB042-34P is broker-only (see `docs/bom`). Buy from a broker, or solder an eMMC chip? | Connector, as decided |
| A2 | 09 | Switch each USB-A port's power separately? This would mean TPS2041B plus a buffer. | Both ports switched together from USB1_DRVVBUS |
| A3 | 13 | Wire the M.2 USB pins to hub port 3, so USB-Bluetooth cards work? (M2-CC3351 uses UART.) | Not connected |
| A4 | 13 | Route BT `UART_WAKE#` and `VIO_CFG` to spare 1.8 V GPIOs? | Test points only |
| A5 | 14 | Fit the on-board HAT-ID EEPROM? It would collide with a HAT's own EEPROM at 0x50. | DNP |
| A6 | 15 | The TI-14 Tag-Connect pinout has no reset pin. `JTAG_SRST_N` sits on the KEY pad, which needs a custom adapter. | KEY pad, pulled up on sheet 06 |
| B1 | 11 | Headphone coupling caps: 47 µF gives a 211 Hz corner into 16 Ω. Fit 100–220 µF? | 47 µF |

## Footprint checks (manufacturer drawings without pad numbers)

| # | Part | Assumption to verify |
|---|---|---|
| B2 | J100/J1500 USB-C (HRO TYPE-C-31-M-12) | Pads named A1B12, A4B9, B4A9, B1A12 for the shared pads; shell pegs S1–S4 |
| B3 | J1000 HDMI-A (XFCN) | Standard HDMI order 1–19; shell legs 20–23 |
| B4 | J1100 TRRS jack PJ-320DB | 1 sleeve, 2 tip, 3 ring 1, 4 ring 2, 5 dummy (GND), CTIA |
| B5 | J1200 CSI FPC (TE) | Both pad rows of each circuit share one number |
| B6 | J700/J701 GB042 | Pins 1–34 agree across Radxa, ROCK 3A and ROCK64 documents. The hold-down pads (35–38 / 31–34) still need checking on a sample. |
| B7 | J702 microSD TF-01A | The "Cd" spring closes to the shell on insertion; the ROM needs SD_CD_N low with a card in |
| B8 | J900 dual USB-A (Bossie) | Pads 1–4 lower port, 5–8 upper, 9–12 shell |
| B9 | J1300 M.2 socket | SMT tabs numbered 76/77 |
| B10 | J1400 header | Raspberry Pi odd/even numbering |
| B11 | SW602 DIP switch | Position k = pads k and 9−k |
| B12 | All | Footprint names are inconsistent; for example, three names for the same 3225 crystal. Normalize them when the PcbLib is built. |

## Electrical items to confirm

| # | Sheet | Item |
|---|---|---|
| A7 | 02 | TPS6521904 rail map, sequence and SD_VSEL polarity against TI SLVUCL1 (not yet obtained) |
| A8 | 01 | TPS25730 strap decoding is "firmware controlled": verify 5–9 V and 1.5/3 A on the EVM or the first boards. Its I2C address 0x20 collides with TCA64xx defaults (none on this board). |
| A9 | 06 | Ethernet boot puts 25 MHz on header pin 12 (BOOTMODE bit 9 is fixed at 1). Booting from the eMMC UDA through MMCSD is unreachable; use the eMMC boot partition. |
| A10 | 07/08 | SD power-enable and PHY reset are tied to RESETSTATZ through resistors so the ROM can boot SD and Ethernet. Check that RESETSTATZ isn't lifted early by the PHY's internal pull-up. Fallback: R816 DNP. |
| B13 | 06 | 25 MHz oscillator rise time: ≤ 7 ns at 15 pF specified, against ≤ 4 ns required at the SoC input. Confirm with ECS or measure. |
| B14 | 10 | TFP410 strapped to latch on the falling edge (ti-tfp410 default). Confirm against the AM62x DPI output timing in the device tree. |
| B15 | 10 | BLM18KG601SN1D bead current rating was not checked against TFP410 PVDD/TVDD current |
| B16 | 11 | AUDIO_EXT_REFCLK1 (G26) must be configured as an **input** to McASP1, because the 12.288 MHz oscillator drives it. Confirm in the TRM. |
| B17 | 11 | Codec supply order: VDD_1V8 comes up before 3.3 V, but the datasheet wants AVDD ≥ DVDD. The codec is held in reset as on the SK. |
| B18 | 01/09 | Total capacitance on VCC_5V0, including 2 × 150 µF USB-A bulk, must be ≤ 470 µF effective for the TPS63070 |
| B19 | 03/08 | Capacitance on the LDO4 (DDR4_VPP_2V5) rail must be ≤ 30 µF including the SiP's internal caps. About 14.5 µF is on the board. |
| C1 | 08 | PHY RESET_N low level with its ~9 k internal pull-up: about 0.63 V worst case. Measure. |
| C2 | 15 | The FT4232 consoles go Hi-Z while the USB host suspends the bridge (PWREN# gating). R1506 DNP makes them always on. |
| C3 | 14 | The 5 V header pins stay live while the SoC is off. Only the 33 Ω resistors limit back-drive from a HAT into SoC pads. |

## Software notes for the device tree

- `ti,vbus-divider` on both USB wrappers (09).
- McASP1 high-speed clock from AUDIO_EXT_REFCLK1 as an input (11).
- The TFP410 runs in strap mode, with PD# on `HDMI_PD_N` (10).
- CC3351 over SDIO (MMC2) + UART6 for Bluetooth. The card's reset is on WLAN_EN (W_DISABLE1#).
- PMIC at 0x30, TPS25730 at 0x20, TMP102 at 0x48 and the board-ID EEPROM at 0x51, all on I2C0.
