# Sheet contract

Every schematic sheet is a Python module. Several people or agents write sheets in parallel, and they connect **only by net name**. This file fixes those names and who owns which file. If you need a change here, ask; don't work around it.

## Ownership

| Sheet module (`sheets/`) | Symbol module (`symlib/`) | Content |
|---|---|---|
| `s01_power_input.py` | `power_input.py` | USB-C #1 (PD power + USB0 data), TVS, CC ESD, TPS25730, LM61460 3.3 V, TPS63070 5 V |
| `s02_pmic.py` | (in `symbols.py`) | PMIC, 3.3 V IO switch, VPP LDO, PHY 1.0 V |
| `s03_sip_power.py` | (in `symbols.py`) | SiP supplies, beads, decoupling, VMON. |
| `s04_sip_gnd_nc.py` | (in `symbols.py`) | SiP VSS and NC/RSVD balls. |
| `s05_sip_io.py` | (in `symbols.py`) | SiP signal balls, generated from `data/pinmux_allocation.csv`. |
| `s06_clock_reset_boot.py` | `clock_reset.py` | 25 MHz oscillator, 32.768 kHz crystal, MCU_PORz logic, reset/user buttons, BOOTMODE straps + DIP |
| `s07_storage.py` | `storage.py` | eMMC-module connector + its power, microSD + TPS22996 dual switch + ESD |
| `s08_ethernet.py` | `ethernet.py` | DP83867IS, 25 MHz crystal, straps, RJ45 |
| `s09_usb.py` | `usb.py` | USB0 choke/ESD/VBUS divider, CH335F hub, USB-A ×2 with TPS2051B switches |
| `s10_hdmi.py` | `av.py` | TFP410, TPD12S016, HDMI-A connector |
| `s11_audio.py` | `av.py` | TLV320AIC3104, 12.288 MHz oscillator, TRRS jack, I2C1 pull-ups |
| `s12_camera.py` | `av.py` | 15-pin CSI FPC |
| `s13_wireless.py` | `wireless.py` | M.2 Key-E socket, standoff |
| `s14_expansion.py` | `debug_io.py` | 40-pin header, HAT-ID EEPROM, series resistors, header I2C pull-ups |
| `s15_debug.py` | `debug_io.py` | FT4232HL, EEPROM, crystal, LDO, debug USB-C, isolation buffers, Tag-Connect TC2070 |
| `s16_misc.py` | `misc.py` | Board-ID EEPROM, TMP102, I2C0 pull-ups, LEDs, mounting holes |

**Do not edit** `schgen.py`, `symbols.py`, `build.py`, `data/*.csv`, or any module you don't own. Shared symbols for gates, ESD and mounting holes are in `symbols.py`: `SN74LVC1G08`, `SN74LVC1G11`, `SN74LVC2G17`, `TPD4E05U06`, `MOUNTING_HOLE`, plus the generic `RES`, `CAP`, `CAP_POL`, `IND`, `FB`, `DIODE`, `ZENER`, `TVS_BI`, `LED`, `XTAL2`, `TESTPOINT` and `SW_PUSH`.

## Rails (fixed names)

| Net | Source | Use |
|---|---|---|
| `VBUS_USBC` | 01: USB-C #1 VBUS, raw 5–9 V | TPS25730 input, USB0 VBUS divider (09) |
| `VSYS_PD` | 01: TPS25730 output | LM61460 and TPS63070 inputs |
| `VCC_3V3_MAIN` | 01: LM61460, always on | PMIC VSYS/PVIN (02), TPS22965 input |
| `VCC_5V0` | 01: TPS63070 | USB-A switches (09), HDMI 5 V (10), header PTC (14), VMON (03) |
| `VCC_3V3_SYS` | 02: TPS22965, sequenced by PMIC GPO2 | **All** SoC-side 3.3 V peripherals and pull-ups |
| `VDD_1V8` | 02: PMIC Buck2 | 1.8 V IO peripherals: eMMC VCCQ, M.2 1.8 V, codec 1.8 V, oscillator |
| `VDDA_1V8` | 02: PMIC LDO3 | SoC analog only. Do not load. |
| `DDR4_VPP_2V5` | 02: PMIC LDO4 | PHY 2.5 V through its own bead on 08 (`VDDA_2V5_PHY`) |
| `VDD_1V0_PHY` | 02: TLV757 | PHY core |
| `VDD_SDIO_LDO1` | 02: PMIC LDO1, 3.3/1.8 V | Input of the SD IO switch on 07 only |
| `VDDSHV5_SD` | 07: TPS22996 channel 2 output | SoC VDDSHV5 (03) and SD pull-ups |
| `GND` | | Single ground |

