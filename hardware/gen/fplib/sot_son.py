"""Small-outline transistor packages (SOT-23, SC70, SOT-553/563) and small
leadless TI packages (USON, X2SON, X1SON).

All lands are the TI "EXAMPLE BOARD LAYOUT" (NSMD, preferred where both are
shown) of the package addendum, page numbers are PDF pages. TI draws every
pad with (R0.05) TYP corners; the library default roundrect corner is used.
Pin 1 is top left; pins 1..n/2 run down the left column, the rest up the
right column, as in the top-view pinouts (checked for every part named).
"""
from footprints import Footprint, chip, dual, row, smd

# --------------------------------------------------------------- SOT-23-3
# LRC LBZX84C6V8LT1G zener (BZX84_SOT23 in symlib/usb.py), SOT-23 (3 leads).
#   LBZX84C2V4LT1G series datasheet Rev.A (LCSC C12746)
#   https://datasheet.lcsc.com/datasheet/pdf/f38bff37f838ce082f42e60b9be47320.pdf?productCode=C12746
#   p.5 "SOT-23" outline and soldering footprint (inches over mm):
#   pads 0.8 (across) x 0.9 (along the lead), the two pads of pins 1/2 at
#   0.95 either side of the centre line, 2.0 between the pad-row centres.
#   Outline: A 2.80-3.04 (length, pin 1-2 direction), B 1.20-1.40 (width).
# Pinout p.2 table heading: 1 = anode, 2 = no connection, 3 = cathode; top
# view p.5: pin 3 alone on one side, 1 and 2 on the other.
# Turned 90 deg clockwise from the p.5 top view (no mirror) so pins 1 and 2
# form the left column like SOT23-5/6: 1 top left, 2 bottom left, 3 right.
SOT23_3 = Footprint(
    "SOT23-3", "SOT-23 3-lead (LRC soldering footprint), 0.95 mm pitch, 0.9 x 0.8 mm pads",
    row(["1", "2"], -1.0, 0.95, 0, -1.9, 0.9, 0.8) + [smd("3", 1.0, 0, 0.9, 0.8)],
    body=(1.30, 2.92))

# --------------------------------------------------------------- SOT-23-5
# TI DBV0005A (SOT-23, 5 leads), drawing 4214839/K 08/2024.
#   TLV755P  SBVS320D  https://www.ti.com/lit/ds/symlink/tlv755p.pdf
#     "DBV0005A EXAMPLE BOARD LAYOUT", p.45 (PACKAGE OUTLINE p.44).
#   Same drawing and revision in SN74LVC1G08 SCES217AA
#   (https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf p.28) and TPS2051B
#   SLVS514P (https://www.ti.com/lit/ds/symlink/tps2051b.pdf p.54).
# Land: 5X (1.1) x (0.6) pads, 2X (0.95) pitch, (2.6) between the pad-column
# centres -> x = +/-1.3; pads 1/2/3 at y = +0.95/0/-0.95 on the left, 5
# opposite 1 and 4 opposite 3 on the right (no middle pad). Pad copper spans
# x 0.75..1.85 (inner gap 1.5, outer 3.7).
# Body (outline p.44): 1.45-1.75 x 2.75-3.05 -> 1.6 x 2.9 nominal.
# Pinouts (top view, 1-2-3 down the left, 5 top right, 4 bottom right):
#   TLV755P Figure 4-2 p.3 (IN 1, GND 2, EN 3, NC 4, OUT 5); SN74LVC1G08 DBV
#   p.3 (A 1, B 2, GND 3, Y 4, VCC 5); TPS2051B Figure 5-1 / Table 5-1 p.3
#   (OUT 1, GND 2, OC 3, EN 4, IN 5); AP2112 SOT25 p.1 (VIN 1, GND 2, EN 3,
#   NC 4, VOUT 5).
# Cross-check Diodes AP2112 DS39724 Rev. 2-2
#   (https://www.diodes.com/assets/Datasheets/AP2112.pdf) "Suggested Pad
#   Layout" SOT25, p.14: X 0.55, Y 0.80, C1 2.40, G 1.60, Z 3.20, C2 0.95.
#   Diodes pads are smaller and 0.1 mm further in per side; the TI land
#   contains them, so one footprint serves all four parts.
SOT23_5 = Footprint(
    "SOT23-5", "SOT-23-5 (TI DBV0005A), 0.95 mm pitch, 1.1 x 0.6 mm pads",
    row(["1", "2", "3"], -1.3, 0.95, 0, -0.95, 1.1, 0.6)
    + row(["4", None, "5"], 1.3, -0.95, 0, 0.95, 1.1, 0.6),
    body=(1.6, 2.9))

