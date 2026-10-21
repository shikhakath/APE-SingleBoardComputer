"""Symbols for sheet 14 (40-pin expansion header) and sheet 15 (debug: FT4232HL,
isolation buffers, debug USB-C, Tag-Connect TC2070).

Every pin table below was read from the datasheet named above the symbol
(downloaded 2026-10-17, text extracted with pdftotext -layout / PyMuPDF; the
drawings without a text layer were rendered and read as images). Every package
pin is present, including shells, NC pins and grounds.
"""
from schgen import box, two_pin

# ------------------------------------------------------------ sheet 14

# HanElectricity 2541WV-2x20P, 2x20 2.54 mm THT pin header (LCSC C25503140).
# https://www.lcsc.com/datasheet/lcsc_datasheet_2407041454_HanElectricity-2541WV-2x20P_C25503140.pdf
# The drawing (single sheet, rev A 2015-05-03) shows two rows of 20 pins at
# 2.54 mm and no shell or mounting pins; it gives no pin numbers, so the pins
# use the Raspberry Pi / IDC numbering: odd pins in one row, even pins in the
# other, pin 1 = 3V3. Pin names are the Raspberry Pi functions
# (docs/research/pinmux-allocation.md section 3).
_RPI_NAMES = {
    1: "3V3", 2: "5V", 3: "GPIO2/SDA1", 4: "5V", 5: "GPIO3/SCL1", 6: "GND",
    7: "GPIO4/GPCLK0", 8: "GPIO14/TXD", 9: "GND", 10: "GPIO15/RXD",
    11: "GPIO17", 12: "GPIO18/PCM_CLK", 13: "GPIO27", 14: "GND", 15: "GPIO22",
    16: "GPIO23", 17: "3V3", 18: "GPIO24", 19: "GPIO10/MOSI", 20: "GND",
    21: "GPIO9/MISO", 22: "GPIO25", 23: "GPIO11/SCLK", 24: "GPIO8/CE0", 25: "GND",
    26: "GPIO7/CE1", 27: "ID_SD", 28: "ID_SC", 29: "GPIO5", 30: "GND",
    31: "GPIO6", 32: "GPIO12/PWM0", 33: "GPIO13/PWM1", 34: "GND",
    35: "GPIO19/PCM_FS", 36: "GPIO16", 37: "GPIO26", 38: "GPIO20/PCM_DIN",
    39: "GND", 40: "GPIO21/PCM_DOUT",
}
HDR_2X20 = box("HDR_2X20_2541WV", "Pin header 2x20 2.54 mm, Raspberry Pi 40-pin numbering", [
    (n, _RPI_NAMES[n], "pas", "L" if n % 2 else "R") for n in range(1, 41)
], prefix="J", footprint="HDR_2X20_P2.54_THT")

# BHFUSE BSMD1206-110-6V PTC resettable fuse, 1206 (LCSC C2803344).
# https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2305121425_BHFUSE-BSMD1206-110-6V_C2803344.pdf
# Electrical table p.4: Ihold 1.10 A, Itrip 2.20 A, Vmax 6 V. Two terminals, not polarized.
PTC_BSMD1206 = two_pin("PTC_BSMD1206", "PTC resettable fuse, 1206, not polarized", [
    "rectangle|1|1|0|-100|-35|100|35", "line|1|1|-80|-60|60|60", "line|1|1|60|60|100|60"],
    "F", body=100, footprint="FUSE_BHFUSE_BSMD1206")

# Shanghai Belling BL24C32A-SFRC, 32 Kbit I2C EEPROM, TSSOP-8 (LCSC C177775).
# https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_BL-Shanghai-Belling-BL24C32A-SFRC_C177775.pdf
# Pin Configuration p.1 (8-lead TSSOP) and Pin Descriptions Table 1 p.2; ordering
# code p.19: SF = TSSOP-8L, R = reel, C = green.
BL24C32A = box("BL24C32A_TSSOP8", "BL24C32A 32 Kbit I2C EEPROM (2-byte address), TSSOP-8", [
    (1, "A0", "in", "L"), (2, "A1", "in", "L"), (3, "A2", "in", "L"),
    (7, "WP", "in", "L"), (4, "GND", "pwr", "L"),
    (8, "VCC", "pwr", "R"), (5, "SDA", "io", "R"), (6, "SCL", "in", "R"),
], footprint="TSSOP8_4.4X3.0_P0.65")

# ------------------------------------------------------------ sheet 15