New rails must look like `VCC_<V>_<USE>`, `VDD_<V>_<USE>` or `VBUS_<USE>`, for example `VDD_SD_3V3`, `VBUS_USBA1`, `VBUS_DBG`, `VCC_3V3_DBG` or `VCC_5V0_HDR`. Names in this form are drawn as power ports.

Only rails that are **on when the SoC is on** may pull up or drive SoC pins (`VCC_3V3_SYS`, `VDD_1V8`). Most AM62x IOs are not fail-safe.

## Cross-sheet nets (other than SoC nets)

| Net | Between | Notes |
|---|---|---|
| `USBC1_DP`, `USBC1_DM` | 01 connector → 09 | 09 puts the CMC + ESD122 between these and `USB0_DP/DM` |
| `PMIC_PGOOD` | 02 → 06 | PMIC nRSTOUT, 10 k pull-up already on 02. Feeds the MCU_PORz AND gate. |
| `PMIC_NINT` | 02 ↔ SoC | Already closed |
| `I2C0_SCL/SDA` | SoC ↔ 01 (TPS25730 0x20/0x21), 02 (PMIC 0x30), 16 (board ID 0x51, TMP102 0x48) | **Pull-ups on 16** (2.2 k to `VCC_3V3_SYS`, 47 Ω series per SK) |
| `I2C1_SCL/SDA` | SoC ↔ 10 (DDC via TPD12S016), 11 (codec 0x18) | **Pull-ups on 11** |
| `JTAG_SRST_N` | 15 → 06 | Optional system reset from the debugger, ANDed into MCU_PORz (SK: JTAG_EMU_RSTn) |

Declare any other cross-sheet net in your final report.

## SoC nets per sheet

Source: `data/pinmux_allocation.csv`. **Close every net assigned to your sheet. Do not rename any.** If an allocation looks wrong, for example a voltage-domain mismatch with your part, leave the CSV alone and report it.