# --------------------------------------------------------------- SOT-23-6
# TI DBV0006A (SOT-23, 6 leads), drawing 4214840/G 08/2024.
#   SN74LVC2G17  SCES381N  https://www.ti.com/lit/ds/symlink/sn74lvc2g17.pdf
#     "DBV0006A EXAMPLE BOARD LAYOUT", p.31 (PACKAGE OUTLINE p.30); same
#     drawing in SN74LVC1G11 SCES487I p.22.
# Land: 6X (1.1) x (0.6), 2X (0.95) pitch, (2.6) column centres -> x = +/-1.3.
# Body: 1.45-1.75 x 2.75-3.05 -> 1.6 x 2.9.
# Pinouts (1-2-3 down the left, 6 opposite 1): SN74LVC2G17 DBV p.3 (1A 1,
#   GND 2, 2A 3, 2Y 4, VCC 5, 1Y 6); USBLC6-2SC6 Figure 1 p.1 (I/O1 1, GND 2,
#   I/O2 3, I/O2 4, VBUS 5, I/O1 6); 93LC46B SOT-23 (OT) p.2 (DO 1, VSS 2,
#   DI 3, CLK 4, CS 5, VCC 6).
# Cross-checks:
#   ST USBLC6-2 Doc ID 11265 Rev 5 (LCSC C7519,
#   https://datasheet.lcsc.com/datasheet/pdf/0d3a2ab954b34651a0695e7ccf534db0.pdf)
#   Figure 22 "SOT23-6L footprint" p.12: 0.60 x 1.20 pads, 0.95 pitch,
#   2.30 centres (1.10 gap, 3.50 overall) -> 0.1 mm longer pads, 0.15 mm
#   further in per side than TI.
#   Microchip 93LC46B DS20001749K
#   (https://ww1.microchip.com/downloads/en/DeviceDoc/20001749K.pdf)
#   "Recommended Land Pattern" C04-2028A, page 19: X 0.60, Y 1.10, C 2.80,
#   G 1.70, Z 3.90 -> same pad, 0.1 mm further out per side than TI.
#   All three overlap by >= 0.9 mm of pad length; the TI land is used.
SOT23_6 = Footprint(
    "SOT23-6", "SOT-23-6 (TI DBV0006A), 0.95 mm pitch, 1.1 x 0.6 mm pads",
    dual(6, 0.95, 2.6, 1.1, 0.6),
    body=(1.6, 2.9))

# --------------------------------------------------------------- SC70-6
# TI DCK0006A (SOT/SC70, 6 leads, JEDEC MO-203 AB), drawing 4214835/D 11/2024.
#   SN74LVC1G11  SCES487I  https://www.ti.com/lit/ds/symlink/sn74lvc1g11.pdf
#     "DCK0006A EXAMPLE BOARD LAYOUT", p.28 (PACKAGE OUTLINE p.27).
# Land: 6X (0.9) x (0.4), 4X (0.65) pitch, (2.2) column centres -> x = +/-1.1
# (inner gap 1.3, outer 3.1).
# Body: 1.1-1.4 x 1.85-2.15 -> 1.25 x 2.0.
# Pinout Figure 4-1 p.3: A 1, GND 2, B 3 down the left; Y 4, VCC 5, C 6 up
# the right.
SC70_6 = Footprint(
    "SC70-6", "SC70-6 / SOT-363 (TI DCK0006A), 0.65 mm pitch, 0.9 x 0.4 mm pads",
    dual(6, 0.65, 2.2, 0.9, 0.4),
    body=(1.25, 2.0))