# FTDI FT4232HL, LQFP-64. FTDI datasheet DS_FT4232H Version 2.6 (FT_000060),
# Figure 3.1 (schematic symbol) and Tables 3.1-3.5 (pages 7-10); copy taken from
# https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_FTDI-FT4232HL-Reel_C56742.pdf
# (ftdichip.com/wp-content/uploads/2020/08/DS_FT4232H.pdf refused the download).
# Bus pin functions in async serial mode (Table 3.5): xDBUS0 TXD, 1 RXD,
# 2 RTS#, 3 CTS#, 4 DTR#, 5 DSR#, 6 DCD#, 7 RI#/TXDEN.
_S = ("", "", "pas", "L")
_SR = ("", "", "pas", "R")
FT4232HL = box("FT4232HL", "FT4232H quad Hi-Speed USB to UART/MPSSE, LQFP-64", [
    (50, "VREGIN", "pwr", "L"), (49, "VREGOUT", "pwr", "L"),
    (12, "VCORE", "pwr", "L"), (37, "VCORE", "pwr", "L"), (64, "VCORE", "pwr", "L"),
    (20, "VCCIO", "pwr", "L"), (31, "VCCIO", "pwr", "L"), (42, "VCCIO", "pwr", "L"),
    (56, "VCCIO", "pwr", "L"), (4, "VPHY", "pwr", "L"), (9, "VPLL", "pwr", "L"),
    _S,
    (8, "DP", "io", "L"), (7, "DM", "io", "L"), (6, "REF", "pas", "L"),
    (14, "RESET#", "in", "L"), (13, "TEST", "in", "L"),
    (2, "OSCI", "in", "L"), (3, "OSCO", "out", "L"),
    _S,
    (63, "EECS", "io", "L"), (62, "EECLK", "out", "L"), (61, "EEDATA", "io", "L"),
    _S,
    (60, "PWREN#", "out", "L"), (36, "SUSPEND#", "out", "L"),
    _S,
    (10, "AGND", "pwr", "L"), (1, "GND", "pwr", "L"), (5, "GND", "pwr", "L"),
    (11, "GND", "pwr", "L"), (15, "GND", "pwr", "L"), (25, "GND", "pwr", "L"),
    (35, "GND", "pwr", "L"), (47, "GND", "pwr", "L"), (51, "GND", "pwr", "L"),
    (16, "ADBUS0/TXD", "io", "R"), (17, "ADBUS1/RXD", "io", "R"), (18, "ADBUS2", "io", "R"),
    (19, "ADBUS3", "io", "R"), (21, "ADBUS4", "io", "R"), (22, "ADBUS5", "io", "R"),
    (23, "ADBUS6", "io", "R"), (24, "ADBUS7", "io", "R"),
    _SR,
    (26, "BDBUS0/TXD", "io", "R"), (27, "BDBUS1/RXD", "io", "R"), (28, "BDBUS2", "io", "R"),
    (29, "BDBUS3", "io", "R"), (30, "BDBUS4", "io", "R"), (32, "BDBUS5", "io", "R"),
    (33, "BDBUS6", "io", "R"), (34, "BDBUS7", "io", "R"),
    _SR,
    (38, "CDBUS0/TXD", "io", "R"), (39, "CDBUS1/RXD", "io", "R"), (40, "CDBUS2", "io", "R"),
    (41, "CDBUS3", "io", "R"), (43, "CDBUS4", "io", "R"), (44, "CDBUS5", "io", "R"),
    (45, "CDBUS6", "io", "R"), (46, "CDBUS7", "io", "R"),
    _SR,
    (48, "DDBUS0/TXD", "io", "R"), (52, "DDBUS1/RXD", "io", "R"), (53, "DDBUS2", "io", "R"),
    (54, "DDBUS3", "io", "R"), (55, "DDBUS4", "io", "R"), (57, "DDBUS5", "io", "R"),
    (58, "DDBUS6", "io", "R"), (59, "DDBUS7", "io", "R"),
], footprint="LQFP64_10X10_P0.5")

# TI SN74AVC4T245PWR, TSSOP-16 (PW). https://www.ti.com/lit/ds/symlink/sn74avc4t245.pdf
# (SCES576I, Feb 2025) Table 4-1 Pin Functions, column "D, DGV, PW, RGY"; Table 7-1
# function table: OE low + DIR high = A->B, OE low + DIR low = B->A, OE high = isolation.
# VCCA supplies the A port and the control pins (DIR, OE).
SN74AVC4T245 = box("SN74AVC4T245_PW", "Dual 2-bit dual-supply bus transceiver, Ioff + VCC isolation, TSSOP-16", [
    (1, "VCCA", "pwr", "L"), (2, "1DIR", "in", "L"), (3, "2DIR", "in", "L"),
    (15, "1OE#", "in", "L"), (14, "2OE#", "in", "L"),
    (4, "1A1", "io", "L"), (5, "1A2", "io", "L"), (6, "2A1", "io", "L"), (7, "2A2", "io", "L"),
    (8, "GND", "pwr", "L"),
    (16, "VCCB", "pwr", "R"), ("", "", "pas", "R"), ("", "", "pas", "R"),
    ("", "", "pas", "R"), ("", "", "pas", "R"),
    (13, "1B1", "io", "R"), (12, "1B2", "io", "R"), (11, "2B1", "io", "R"), (10, "2B2", "io", "R"),
    (9, "GND", "pwr", "R"),
], footprint="TSSOP16_4.4X5.0_P0.65")

