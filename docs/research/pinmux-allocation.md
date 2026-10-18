# OSD6254-1G-IPM pinmux allocation: notes

Generated 2026-10-17. The ball list is `pinmux_allocation.csv`; this file explains the choices behind it.

Legend: **[C]** checked in a source. **[I]** my inference or judgement. **[?]** not verified, check before layout.

## 0. How the allocation was produced and checked

- **Pad data.** The AM62x pad, mux-mode and IO-domain data come from a table parse of the AM625 datasheet (SPRSP58C) Table 5-1, using `find_tables`. That gives 331 pads, each with its full mux list and POWER column.
- **Ball numbers.** Ball numbers are joined to pads through the Octavo Table 5-7 AMC-ball column. Every pad name matched. The join is pad name to ball number, using `osd6254_ballmap.csv`.
- **Validation.** The generator script (`bm/make_pinmux.py`) checks each row and found **0 errors**:
  - The signal exists on that pad at that mux mode.
  - No pad is used twice. Bootstrap rows are the only exception.
  - No peripheral signal (for example UART6_RXD) is muxed onto two pads.
- **Coverage.**
  - 174 signal pads are allocated.
  - 8 pads are BOOTMODE straps only (GPMC0_AD0–7).
  - 39 balls are unused: 20 OLDI0, 4 CSI0 lanes 2/3, and 15 spares (§9).
  - Total: 221, which equals every OSD signal ball.
- **IO-voltage plan.** All allocations follow DESIGN_PROPOSAL §6:

  | Rail | Voltage |
  |---|---|
  | VDDSHV0 | 3.3 V |
  | VDDSHV1 | 1.8 V |
  | VDDSHV2 | 3.3 V |
  | VDDSHV3 | 3.3 V |
  | VDDSHV4 | 1.8 V |
  | VDDSHV5 | switched |
  | VDDSHV6 | 1.8 V |
  | VDDSHV_MCU, VDDSHV_CANUART | 3.3 V |

  No ball needs a different bank voltage.

## 1. Peripheral instance map (one owner per instance)