# --------------------------------------------------------------- SOT-553-5
# TI DRL0005A (SOT, 5 leads, 0.6 mm max, JEDEC MO-293 UAAD-1), drawing
# 4220753/E 11/2024.
#   TPD2E001  SLLS684I  https://www.ti.com/lit/ds/symlink/tpd2e001.pdf
#     "DRL0005A EXAMPLE BOARD LAYOUT", p.22 (PACKAGE OUTLINE p.21); same
#     drawing in SN74LVC1G08 SCES217AA p.38.
# Land: 5X (0.67) x (0.3), 2X (0.5) pitch on the left, (1) between pads 5
# and 4 on the right (no middle pad), (1.48) column centres -> x = +/-0.74
# (copper x 0.405..1.075).
# Body: 1.1-1.3 x 1.5-1.7 -> 1.2 x 1.6.
# Pinout "DRL Package 5-Pin SOT Top View" p.3: VCC 1, N.C. 2, IO1 3 down the
# left; GND 4 bottom right, IO2 5 top right.
SOT553_5 = Footprint(
    "SOT553-5", "SOT-553 5-lead (TI DRL0005A), 0.5 mm pitch, 0.67 x 0.3 mm pads",
    row(["1", "2", "3"], -0.74, 0.5, 0, -0.5, 0.67, 0.3)
    + row(["4", None, "5"], 0.74, -0.5, 0, 0.5, 0.67, 0.3),
    body=(1.2, 1.6))

# --------------------------------------------------------------- SOT-563-6
# TI DRL0006A (SOT, 6 leads, 0.6 mm max, JEDEC MO-293 UAAD), drawing
# 4223266/F 11/2024.
#   TMP102  SBOS397I  https://www.ti.com/lit/ds/symlink/tmp102.pdf
#     "DRL0006A EXAMPLE BOARD LAYOUT", p.31 (PACKAGE OUTLINE p.30).
# Land: 6X (0.67) x (0.3), 4X (0.5) pitch, (1.48) column centres -> x = +/-0.74.
# Body: 1.1-1.3 x 1.5-1.7 -> 1.2 x 1.6.
# Pinout Figure 4-1 p.3: SCL 1, GND 2, ALERT 3 down the left; ADD0 4, V+ 5,
# SDA 6 up the right.
SOT563_6 = Footprint(
    "SOT563-6", "SOT-563 6-lead (TI DRL0006A), 0.5 mm pitch, 0.67 x 0.3 mm pads",
    dual(6, 0.5, 1.48, 0.67, 0.3),
    body=(1.2, 1.6))

# --------------------------------------------------------------- USON-10 DQA
# TI DQA (USON-10, 1 x 2.5 mm, 0.5 mm pitch).
#   TPD4E05U06  SLVSBO7O  https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf
#     "DQA0010A EXAMPLE BOARD LAYOUT", p.29 (4220328/A 12/2015, outline p.28)
#     and "DQA0010B EXAMPLE BOARD LAYOUT", p.32 (4230307/A 12/2023, outline
#     p.31). The datasheet carries both variants with the same DQA code.
# Land (identical in both): 10X (0.565) pad length along x, 8X (0.2) wide,
# pads 3 and 8 2X (0.4) wide, 4X (0.5) pitch, (0.835) between the column
# centres -> x = +/-0.4175 (inner gap 0.27, outer 1.40).
# DQA0010B additionally joins pads 3 and 8 with a (0.3)-wide bar across the
# centre (pad-centre span (0.8)) and an optional (D0.2) via: on the B package
# the two GND terminals are one strip. The bar is not drawn (two differently
# named pads cannot overlap in the pad check); pads 3 and 8 are both GND on
# this board, so route a short GND track between them if wanted. Without the
# bar the land is the DQA0010A pattern and also takes the B package.
# Body: 0.9-1.1 x 2.4-2.6 -> 1.0 x 2.5.
# Pinout Figure 4-3 p.4: D1+ 1, D1- 2, GND 3, D2+ 4, D2- 5 down the left;
# NC 6, NC 7, GND 8, NC 9, NC 10 up the right (10 opposite 1).
# silk_offset 0.1 moves the outline's top and bottom edges clear of pads 1/10
# and 5/6 so the ends of the part show on the legend.
USON10_DQA = Footprint(
    "USON10_DQA", "USON-10 1x2.5 mm (TI DQA0010A/B), 0.5 mm pitch",
    [smd(p.name, p.x, p.y, p.w, 0.4 if p.name in ("3", "8") else p.h)
     for p in dual(10, 0.5, 0.835, 0.565, 0.2)],
    body=(1.0, 2.5), silk_offset=0.1)

