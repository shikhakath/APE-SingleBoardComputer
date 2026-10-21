"""Gull-wing small-outline ICs (SOIC-8, TSSOP-8/16/24) and two-terminal diode
packages (SOD323, SMA / DO-214AC).

Pad numbering: ICs use SOIC numbering (``dual``): pin 1 top left, 1..n/2 down
the left column, the rest up the right; every top-view pinout below was checked
against it. Diodes: pad "1" = anode (left), "2" = cathode (right), as the
generic DIODE symbol (pin 1 = A, pin 2 = K); the cathode bar marks pad 2.
Bodies are the nominal moulded body without leads (x = across the leads).
"""
from footprints import Footprint, chip, dual, with_radius


# ---------------------------------------------------------------- SOIC-8
# Microchip (Atmel) AT24C512C-SSHD-T, 8-lead JEDEC SOIC, 0.150" body (Atmel code
# 8S1 = Microchip SN). Users: AT24C512C_SOIC8 (symlib/misc.py).
# The Atmel datasheet 8720C (https://www.lcsc.com/datasheet/C12371.pdf), Section
# 13.1 "8S1 -- 8-lead JEDEC SOIC" p.15, has the outline only (E1 3.81-3.99,
# D 4.80-5.05, e 1.27 BSC, MS-012 AA) and no land pattern. The Microchip
# packaging specification DS00000049 could not be fetched (microchip.com returns
# HTTP 403), so the land pattern is taken from the current Microchip datasheet,
# which prints the same drawing:
#   Microchip AT24C512C Data Sheet DS20006161D (2019-2022), "Packaging
#   Information", DS20006161D-page 26: "8-Lead Plastic Small Outline (SN) -
#   Narrow, 3.90 mm (.150 In.) Body [SOIC]" RECOMMENDED LAND PATTERN, Microchip
#   Technology Drawing C04-2057-SN Rev H. Copy via LCSC C615967:
#   https://www.lcsc.com/datasheet/C615967.pdf
#   E (pitch) 1.27 BSC, C (pad centre spacing) 5.40, X1 (pad width) 0.60 max,
#   Y1 (pad length) 1.55 max -> pad centres x = +-5.40/2 = +-2.70.
# Body: C04-057-SN Rev H sheet 2, DS20006161D-page 25: E1 3.90 BSC x D 4.90 BSC.
# Pinout (DS20006161D-page 4, "8-Lead SOIC/SOIJ/TSSOP (Top View)"; 8720C
# Figure 1 p.2): 1 A0, 2 A1, 3 A2, 4 GND down the left, 5 SDA .. 8 VCC up the right.
SOIC8 = Footprint(
    "SOIC8_3.9X4.9_P1.27", "SOIC-8 3.9x4.9 mm, 1.27 mm pitch (Microchip SN / Atmel 8S1), Microchip C04-2057-SN land",
    dual(8, 1.27, 5.40, 1.55, 0.60),
    body=(3.90, 4.90))

# ---------------------------------------------------------------- TSSOP (TI PW)
# TI PW example board layouts (PW0008A / PW0016A / PW0024A) are identical per
# pin: NSMD pad copper 1.5 (along x) x 0.45, (R0.05) TYP corners, 0.65 pitch,
# pad centres (5.8) apart -> x = +-2.90; inner pad edge at 2.90 - 0.75 = 2.15.
# R0.05 corners (with_radius).
_PW_SPAN, _PW_L, _PW_W, _PW_R = 5.8, 1.5, 0.45, 0.05

# Shanghai Belling BL24C32A-SFRC, TSSOP-8. Users: BL24C32A_TSSOP8 (symlib/debug_io.py).
# Belling datasheet BL24C32A Version 1.94,
# https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_BL-Shanghai-Belling-BL24C32A-SFRC_C177775.pdf
# Package Information, Figure 15 "TSSOP" p.14: D 3.00 nom, E1 4.40 nom,
# E 6.40 nom, e 0.65 BSC, JEDEC MO-153 AA - outline only, no land pattern.
# Pinout p.1 "8-lead TSSOP": 1 A0, 2 A1, 3 A2, 4 GND; 5 SDA, 6 SCL, 7 WP, 8 VCC.
# Land pattern: TI PW0008A (same MO-153 AA body: D 2.9-3.1, E1 4.3-4.5), from
#   TI LM393 datasheet SLCS005AH (Oct 1979, rev. Apr 2025),
#   https://www.ti.com/lit/ds/symlink/lm393.pdf, PDF p.54 "PW0008A EXAMPLE BOARD
#   LAYOUT" (LAND PATTERN EXAMPLE, drawing 4221848/A 02/2015); outline PDF p.53.
# Cross-check: Microchip "8-Lead Plastic Thin Shrink Small Outline (ST) - 4.4 mm
# Body [TSSOP]" land pattern C04-2086 Rev B (DS20006161D-page 32) is the same:
# C 5.80, X1 0.45, Y1 1.50.
TSSOP8 = Footprint(
    "TSSOP8_4.4X3.0_P0.65", "TSSOP-8 4.4x3.0 mm, 0.65 mm pitch (MO-153 AA), TI PW0008A land",
    with_radius(dual(8, 0.65, _PW_SPAN, _PW_L, _PW_W), _PW_R),
    body=(4.40, 3.00))