# Diodes AP2112K-3.3TRG1, 600 mA LDO, SOT-23-5 (SOT25).
# https://www.diodes.com/assets/Datasheets/AP2112.pdf (DS39724 Rev. 2-2) Pin Assignments
# and Pin Descriptions p.1-2: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT. CIN = COUT = 1 uF ceramic.
AP2112K = box("AP2112K_SOT25", "AP2112K 600 mA CMOS LDO, fixed output, SOT-23-5", [
    (1, "VIN", "pwr", "L"), (3, "EN", "in", "L"), (2, "GND", "pwr", "L"),
    (5, "VOUT", "pwr", "R"), (4, "NC", "pas", "R"),
], footprint="SOT23-5")

# Microchip 93LC46BT-I/OT, 1 Kbit Microwire EEPROM, x16 only, SOT-23-6 (OT).
# https://ww1.microchip.com/downloads/en/DeviceDoc/20001749K.pdf (DS20001749K)
# Table 3-1 Pin Descriptions, SOT-23 column: DO 1, VSS 2, DI 3, CLK 4, CS 5, VCC 6.
EE93LC46B = box("93LC46B_OT", "93LC46B 1 Kbit Microwire EEPROM (64 x 16), SOT-23-6", [
    (5, "CS", "in", "L"), (4, "CLK", "in", "L"), (3, "DI", "in", "L"), (2, "VSS", "pwr", "L"),
    (6, "VCC", "pwr", "R"), (1, "DO", "out", "R"),
], footprint="SOT23-6")

# YXC X322512MSB4SI, 12 MHz 20 pF +/-10 ppm crystal, 3.2 x 2.5 mm, 4 pads (YSX321SL series).
# https://www.lcsc.com/datasheet/lcsc_datasheet_2403291504_YXC-Crystal-Oscillators-X322512MSB4SI_C9002.pdf
# "Top View Crystal Connection": #1 and #3 = crystal, #2 and #4 = GND (lid).
X322512MSB4SI = box("X322512MSB4SI", "Crystal 3225 4-pad (1/3 crystal, 2/4 case GND)", [
    (1, "X1", "pas", "L"), (2, "GND", "pas", "L"),
    (3, "X2", "pas", "R"), (4, "GND", "pas", "R"),
], prefix="Y", footprint="XTAL_3225_4P")

# TI TPD2E001DRLR, 2-channel low-capacitance ESD with VCC rail, SOT-5 (DRL).
# https://www.ti.com/lit/ds/symlink/tpd2e001.pdf (SLLS684I) Section 5 Pin Functions,
# DRL column: VCC 1, N.C. 2, IO1 3, GND 4, IO2 5. Bypass VCC with 0.1 uF.
TPD2E001 = box("TPD2E001_DRL", "2-channel USB ESD array with VCC clamp rail, SOT-5 (DRL)", [
    (3, "IO1", "pas", "L"), (5, "IO2", "pas", "L"), (2, "NC", "pas", "L"),
    (1, "VCC", "pwr", "R"), (4, "GND", "pwr", "R"),
], prefix="U", footprint="SOT553-5")

# The debug USB-C (HRO TYPE-C-31-M-12, LCSC C165948) is the same part as USB-C #1, so
# sheet 15 reuses symlib.power_input.TYPE_C_31_M_12 (one library part, one footprint).

# Tag-Connect TC2070-NL footprint (no part; the TC2070-IDC-NL cable is a tool).
# https://www.tag-connect.com/wp-content/uploads/bsk-pdf-manager/TC2070-IDC-NL_Datasheet_12.pdf
# Sheet 1: 14 contact pads, 1-7 in one row and 8-14 in the other (14 opposite 1),
# plus three non-plated alignment holes (no pins). Sheet 2: plug pin n is IDC pin n.
# Signals = TI 14-pin JTAG header (TI "XDS Target Connection Guide",
# software-dl.ti.com/ccs/esd/documents/xdsdebugprobes/emu_jtag_connectors.html):
# 1 TMS, 2 nTRST, 3 TDI, 4 TDIS, 5 VTRef, 6 KEY, 7 TDO, 8 GND, 9 RTCK, 10 GND,
# 11 TCK, 12 GND, 13 EMU0, 14 EMU1 (pins 1-14 equal cTI-20 pins 1-14, SPRU655I Table 13).
TC2070 = box("TC2070_TI14", "Tag-Connect TC2070-NL footprint, TI 14-pin JTAG pinout (pad 6 = KEY)", [
    (1, "TMS", "pas", "L"), (3, "TDI", "pas", "L"), (5, "VTREF", "pas", "L"),
    (7, "TDO", "pas", "L"), (9, "RTCK", "pas", "L"), (11, "TCK", "pas", "L"),
    (13, "EMU0", "pas", "L"),
    (2, "nTRST", "pas", "R"), (4, "TDIS", "pas", "R"), (6, "KEY", "pas", "R"),
    (8, "GND", "pas", "R"), (10, "GND", "pas", "R"), (12, "GND", "pas", "R"),
    (14, "EMU1", "pas", "R"),
], prefix="J", footprint="TC2070-NL")

SYMBOLS = [HDR_2X20, PTC_BSMD1206, BL24C32A, FT4232HL, SN74AVC4T245, AP2112K, EE93LC46B,
           X322512MSB4SI, TPD2E001, TC2070]
