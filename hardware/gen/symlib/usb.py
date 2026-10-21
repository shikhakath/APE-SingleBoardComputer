"""Symbols for sheet 09 (USB): CH335F hub, TPS2051B switch, USBLC6-2SC6 and
ESD122 ESD arrays, SDCW2012 common-mode choke, SOT-23 zener, 12 MHz crystal
and the Bossie dual stacked USB-A receptacle.

Every pin table below was read from the datasheet named above the symbol
(downloaded 2026-10-17); the page/table is given in the comment.
"""
from schgen import box

# WCH CH334/CH335 datasheet V2.91 (Chinese), LCSC C5137013:
# https://datasheet.lcsc.com/datasheet/pdf/77721fceaa29165ba79c58173b46c67f.pdf?productCode=C5137013
# Figure 1-1 p.2 (CH335F QFN-28 pin drawing) and Table 1-3 p.4-6 (pin definitions,
# "335F" column). Exposed pad is "pin 0" in the datasheet (GND, 底板); mapped here as
# pin 29, the next free number. Pin 27 is an optional GND (may float, connect it).
# OVCURx# and RESET#/CDP are 5 V tolerant inputs ("5I"); RESET# has a ~25 kOhm
# internal pull-up (3.2.2 p.11); LED1/PSELF and LED2/PGANG are sampled during reset
# (internal pull-ups: self-powered, ganged OC) and then drive LEDs.
CH335F = box("CH335F", "WCH CH335F USB 2.0 HS 4-port MTT hub, per-port power/OC, QFN-28 4x4", [
    (21, "DPU", "io", "L"),
    (20, "DMU", "io", "L"),
    ("", "", "pas", "L"),
    (11, "XI", "in", "L"),
    (12, "XO", "out", "L"),
    ("", "", "pas", "L"),
    (17, "RESET#/CDP", "in", "L"),
    (1, "LED1/PSELF", "io", "L"),
    (3, "LED2/PGANG", "io", "L"),
    (22, "LED3/SCL", "io", "L"),
    (25, "LED4/SDA", "io", "L"),
    ("", "", "pas", "L"),
    (26, "V5", "pwr", "L"),
    (28, "VDD33", "pwr", "L"),
    (27, "GND", "pwr", "L"),
    (29, "EP_GND", "pwr", "L"),
    (7, "DP1", "io", "R"),
    (6, "DM1", "io", "R"),
    (4, "PWREN1#", "out", "R"),
    (24, "OVCUR1#", "in", "R"),
    (9, "DP2", "io", "R"),
    (8, "DM2", "io", "R"),
    (2, "PWREN2#", "out", "R"),
    (23, "OVCUR2#", "in", "R"),
    (14, "DP3", "io", "R"),
    (13, "DM3", "io", "R"),
    (10, "PWREN3#", "out", "R"),
    (19, "OVCUR3#", "in", "R"),
    (16, "DP4", "io", "R"),
    (15, "DM4", "io", "R"),
    (5, "PWREN4#/SUSP", "out", "R"),
    (18, "OVCUR4#", "in", "R"),
], footprint="QFN28_4X4_P0.4")

# TI TPS2041B/TPS2051B datasheet SLVS514P (Aug 2024),
# https://www.ti.com/lit/ds/symlink/tps2051b.pdf, Figure 5-1 (DBV top view) and
# Table 5-1 "Pin Functions" p.3: SOT-23 OUT=1, GND=2, OC=3, EN=4 (TPS2051B: active
# high), IN=5. OC is an open-drain, active-low fault output.
TPS2051B_DBV = box("TPS2051B_DBV", "TPS2051B 0.5 A USB power switch, active-high EN, OC flag, SOT-23-5", [
    (5, "IN", "pwr", "L"),
    (4, "EN", "in", "L"),
    (2, "GND", "pwr", "L"),
    (1, "OUT", "pas", "R"),
    (3, "nOC", "oc", "R"),
], footprint="SOT23-5")

# ST USBLC6-2 datasheet (LCSC C7519),
# https://datasheet.lcsc.com/datasheet/pdf/0d3a2ab954b34651a0695e7ccf534db0.pdf?productCode=C7519
# Figure 1 "Functional diagram (top view)" p.1, SOT23-6L: I/O1=1 and 6 (same line,
# flow-through), GND=2, I/O2=3 and 4, VBUS=5.
USBLC6_2SC6 = box("USBLC6-2SC6", "USBLC6-2 2-line USB ESD array with VBUS clamp, SOT23-6L", [
    (1, "I/O1", "pas", "L"),
    (3, "I/O2", "pas", "L"),
    (2, "GND", "pwr", "L"),
    (6, "I/O1", "pas", "R"),
    (4, "I/O2", "pas", "R"),
    (5, "VBUS", "pwr", "R"),
], prefix="D", footprint="SOT23-6")