# TI SN74AVC4T245PWR, TSSOP-16 (PW). Users: SN74AVC4T245_PW (symlib/debug_io.py).
# TI SCES576I (June 2004, rev. Feb 2025), https://www.ti.com/lit/ds/symlink/sn74avc4t245.pdf
# PDF p.43 "PW0016A PACKAGE OUTLINE" (D 4.9-5.1, E1 4.3-4.5, 14X 0.65) and PDF
# p.44 "PW0016A EXAMPLE BOARD LAYOUT" (16X (1.5), 16X (0.45), 14X (0.65), (5.8),
# drawing 4220204/B 12/2023). Pinout: Figure 4-1 "D, DGV, or PW Package" (Top
# View) p.4, SOIC numbering (1 VCCA top left, 8 GND, 9 GND, 16 VCCB top right).
TSSOP16 = Footprint(
    "TSSOP16_4.4X5.0_P0.65", "TSSOP-16 4.4x5.0 mm, 0.65 mm pitch (TI PW0016A), TI example board layout",
    with_radius(dual(16, 0.65, _PW_SPAN, _PW_L, _PW_W), _PW_R),
    body=(4.40, 5.00))

# TI TPD12S016PWR, TSSOP-24 (PW). Users: TPD12S016_PW (symlib/av.py).
# TI SLLSE96F (Sept 2011, rev. Oct 2015), https://www.ti.com/lit/ds/symlink/tpd12s016.pdf
# PDF p.28 "PW0024A PACKAGE OUTLINE" (D 7.7-7.9, E1 4.3-4.5, 22X 0.65) and PDF
# p.29 "PW0024A EXAMPLE BOARD LAYOUT" (24X (1.5), 24X (0.45), 22X (0.65), (5.8),
# drawing 4220208/A 02/2017). Pinout: Section 5 "PW Package 24-Pin TSSOP Top
# View" p.4: left 1 CEC_A .. 12 CT_HPD top to bottom, right 24 VCCA .. 13 5V_OUT
# top to bottom.
TSSOP24 = Footprint(
    "TSSOP24_4.4X7.8_P0.65", "TSSOP-24 4.4x7.8 mm, 0.65 mm pitch (TI PW0024A), TI example board layout",
    with_radius(dual(24, 0.65, _PW_SPAN, _PW_L, _PW_W), _PW_R),
    body=(4.40, 7.80))

# ---------------------------------------------------------------- SOD323
# Generic DIODE with Diodes Inc. BAT54WS-7-F; generic TVS_BI with Nexperia
# PESD24VL1BA (bidirectional: the cathode bar is only an orientation mark there).
# Diodes Inc. BAT54WS datasheet DS30098 Rev. 14-2 (July 2022),
# https://www.diodes.com/assets/Datasheets/BAT54WS.pdf, p.4 "Suggested Pad
# Layout" SOD323: X (pad length) 0.590, Y (pad width) 0.450, X1 (outer pad
# extent) 2.700 -> inner gap 2.700 - 2 x 0.590 = 1.520, pad centres
# x = +-(2.700 - 0.590)/2 = +-1.055.
# Body: same page, "Package Outline Dimensions" SOD323: E 1.70 typ (across the
# leads) x D 1.30 typ. Polarity: cathode band (p.1).
# Nexperia PESD24VL1BA v.3 (11 April 2023),
# https://assets.nexperia.com/documents/data-sheet/PESD24VL1BA.pdf, p.8 Fig. 9
# "Reflow soldering footprint for SOD323" (sod323_fr): lands 0.5 x 0.5 at 2.2
# pitch (outer extent 2.7), resist 0.6 x 0.6, occupied area 3.05 x 1.65 - the
# Diodes lands fit inside the same 2.7 mm extent.
SOD323 = Footprint(
    "SOD323", "SOD-323 (SC-76) diode, pad 1 anode / pad 2 cathode, Diodes Inc. suggested pad layout",
    chip(0.590, 0.450, 2.700 - 2 * 0.590),
    body=(1.70, 1.30), marker="cathode", marker_pad="2")

# ---------------------------------------------------------------- SMA
# Generic DIODE with MDD (Microdiode) SS34, SMA / DO-214AC (LCSC C8678).
# MDD SS32 THRU SS3200 datasheet Rev:2024A5, https://www.lcsc.com/datasheet/C8678.pdf
# (file https://datasheet.lcsc.com/datasheet/pdf/dfa1ff67dea875d0135103ba9ada713a.pdf).
# Page 3 "Suggested Pad Layout": A (pad width, y) 1.68, B (pad length, x) 1.52,
# C (pad centre distance) 3.93, D (gap) 2.41, E (outer extent) 5.45; consistent:
# D + B = 2.41 + 1.52 = 3.93 = C, D + 2B = 5.45 = E. Pad centres x = +-3.93/2 = +-1.965.
# Body: page 1 "DO-214AC/SMA" outline, body length 3.80-4.50 (x) and width
# 2.30-2.80 (y), no nominal given -> mid-range 4.15 x 2.55. Polarity: colour band
# = cathode (page 1).
DIO_SMA = Footprint(
    "DIO_SMA", "SMA (DO-214AC) diode, pad 1 anode / pad 2 cathode, MDD suggested pad layout",
    chip(1.52, 1.68, 2.41),
    body=(4.15, 2.55), marker="cathode", marker_pad="2")

FOOTPRINTS = [SOIC8, TSSOP8, TSSOP16, TSSOP24, SOD323, DIO_SMA]