# --------------------------------------------------------------- X2SON-3 DMX
# TI DMX0003A (X2SON-3, 0.6 x 1.0 mm, 0.4 mm max), drawing 4223380/A 10/2016.
#   ESD122  SLVSDP5A  https://www.ti.com/lit/ds/symlink/esd122.pdf
#     "DMX0003A EXAMPLE BOARD LAYOUT", p.25 (PACKAGE OUTLINE p.24).
# Land: 3X (0.2 square) pads; (0.3) in x between pad 1 and the pad 2/3 column,
# split evenly about PKG centreline -> pad 1 at x = -0.15, pads 2/3 at
# x = +0.15; (0.68) between pads 3 and 2 -> y = +/-0.34 (outline: basic 2X 0.3
# and 0.68). Pad 1 sits on the SYMM line (y = 0).
# The layout view is used as drawn: pad 1 alone on the left, 3 top right,
# 2 bottom right. That is the top-view pinout of section 5 p.3 (IO2 3 top
# left, IO1 2 top right, GND 1 bottom centre) turned 90 deg clockwise, so pin 1
# is on the left as in IPC zero orientation for a 3-terminal part.
# Body: 0.5-0.7 x 0.9-1.1 -> 0.6 x 1.0 (long side along y in this view).
X2SON3_DMX = Footprint(
    "X2SON3_DMX", "X2SON-3 0.6x1.0 mm (TI DMX0003A), 0.2 mm square pads",
    [smd("1", -0.15, 0, 0.2, 0.2), smd("2", 0.15, -0.34, 0.2, 0.2), smd("3", 0.15, 0.34, 0.2, 0.2)],
    body=(0.6, 1.0))

# --------------------------------------------------------------- X1SON-2 DPY
# TI DPY0002A (X1SON-2, 1.0 x 0.6 mm, 0.45 mm max), drawing 4224561/C 07/2024.
#   TPD1E10B06  SLLSEB1G  https://www.ti.com/lit/ds/symlink/tpd1e10b06.pdf
#     "DPY0002A EXAMPLE BOARD LAYOUT", p.28 (PACKAGE OUTLINE p.27); the same
#     drawing revision is in TPD4E05U06 SLVSBO7O (TPD1E05U06 DPY).
# Land: 2X (0.3) along x x (0.5) along y, (0.7) between pad centres ->
# x = +/-0.35, gap 0.4.
# Body: 0.9-1.1 x 0.5-0.7 -> 1.0 x 0.6. Pad 1 left (pin 1 index area on the
# left in the outline). Bidirectional TVS used through the generic TVS_BI
# symbol (pins "1"/"2"): no polarity marker, and no legend at 0402 size.
X1SON2_DPY = Footprint(
    "X1SON2_DPY", "X1SON-2 1.0x0.6 mm (TI DPY0002A), bidirectional, 0.3 x 0.5 mm pads",
    chip(0.3, 0.5, 0.4),
    body=(1.0, 0.6), marker="none", silk=False)

FOOTPRINTS = [SOT23_3, SOT23_5, SOT23_6, SC70_6, SOT553_5, SOT563_6, USON10_DQA, X2SON3_DMX, X1SON2_DPY]