| Instance | Use | Pads (ball) |
|---|---|---|
| MMC0 8-bit | eMMC module connector, 1.8 V | MMC0_* (J1, K1, K2, L1, L2, M1, M2, N1, N2, P1) |
| MMC1 4-bit | microSD UHS-I | MMC1_* (B21, A21, A22, B22, A20, B20) + MMC1_SDCD (A23, **VDDSHV0**) |
| MMC2 4-bit | M.2 Wi-Fi SDIO, 1.8 V | MMC2_* (D23, C23, D22, C22, D21, C21) |
| UART0 | FT4232 ch A: Linux console | A10, B10 |
| UART1 | FT4232 ch B: TIFS | MCASP0_AFSR (A19, m2), MCASP0_ACLKR (B19, m2) |
| MCU_UART0 | FT4232 ch C | B2, B3 |
| WKUP_UART0 | FT4232 ch D: DM | C2, C1 |
| UART5 | Header pins 8/10 | MCAN0_RX (A11, m1, TXD), MCAN0_TX (B11, m1, RXD). Same as SK and BRK. |
| **UART6** | **M.2 Bluetooth, 4-wire, 1.8 V** | OSPI0_D4 to D7 (B26, B27, C27, C28, m3) |
| I2C0 | System: PMIC 0x30, ID EEPROM, PD controller, TMP102 | A12, B12 |
| I2C1 | SiI9022A + audio codec | A13, B13 |
| I2C2 | Camera FPC | GPMC0_CSn2 (E26, m1), GPMC0_CSn3 (E25, m1) |
| MCU_I2C0 | Header pins 3/5 (RPi I2C1) | A7, B7 (fail-safe open-drain) |
| WKUP_I2C0 | Header pins 27/28 (HAT ID) | A8, B8 (fail-safe open-drain) |
| I2C3 | unused | |
| SPI0 | Header SPI0 (19/21/23/24/26) | D12, C12, C11, D13, C13 |
| McASP0 | Header PCM (12/35/38/40) | A18, B18, A16, B16 |
| McASP1 | Audio codec | GPMC0_BE0n_CLE (J26), WAIT0 (L25), WEn (J25), ADVn_ALE (H25), all m2. SK mapping. |
| McASP2 | HDMI I2S | RGMII2_TD3 (R20), TD2 (T21), RD2 (T24), all m2 |
| AUDIO_EXT_REFCLK1 | Codec MCLK | GPMC0_WPn (G26, m1) |
| AUDIO_EXT_REFCLK0 | HDMI MCLK (optional, DNP) | RGMII2_RD3 (R23, m2) |
| EHRPWM1 A/B | Header PWM0/PWM1 (pins 32/33) | MCASP0_AXR1 (A17, m6), MCASP0_AXR0 (B17, m6) |
| CLKOUT0 | Header pin 7 GPCLK0 | EXT_REFCLK1 (D16, m5). SK mapping. |
| CPSW RGMII1 + MDIO0 | DP83867 | U20–V25, U26, V26 |
| DSS VOUT0 | 24-bit DPI to SiI9022A | VOUT0_* + GPMC0_AD8–15 (m1) |
| CSI0 | 2 lanes + clock | U17/V17, U16/V16, U15/V15 |
| USB0 | Device (USB-C #1) | V12, U12, V11 |
| USB1 | Host to hub | V10, U10, U11, DRVVBUS D19 |
| WKUP_CLKOUT0 | 32 kHz to M.2 SUSCLK | C7 |
| OSPI0, CPSW port 2, MCAN0, MCU_MCAN0/1, MCU_SPI0, OLDI0 | Not used as interfaces; pads re-used as GPIO or UART6 | |

## 2. Decisions that differ from the obvious or from the SK, and why

1. **BT is on UART6, not MAIN_UART1.**
   - The SK runs BT on MAIN_UART1 through a FET mux shared with an FT4232 channel. MAIN_UART1 is also the TIFS console, so the two conflict.
   - UART6 is available as a complete 4-wire port on the OSPI0_D4–D7 balls (mode 3). Those balls sit in VDDSHV1, which is 1.8 V, the same level as M.2 UART. No buffer or level shifter is needed, and MAIN_UART1 stays free for FT4232 channel B.
   - BT_EN (GPIO0_12 on OSPI0_CSn1) is also native 1.8 V, which removes the SK's TXS0104.
2. **HDMI audio uses a second McASP (McASP2) on the unused RGMII2 balls.**
   - Separate ALSA cards allow independent sample rates and simultaneous codec and HDMI streams.
   - No SN74CB3Q3257 mux is needed (the SK needed one).
   - It takes no balls from the header or the boot straps, and all its balls are at 3.3 V (VDDSHV2), which matches SiI9022A IOVCC.
   - **Alternative:** share McASP1, fanning BCLK and FSYNC out to both chips, with AXR0 to the codec and AXR1 (GPMC0_OEn_REn, m2) to HDMI. The cost is that pin 31 of the header is lost. I rejected it.
3. **The header favours PCM/I2S over RPi SPI1 on pins 12/35/38/40.**
   - Only the McASP0 balls offer both McASP and SPI2 at 3.3 V. Even on those balls, SPI2_CLK exists only on MCASP0_ACLKR, and no ball carries both a frame-sync and a SPI data function.
   - So RPi PCM (CLK, FS, DIN, DOUT) and RPi SPI1 (CE0, MISO, MOSI, SCLK) cannot both sit on the RPi pins. I chose PCM, because audio HATs are far more common than SPI1 HATs.
   - **Consequences:**
     - RPi SPI1 is **not available**. Pins 11 and 36 are plain GPIO.
     - SPI2 fragments are still reachable as alternate modes: CS1 on pin 12, CS3 on 35, D0 on 38, D1 on 40, CS2 on 32. Without a clock they are of little use.
     - The SK put SPI2 on 11/12/35/36/38/40, so SK SPI2 overlays will not port.
4. **Header PWM0/PWM1 (pins 32/33) use EHRPWM1_A/B,** a real Linux ehrpwm channel pair. The SK had a PRU eCAP on pin 32.
5. **Header I2C (pins 3/5) uses MCU_I2C0 and HAT-ID (pins 27/28) uses WKUP_I2C0.**
   - Both are the AM62x "I2C OD FS" fail-safe open-drain buffers, so they tolerate a HAT that pulls up while the SoC is unpowered. **[C]** AM625 Table 5-1 buffer type; Octavo checklist 62_ALL_16.
   - The SK used I2C2 behind a TCA9543A for pins 3/5, and SoC I2C0 (the PMIC bus) for 27/28. The proposal forbids the latter, and so does the task.
   - I2C2 is then free for the camera. **[I]** Linux must enable `mcu_i2c0` and `wkup_i2c0` in the device tree. Make sure no M4F firmware claims MCU_I2C0.
6. **Header UART (pins 8/10) is UART5 on the MCAN0 balls.** This is the same as the SK and BRK, so their device-tree overlays carry over. CAN is therefore not available on the main domain. MCU_MCAN0/1 balls are used as GPIO.
7. **The PHY interrupt gets its own GPIO (GPIO0_87).** EXTINTn is the TPS65219 nINT. **[?]** The SK shared EXTINTn between the PHY and PRU, but I did not confirm that the TPS65219 MFD driver requests a shared IRQ. A dedicated GPIO avoids the question.
8. **The second Ethernet port is given up.** All 12 RGMII2 balls are re-used:
   - 4 for McASP2 / HDMI audio.
   - 8 as 3.3 V main-domain GPIO: PHY reset/int, HDMI reset/int, hub reset, SD power enable, codec reset, CAM_IO0.

   If a second port is wanted later, move those GPIOs to the spare MCU-domain balls (§9) and HDMI audio back onto McASP1.
9. **eMMC reset uses GPIO0_11 (OSPI0_CSn0, 1.8 V)** combined with RESETSTATz in a 1.8 V-powered LVC1G08. The LVC inputs are 5.5 V-tolerant, so they accept the 3.3 V RESETSTATz. This copies the SK's AND-with-RESETSTATz scheme for eMMC, SD power, PHY, HDMI and hub resets.

## 3. 40-pin header map (3.3 V everywhere)

| Pin | RPi function | AM62x function (mode) | Pad | Ball | Same as SK? |
|---|---|---|---|---|---|
| 3 | GPIO2 SDA1 | MCU_I2C0_SDA (0) | MCU_I2C0_SDA | B7 | no (SK: I2C2) |
| 5 | GPIO3 SCL1 | MCU_I2C0_SCL (0) | MCU_I2C0_SCL | A7 | no |
| 7 | GPIO4 GPCLK0 | CLKOUT0 (5) / GPIO1_30 | EXT_REFCLK1 | D16 | yes |
| 8 | GPIO14 TXD | UART5_TXD (1) | MCAN0_RX | A11 | yes |
| 10 | GPIO15 RXD | UART5_RXD (1) | MCAN0_TX | B11 | yes |
| 11 | GPIO17 | GPIO0_40 (7) | GPMC0_DIR | G25 | no (SK: SPI2_CS1) |
| 12 | GPIO18 PCM_CLK | MCASP0_ACLKX (0); alt SPI2_CS1, ECAP2 PWM | MCASP0_ACLKX | A18 | no |
| 13 | GPIO27 | GPIO0_42 | GPMC0_CSn1 | F25 | yes |
| 15 | GPIO22 | GPIO1_22 | UART0_CTSn | A9 | yes |
| 16 | GPIO23 | GPIO0_38 | GPMC0_WAIT1 | L26 | yes |
| 18 | GPIO24 | GPIO0_31 | GPMC0_CLK | K26 | no (SK: GPMC0_WPn, now AUD_MCLK) |
| 19 | GPIO10 MOSI | SPI0_D0 | SPI0_D0 | D12 | yes |
| 21 | GPIO9 MISO | SPI0_D1 | SPI0_D1 | C12 | yes |
| 22 | GPIO25 | GPIO1_23 | UART0_RTSn | B9 | no (SK: 1.8 V OSPI0_CSn3) |
| 23 | GPIO11 SCLK | SPI0_CLK | SPI0_CLK | C11 | yes |
| 24 | GPIO8 CE0 | SPI0_CS0 | SPI0_CS0 | D13 | yes |
| 26 | GPIO7 CE1 | SPI0_CS1 | SPI0_CS1 | C13 | yes |
| 27 | ID_SD | WKUP_I2C0_SDA | WKUP_I2C0_SDA | B8 | no (SK: I2C0) |
| 28 | ID_SC | WKUP_I2C0_SCL | WKUP_I2C0_SCL | A8 | no (SK: I2C0) |
| 29 | GPIO5 | GPIO0_36 | GPMC0_BE1n | K25 | yes |
| 31 | GPIO6 | GPIO0_33 | GPMC0_OEn_REn | H26 | yes |
| 32 | GPIO12 PWM0 | EHRPWM1_A (6) | MCASP0_AXR1 | A17 | no (SK: GPMC0_DIR eCAP) |
| 33 | GPIO13 PWM1 | EHRPWM1_B (6) | MCASP0_AXR0 | B17 | yes |
| 35 | GPIO19 PCM_FS | MCASP0_AFSX (0) | MCASP0_AFSX | B18 | no (SK: SPI2_D1) |
| 36 | GPIO16 | MCU_GPIO0_13 | MCU_MCAN0_TX | E2 | no (SK: SPI2_CS2) |
| 37 | GPIO26 | GPIO0_41 | GPMC0_CSn0 | F26 | yes |
| 38 | GPIO20 PCM_DIN | MCASP0_AXR3 (0); alt SPI2_D0 | MCASP0_AXR3 | A16 | yes (same ball) |
| 39 | GND | | | | no (SK: HAT-detect) |
| 40 | GPIO21 PCM_DOUT | MCASP0_AXR2 (0); alt SPI2_D1 | MCASP0_AXR2 | B16 | no (SK: SPI2_CLK) |

Notes on the header:

- **None of the header balls are BOOTMODE balls.** A HAT therefore cannot change the boot mode.
- **Fail-safety.** Only pins 3, 5, 27 and 28 are fail-safe. Keep the 33–100 Ω series resistors and the switched header rails from proposal §5.7 on all other pins.

## 4. BOOTMODE straps (GPMC0_AD0–15, latched on the rising edge of PORz_OUT, pulled to VDDSHV3 3.3 V)

Default is **0x0643**: 25 MHz reference, primary MMCSD on port 1 (SD card) in filesystem mode, backup USB DFU. The individual bits:

| Bits | Value | Meaning |
|---|---|---|
| B2..B0 | 011 | 25 MHz |
| B6..B3 | 1000 | MMCSD |
| B7 | 0 | Filesystem mode |
| B8 | 0 | Reserved |
| B9 | 1 | MMC port 1 |
| B12..B10 | 001 | Backup USB |
| B13 | 0 | DFU |
| B15..B14 | 00 | Reserved |

**[C]** TRM boot chapter, Tables 5-2 to 5-5, 5-18 and 5-29.

- **DIP switch on B6..B3 (GPMC0_AD3–6).** These balls have no display function. The useful settings are:
  - 1000 SD.
  - 1001 eMMC boot (no extra configuration bits).
  - 0111 UART.
  - 0100 RGMII Ethernet.
  - 1111 no-boot/dev.
- **B8..B15 are VOUT0_DATA16–23**, so they get fixed 10 kΩ straps only.
- **[?]** **USB as the primary boot mode (1010) should not be selected.** It reads B9 as "core voltage", and the fixed B9 = 1 means 0.75 V, while this board runs VDD_CORE at 0.85 V. USB DFU is set as the backup instead, and the backup path does not use B9.
- **[?]** Ethernet RGMII primary boot also reads B9 as the "Clkout" option. Confirm in the TRM what B9 = 1 does for RGMII boot.

## 5. OLDI0 is not used (scope change: HDMI only)

- **All 20 OLDI0 balls** (P2, R1, R2, T1, T2, U2–U9, V3–V9) are left **unconnected**: no traces and no vias to them. **[C]** AM625 DS Table 5-74: "If OLDI0 is not used, leave unconnected"; Octavo checklist 62_OLDI_1.
- **VDDA_1P8_OLDI0 (ball P11) must still be powered from the 1.8 V analog rail** (LDO3, through the usual bead), with the Octavo Table 4-3 decoupling (1 µF + 0.1 µF).
  - **[C]** AM625 Table 5-74 allows CSIRX0 and USB analog supplies to go to VSS when those blocks are unused. It gives **no such exception for VDDA_1P8_OLDI0**, and its general note says all power balls must be supplied unless otherwise specified.
  - **[C]** The Octavo checklist is silent on the OLDI supply.
  - **[I]** So: keep it at 1.8 V.
- No panel I2C, touch interrupt, panel reset or backlight PWM is allocated.
- The OLDI0 pins **stay in the SiP symbol** (Part G) so that every footprint pad maps to a pin.

## 6. Other unused-interface rules applied

- **CSI0 lanes 2/3** (U13, V13, U14, V14): leave unconnected, because CSI0 runs in 2-lane mode (Table 5-74). VDDA_1P8_CSIRX0 and VDDA_CORE_CSIRX0 stay powered, because CSI is used.
- **USB0_DRVVBUS** (C19): not used, because the port is device-only. Leave it unrouted. Optionally fit a 10 kΩ pull-down; the SK D-note says to fit it if USB deep-sleep wake is not used. Octavo 62_USB_6 notes the internal pull-down is enabled by default.
- **VPP** (eFuse): leave open or at 0 V except while programming. The VPP_EFUSE_EN LDO is DNP. Do not confuse it with DDR_VPP (2.5 V).
- **NC (93 balls) and RSVD (AM62X_RSVD0–8, DDR_RSVD0):** no connection and no routing through them (Octavo 62_ALL_6).
- **MCU_OSC0_XO** goes to VSS, because XI is driven by an LVCMOS oscillator. **WKUP_LFOSC0** has a 32.768 kHz crystal; it is not unused.

## 7. GPIO list (Linux numbering: main_gpio0/1 = GPIOx_y, mcu_gpio0 = MCU_GPIO0_y)

| Net | GPIO | Pad (ball) | V | Default (external pull) |
|---|---|---|---|---|
| EMMC_RST_N | GPIO0_11 | OSPI0_CSn0 (D25) | 1.8 | PU, AND RESETSTATz |
| BT_EN | GPIO0_12 | OSPI0_CSn1 (C25) | 1.8 | PD |
| WLAN_EN | GPIO0_71 | MMC2_SDCD (D20) | 1.8 | per SK |
| WLAN_IRQ | GPIO0_72 | MMC2_SDWP (C20) | 1.8 | PU (SK rev B) |
| SD_VSEL | GPIO1_49 | MMC1_SDWP (B23) | 3.3 | sets 3.3 V at POR **[?] polarity** |
| SD_PWR_EN | GPIO1_1 | RGMII2_RX_CTL (T23) | 3.3 | PU, AND RESETSTATz |
| ETH_PHY_RST_N | GPIO0_88 | RGMII2_TXC (R19) | 3.3 | PU, AND RESETSTATz |
| ETH_PHY_INT_N | GPIO0_87 | RGMII2_TX_CTL (T20) | 3.3 | PU |
| HDMI_RST_N | GPIO0_89 | RGMII2_TD0 (T22) | 3.3 | PD, AND RESETSTATz |
| HDMI_INT_N | GPIO0_90 | RGMII2_TD1 (R21) | 3.3 | PU |
| USB_HUB_RST_N | GPIO1_2 | RGMII2_RXC (R22) | 3.3 | PD, AND RESETSTATz |
| AUD_RST_N | GPIO1_3 | RGMII2_RD0 (T25) | 3.3 | PD |
| CAM_IO0 (power/reset) | GPIO1_4 | RGMII2_RD1 (R24) | 3.3 | PD |
| CAM_IO1 (optional) | MCU_GPIO0_14 | MCU_MCAN0_RX (E1) | 3.3 | 0 Ω DNP |
| PD_INT_N | MCU_GPIO0_16 | MCU_MCAN1_RX (F1) | 3.3 | PU |
| USER_BTN_N | MCU_GPIO0_15 | MCU_MCAN1_TX (F2) | 3.3 | PU (SK SW4) |
| USER_LED1 | MCU_GPIO0_0 | MCU_SPI0_CS0 (B6) | 3.3 | |
| USER_LED2 | MCU_GPIO0_1 | MCU_SPI0_CS1 (A6) | 3.3 | |
| VPP_EFUSE_EN | MCU_GPIO0_2 | MCU_SPI0_CLK (A4) | 3.3 | PD |

Notes on the GPIOs:

- **External pulls.** All of these balls come out of reset as GPIO with the input buffer off and no pull (Off/Off/Off). Every line whose default state matters therefore has an external pull, as listed.
- **[?] MCU_GPIO0 in Linux.** The MCU_GPIO0 lines need `mcu_gpio0` enabled in the Linux device tree. TI's SK drives MCU_GPIO0_1 and _15 from Linux, but confirm the SDK version does not reserve the bank for the M4F.

## 8. Flags: allocations I am not fully sure of

1. **[?] SD_VSEL polarity and default.** Check which VSEL_SD level gives 3.3 V in the TPS6521904 NVM (SLVUCL1), then choose the strap direction.
2. **[?] USB1_DRVVBUS.** I allocated it as the host VBUS enable (USB-A switch enable or hub VBUS-detect). If the hub's per-port PWRCTL drives the port switches, leave DRVVBUS unrouted with a pull-down instead.
3. **[?] SiI9022A MCLK requirement.** HDMI_I2S_MCLK (AUDIO_EXT_REFCLK0) is a DNP option until this is confirmed.
4. **[?] AUDIO_EXT_REFCLK1 frequency accuracy for 48 kHz and 44.1 kHz families.** It depends on the audio PLL configuration. Keep the DNP 12.288 MHz oscillator option. The codec PLL can also derive its clocks from BCLK.
5. **[?] PMIC_LPM_EN0 destination.** I assumed TPS65219 MODE/STBY. Confirm against SK p.13.
6. **[?] DPI bit order to the SiI9022A.** Confirm against SK p.43.
7. **[?] Tag-Connect variant.** The chosen footprint must carry TRSTn, and optionally EMU0/1. Otherwise TRSTn's pull-down holds the TAP in reset.
8. **[?] EEPROM address.** The board-ID EEPROM is at 0x50 (BRK). TI's SK board-detect EEPROM is at 0x51. Pick one deliberately; the Octavo U-Boot does not use TI board-detect.
9. **[I] FT4232H back-power.** The FT4232H is powered from the debug USB. Put SN74AVC4T245- or TXU0104-class isolation on all 8 UART lines (SK practice), or the SoC RX pads get back-powered while the board is off.
10. **[I] M.2 sideband voltages.** UART, SDIO, WLAN_EN and BT_EN are at 1.8 V (SK practice for M.2-CC3351). SUSCLK is at 3.3 V (WKUP_CLKOUT0 on VDDSHV_MCU). Confirm the module's BT_EN and WLAN_EN thresholds in the M.2-CC3351 data.

## 9. Unused balls by IO domain (39 balls, plus the 8 strap-only balls)

| Domain | Ball (pad) | Recommendation |
|---|---|---|
| VDDA_1P8_OLDI0 | P2 (A0N), R1 (A0P), R2 (A1N), T1 (A1P), T2 (A2N), U2 (A2P), U3 (A3N), V3 (A3P), U4 (A4N), V4 (A4P), U5 (A5N), V5 (A5P), U6 (A6N), V6 (A6P), U7 (A7N), V7 (A7P), U8 (CLK0N), V8 (CLK0P), U9 (CLK1N), V9 (CLK1P) | Unconnected; VDDA_1P8_OLDI0 (P11) stays at 1.8 V |
| VDDA_1P8_CSIRX0 | U14 (RXN2), U13 (RXN3), V14 (RXP2), V13 (RXP3) | Unconnected (2-lane mode) |
| VDDSHV1 (1.8 V) | A24 (OSPI0_CLK), D24 (OSPI0_CSn2), C24 (OSPI0_CSn3), B24 (D0), A25 (D1), B25 (D2), A26 (D3), D26 (DQS), C26 (LBCLKO) | 9 spare 1.8 V GPIOs (GPIO0_0–6, _13, _14); leave unconnected or bring out to test pads. Candidates: M.2 UART_WAKE#, eMMC module detect. |
| VDDSHV_MCU (3.3 V) | B5 (MCU_SPI0_D0), A5 (MCU_SPI0_D1) | Spare MCU_GPIO0_3/4 |
| VDDSHV_CANUART (3.3 V) | B4 (MCU_UART0_CTSn), A3 (MCU_UART0_RTSn), D1 (WKUP_UART0_CTSn), D2 (WKUP_UART0_RTSn) | Spare MCU_GPIO0_7/8/11/12 (wake-capable) |
| VDDSHV3 (3.3 V) | G28, G27, F28, F27, E28, E27, D28, D27 (GPMC0_AD0–7) | BOOTMODE00–07 straps only; no runtime use |
| VDDSHV0, VDDSHV2, VDDSHV4, VDDSHV5, VDDSHV6, VDDS_OSC0 | none | Every ball is allocated. C19 USB0_DRVVBUS is listed in the CSV as "unused, optional pull-down". |

Peripheral instances left completely unused: I2C3, SPI1, SPI2 (fragments only), MCAN0, MCU_MCAN0/1, MCU_SPI0/1, OSPI0, GPMC, CPSW port 2, OLDI0, PRU-SS IO, eQEP, and EHRPWM0/2.