# TI ESD122 datasheet SLVSDP5A, https://www.ti.com/lit/ds/symlink/esd122.pdf,
# section 5 "Pin Configuration and Functions" p.3, DMX (X2SON-3 0.6x1.0): GND=1,
# IO1=2, IO2=3.
ESD122_DMX = box("ESD122_DMX", "ESD122 2-channel 0.2 pF bidirectional ESD diode, X2SON-3 (DMX)", [
    (2, "IO1", "pas", "L"),
    (3, "IO2", "pas", "L"),
    (1, "GND", "pwr", "R"),
], prefix="D", footprint="X2SON3_DMX")

# Sunlord SDCW series catalogue (rev. 2025-05-23, JLC/LCSC C54888), p.1 "Shape and
# Dimensions" terminal numbering (1)..(4) and p.3 "Equivalent Circuit": winding A
# (1)-(2), winding B (4)-(3), dots on 1 and 4. SDCW2012-2-900TF: 90 Ohm @100 MHz,
# 0.35 Ohm, 330 mA (p.2 table).
SDCW2012_CMC = box("SDCW2012-2", "Sunlord SDCW2012-2 wire-wound 2-line common-mode choke, 0805", [
    (1, "A1", "pas", "L"),
    (4, "B4", "pas", "L"),
    (2, "A2", "pas", "R"),
    (3, "B3", "pas", "R"),
], prefix="L", footprint="CMC_SUNLORD_SDCW2012")

# LRC LBZX84CxxxLT1G series datasheet Rev.A (LCSC C12746),
# https://datasheet.lcsc.com/datasheet/pdf/f38bff37f838ce082f42e60b9be47320.pdf?productCode=C12746
# p.1 package drawing and p.2 table heading "Pinout: 1-Anode, 2-No Connection,
# 3-Cathode". LBZX84C6V8LT1G: Vz 6.4/6.8/7.2 V @5 mA, IR <= 2 uA @ 4 V.
BZX84_SOT23 = box("BZX84_SOT23", "Zener diode SOT-23 (1 = anode, 2 = NC, 3 = cathode)", [
    (3, "K", "pas", "L"),
    (1, "A", "pas", "R"),
    (2, "NC", "pas", "R"),
], prefix="D", footprint="SOT23-3")

# YXC YSX321SL crystal datasheet (X322512MSB4SI, LCSC C9002),
# https://datasheet.lcsc.com/datasheet/pdf/a84bd8d530dd46e4b0f6d0ee59d8a89c.pdf?productCode=C9002
# "Top View Crystal Connection" p.1: crystal between #1 and #3, #2 and #4 = GND.
XTAL_YSX321SL = box("XTAL_YSX321SL", "Crystal 3.2x2.5 mm 4-pad, YXC YSX321SL (1/3 crystal, 2/4 GND)", [
    (1, "X1", "pas", "L"),
    (2, "GND", "pas", "L"),
    (3, "X2", "pas", "R"),
    (4, "GND", "pas", "R"),
], prefix="Y", footprint="XTAL_3225_4P")

# Bossie BX-TYPE-A-MWC44 drawing rev A (LCSC C18077688),
# https://datasheet.lcsc.com/datasheet/pdf/5bd3848faf114811a5412815f6d91e72.pdf?productCode=C18077688
# "Recommended PCBA layout": 2 rows x 4 contacts (0.90 mm holes, 2.00 mm pitch,
# rows 2.71 mm apart) and 4 shell pegs (2.30 mm holes). The drawing does NOT
# number the pads, so this symbol defines the numbering; the footprint must use
# it: 1-4 = lower port (VBUS, D-, D+, GND), 5-8 = upper port, 9-12 = shell pegs.
BX_TYPE_A_MWC44 = box("BX-TYPE-A-MWC44", "Dual stacked USB 2.0 Type-A receptacle, THT right angle (Bossie BX-TYPE-A-MWC44)", [
    (1, "VBUS_L", "pwr", "L"),
    (2, "D-_L", "pas", "L"),
    (3, "D+_L", "pas", "L"),
    (4, "GND_L", "pwr", "L"),
    ("", "", "pas", "L"),
    (5, "VBUS_U", "pwr", "L"),
    (6, "D-_U", "pas", "L"),
    (7, "D+_U", "pas", "L"),
    (8, "GND_U", "pwr", "L"),
    (9, "SHELL", "pas", "R"),
    (10, "SHELL", "pas", "R"),
    (11, "SHELL", "pas", "R"),
    (12, "SHELL", "pas", "R"),
], prefix="J", footprint="USBA_2X_BX-TYPE-A-MWC44")

SYMBOLS = [CH335F, TPS2051B_DBV, USBLC6_2SC6, ESD122_DMX, SDCW2012_CMC, BZX84_SOT23,
           XTAL_YSX321SL, BX_TYPE_A_MWC44]