| Function | Sheet | SoC nets (ball, IO domain) |
|---|---|---|
| eMMC (MMC0) | 07 | `EMMC_CLK` (J1, 1.8V), `EMMC_CMD` (K1, 1.8V), `EMMC_D0` (K2, 1.8V), `EMMC_D1` (L1, 1.8V), `EMMC_D2` (L2, 1.8V), `EMMC_D3` (M1, 1.8V), `EMMC_D4` (M2, 1.8V), `EMMC_D5` (N1, 1.8V), `EMMC_D6` (N2, 1.8V), `EMMC_D7` (P1, 1.8V), `EMMC_RST_N` (D25, 1.8V) |
| microSD (MMC1) | 07 | `SD_CLK` (B21, 3.3V/1.8V (switched, LDO1)), `SD_CMD` (A21, 3.3V/1.8V (switched, LDO1)), `SD_D0` (A22, 3.3V/1.8V (switched, LDO1)), `SD_D1` (B22, 3.3V/1.8V (switched, LDO1)), `SD_D2` (A20, 3.3V/1.8V (switched, LDO1)), `SD_D3` (B20, 3.3V/1.8V (switched, LDO1)), `SD_CD_N` (A23, 3.3V), `SD_VSEL` (B23, 3.3V), `SD_PWR_EN` (T23, 3.3V) |
| M.2 Wi-Fi (MMC2 SDIO) | 13 | `WL_SDIO_CLK` (D23, 1.8V), `WL_SDIO_CMD` (C23, 1.8V), `WL_SDIO_D0` (D22, 1.8V), `WL_SDIO_D1` (C22, 1.8V), `WL_SDIO_D2` (D21, 1.8V), `WL_SDIO_D3` (C21, 1.8V), `WLAN_EN` (D20, 1.8V), `WLAN_IRQ` (C20, 1.8V) |
| M.2 Bluetooth (UART6) | 13 | `BT_UART_RXD` (B26, 1.8V), `BT_UART_TXD` (B27, 1.8V), `BT_UART_RTS_N` (C27, 1.8V), `BT_UART_CTS_N` (C28, 1.8V), `BT_EN` (C25, 1.8V) |
| M.2 (32 kHz) | 13 | `M2_SUSCLK_32K` (C7, 3.3V) |
| Ethernet (RGMII1, DP83867) | 08 | `ETH_TXC` (U23, 3.3V), `ETH_TX_CTL` (V23, 3.3V), `ETH_TD0` (U25, 3.3V), `ETH_TD1` (V25, 3.3V), `ETH_TD2` (U24, 3.3V), `ETH_TD3` (V24, 3.3V), `ETH_RXC` (U20, 3.3V), `ETH_RX_CTL` (V20, 3.3V), `ETH_RD0` (U22, 3.3V), `ETH_RD1` (V22, 3.3V), `ETH_RD2` (U21, 3.3V), `ETH_RD3` (V21, 3.3V), `ETH_MDC` (V26, 3.3V), `ETH_MDIO` (U26, 3.3V), `ETH_PHY_RST_N` (R19, 3.3V), `ETH_PHY_INT_N` (T20, 3.3V) |
| HDMI bridge (VOUT0 DPI) | 10 | `DPI_D0` (P26, 3.3V), `DPI_D1` (N25, 3.3V), `DPI_D2` (N26, 3.3V), `DPI_D3` (M25, 3.3V), `DPI_D4` (M26, 3.3V), `DPI_D5` (U27, 3.3V), `DPI_D6` (T27, 3.3V), `DPI_D7` (T28, 3.3V), `DPI_D8` (R27, 3.3V), `DPI_D9` (R28, 3.3V), `DPI_D10` (P27, 3.3V), `DPI_D11` (P28, 3.3V), `DPI_D12` (N27, 3.3V), `DPI_D13` (N28, 3.3V), `DPI_D14` (M27, 3.3V), `DPI_D15` (M28, 3.3V), `DPI_D16` (L27, 3.3V), `DPI_D17` (L28, 3.3V), `DPI_D18` (K27, 3.3V), `DPI_D19` (K28, 3.3V), `DPI_D20` (J28, 3.3V), `DPI_D21` (J27, 3.3V), `DPI_D22` (H28, 3.3V), `DPI_D23` (H27, 3.3V), `DPI_PCLK` (T26, 3.3V), `DPI_DE` (R25, 3.3V), `DPI_HSYNC` (P25, 3.3V), `DPI_VSYNC` (R26, 3.3V) |
| HDMI (TFP410 control) | 10 | `HDMI_PD_N` (T22, 3.3V), `HDMI_HPD` (R21, 3.3V), `HDMI_CT_CP_HPD` (R20, 3.3V), `HDMI_LS_OE` (T21, 3.3V) |
| Audio codec (McASP1) | 11 | `AUD_BCLK` (J26, 3.3V), `AUD_FSYNC` (L25, 3.3V), `AUD_DOUT` (J25, 3.3V), `AUD_DIN` (H25, 3.3V), `AUD_MCLK` (G26, 3.3V) |
| Audio codec (control) | 11 | `AUD_RST_N` (T25, 3.3V) |
| I2C1 (HDMI + codec) | 11 (pull-ups) / 10 (DDC) | `I2C1_SCL` (A13, 3.3V), `I2C1_SDA` (B13, 3.3V) |
| Camera (CSI0 2-lane) | 12 | `CSI_CLK_P` (U17, D-PHY (1.8V analog)), `CSI_CLK_N` (V17, D-PHY (1.8V analog)), `CSI_D0_P` (U16, D-PHY (1.8V analog)), `CSI_D0_N` (V16, D-PHY (1.8V analog)), `CSI_D1_P` (U15, D-PHY (1.8V analog)), `CSI_D1_N` (V15, D-PHY (1.8V analog)) |
| Camera (I2C2) | 12 | `CAM_I2C_SCL` (E26, 3.3V), `CAM_I2C_SDA` (E25, 3.3V) |
| Camera (control) | 12 | `CAM_IO0` (R24, 3.3V), `CAM_IO1` (E1, 3.3V) |
| USB0 (device, USB-C #1) | 09 | `USB0_DP` (V12, USB2 PHY), `USB0_DM` (U12, USB2 PHY), `USB0_VBUS_DIV` (V11, USB2 PHY), `USB0_DRVVBUS` (C19, 3.3V) |
| USB1 (host, to hub) | 09 | `USB1_DP` (V10, USB2 PHY), `USB1_DM` (U10, USB2 PHY), `USB1_VBUS_DIV` (U11, USB2 PHY), `USB1_DRVVBUS` (D19, 3.3V), `USB_HUB_RST_N` (R22, 3.3V) |
| I2C0 (system) | 16 (pull-ups) / 02 / 01 | `I2C0_SCL` (A12, 3.3V), `I2C0_SDA` (B12, 3.3V) |
| PD controller | 01 | `PD_INT_N` (F1, 3.3V) |
| RPi 40-pin header | 14 | `HDR3_I2C1_SDA` (B7, 3.3V), `HDR5_I2C1_SCL` (A7, 3.3V), `HDR7_GPIO4_GPCLK` (D16, 3.3V), `HDR8_UART_TXD` (A11, 3.3V), `HDR10_UART_RXD` (B11, 3.3V), `HDR11_GPIO17` (G25, 3.3V), `HDR12_GPIO18_PCM_CLK` (A18, 3.3V), `HDR13_GPIO27` (F25, 3.3V), `HDR15_GPIO22` (A9, 3.3V), `HDR16_GPIO23` (L26, 3.3V), `HDR18_GPIO24` (K26, 3.3V), `HDR19_SPI0_MOSI` (D12, 3.3V), `HDR21_SPI0_MISO` (C12, 3.3V), `HDR22_GPIO25` (B9, 3.3V), `HDR23_SPI0_SCLK` (C11, 3.3V), `HDR24_SPI0_CE0_N` (D13, 3.3V), `HDR26_SPI0_CE1_N` (C13, 3.3V), `HDR27_ID_SD` (B8, 3.3V), `HDR28_ID_SC` (A8, 3.3V), `HDR29_GPIO5` (K25, 3.3V), `HDR31_GPIO6` (H26, 3.3V), `HDR32_GPIO12_PWM0` (A17, 3.3V), `HDR33_GPIO13_PWM1` (B17, 3.3V), `HDR35_GPIO19_PCM_FS` (B18, 3.3V), `HDR36_GPIO16` (E2, 3.3V), `HDR37_GPIO26` (F26, 3.3V), `HDR38_GPIO20_PCM_DIN` (A16, 3.3V), `HDR40_GPIO21_PCM_DOUT` (B16, 3.3V) |
| Debug (FT4232H) | 15 | `DBG_MAIN_UART0_RXD` (A10, 3.3V), `DBG_MAIN_UART0_TXD` (B10, 3.3V), `DBG_MAIN_UART1_RXD` (A19, 3.3V), `DBG_MAIN_UART1_TXD` (B19, 3.3V), `DBG_MCU_UART0_RXD` (B2, 3.3V), `DBG_MCU_UART0_TXD` (B3, 3.3V), `DBG_WKUP_UART0_RXD` (C2, 3.3V), `DBG_WKUP_UART0_TXD` (C1, 3.3V) |
| JTAG (Tag-Connect) | 15 | `JTAG_TCK` (D9, 3.3V), `JTAG_TMS` (C10, 3.3V), `JTAG_TDI` (D10, 3.3V), `JTAG_TDO` (D11, 3.3V), `JTAG_TRSTN` (C9, 3.3V), `EMU0` (D8, 3.3V), `EMU1` (C8, 3.3V) |
| System / reset / PMIC | 06 | `MCU_PORZ` (D6, 1.8V), `RESET_REQZ` (D17, 3.3V), `MCU_RESETZ` (C5, 3.3V), `PORZ_OUT` (D18, 3.3V), `RESETSTATZ` (C18, 3.3V), `MCU_RESETSTATZ` (C6, 3.3V), `MCU_ERRORN` (D7, 1.8V), `PMIC_NINT` (C17, 3.3V), `PMIC_LPM_EN0` (D5, 3.3V), `OSC_25M` (G1, 1.8V), `GND` (G2, 1.8V), `LFOSC_XI` (H1, 1.8V), `LFOSC_XO` (H2, 1.8V) |
| User IO | 06 (button) / 16 (LEDs) | `USER_LED1` (B6, 3.3V), `USER_LED2` (A6, 3.3V), `USER_BTN_N` (F2, 3.3V) |
| eFuse | 02 (done) | `VPP_EFUSE_EN` (A4, 3.3V) |
| BOOTMODE strap | 06 | `BOOTMODE00` (G28, 3.3V), `BOOTMODE01` (G27, 3.3V), `BOOTMODE02` (F28, 3.3V), `BOOTMODE03` (F27, 3.3V), `BOOTMODE04` (E28, 3.3V), `BOOTMODE05` (E27, 3.3V), `BOOTMODE06` (D28, 3.3V), `BOOTMODE07` (D27, 3.3V), `BOOTMODE08` (L27, 3.3V), `BOOTMODE09` (L28, 3.3V), `BOOTMODE10` (K27, 3.3V), `BOOTMODE11` (K28, 3.3V), `BOOTMODE12` (J28, 3.3V), `BOOTMODE13` (J27, 3.3V), `BOOTMODE14` (H28, 3.3V), `BOOTMODE15` (H27, 3.3V) |

BOOTMODE straps: `BOOTMODE00`–`BOOTMODE07` are strap-only nets. BOOTMODE08–15 are the nets `DPI_D16`–`DPI_D23`, shared with the HDMI data bus, so sheet 06 puts fixed 10 k straps on those nets with no DIP switch. The default strap value is 0x0643 (see `docs/research/pinmux-allocation.md`).

## Rules for every sheet

1. **Parts:** use the parts chosen in `docs/bom/APE-SBC_BOM_estimate.csv`. Set `comment=` to the value or MPN and pass `MPN=` and `Manufacturer=` parameters. If a BOM part is wrong for the circuit, pick an in-stock replacement (stock ≥ 10 boards at a real distributor) and report it.
2. **Pinouts:**
   - Download the manufacturer datasheet into a new scratch directory, not the repo. Build the symbol from its pin table.
   - Above each symbol, put the datasheet URL and table or page in a comment.
   - Include **every package pin** (NC, thermal pad, connector shell/mounting pins) so the footprint maps. Give a thermal pad the next free pin number and note it.
   - Connector numbering follows the manufacturer drawing.
3. **Circuits:**
   - Follow each IC datasheet's application section and the TI SK-AM62B-P1 schematic (`reference/1_PROC142B/1_SCHEMATIC/2_PDF_Standard/`; extracted text per page is in the scratchpad `txt/pNN.txt` if your brief says so), along with `docs/research/*.md` and `docs/research/bom/*.md`.
   - Include every decoupling cap, pull, strap, series resistor and ESD part.
   - Use pull-downs, not AND gates, to hold peripheral resets during SoC reset. AM62x pads turn off during reset.
4. **Designators:** sheet NN uses NN00–NN99 for every prefix, for example sheet 07 has U700, C700 and J700. Sheets 10, 11 and 12 use 1000–1099, 1100–1199 and 1200–1299.
5. **Layout:**
   - Sheet size: `style=7` (C, 22×17 in) or `8` (D, 34×22 in).
   - Use `Sheet.column()` for passives.
   - `python build.py check` must report **no geometry or layout problems** on your sheets, and none of your assigned SoC nets may remain single-node.
6. **Unused pins:**
   - `"NC"` (No-ERC marker) only where the datasheet says to leave a pin floating. Otherwise tie it as the datasheet says.
   - Nets that only go to a test point start with `TP_`.
7. **Notes:** add `sh.note(x, y, text)` for layout constraints, DNP options and open questions.
