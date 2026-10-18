"""Symbols for sheet 01 (USB-C #1 power input, USB-PD sink, 3.3 V buck, 5 V buck-boost).

Every pin table below was extracted from the manufacturer datasheet named in the
comment above the symbol (pdftotext -layout / PyMuPDF render, 2026-10-17), not
from memory. Thermal pads are separate pins with the next free number.
"""
from schgen import box

# ------------------------------------------------------------ USB-C receptacle
# Korean Hroparts Elec TYPE-C-31-M-12 (LCSC C165948), USB 2.0 16-contact, SMD
# right-angle, 4 THT shell pegs. Drawing "TYPE-C-31-M-12", sheet 1 of 1
# (2020-12-08): https://datasheet.lcsc.com/datasheet/pdf/9e56b777c022540fcce7c7f67825f55e.pdf?productCode=C165948
# Pin/signal table (lower right of the drawing) and "RECOMMEND P.C.B LAYOUT":
#   12 SMD pads. Four pads are shared by two contacts and are labelled
#   "A1/B12", "A4/B9", "B4/A9", "B1/A12" on the drawing; here they are pin
#   numbers A1B12, A4B9, B4A9, B1A12 (slash dropped). The other eight pads carry
#   one contact each: A5 CC1, A6 DP1, A7 DN1, A8 SBU1, B5 CC2, B6 DP2, B7 DN2,
#   B8 SBU2.
#   Shell: 4 plated oval slots (two 0.60 x 2.00/1.70 front, two 0.60 x 1.40/1.70
#   rear); the drawing does not number them, so they are S1/S2 (front) and
#   S3/S4 (rear). The two 0.60 mm round holes are non-plated locating posts (no pin).
TYPE_C_31_M_12 = box("TYPE-C-31-M-12", "USB Type-C receptacle, USB 2.0 16-contact, SMD R/A, 4 THT shell pegs", [
    ("A1B12", "GND", "pas", "L"),
    ("B1A12", "GND", "pas", "L"),
    ("", "", "pas", "L"),
    ("S1", "SHIELD", "pas", "L"),
    ("S2", "SHIELD", "pas", "L"),
    ("S3", "SHIELD", "pas", "L"),
    ("S4", "SHIELD", "pas", "L"),
    ("A4B9", "VBUS", "pas", "R"),
    ("B4A9", "VBUS", "pas", "R"),
    ("", "", "pas", "R"),
    ("A5", "CC1", "pas", "R"),
    ("B5", "CC2", "pas", "R"),
    ("", "", "pas", "R"),
    ("A6", "DP1", "pas", "R"),
    ("B6", "DP2", "pas", "R"),
    ("A7", "DN1", "pas", "R"),
    ("B7", "DN2", "pas", "R"),
    ("", "", "pas", "R"),
    ("A8", "SBU1", "pas", "R"),
    ("B8", "SBU2", "pas", "R"),
], prefix="J", footprint="USB-C_HRO_TYPE-C-31-M-12")

# ------------------------------------------------------------ VBUS clamp
# TI TVS2200 DRV (WSON-6 2x2), https://www.ti.com/lit/ds/symlink/tvs2200.pdf
# Figure 6-1 / Table 6-1 (p.3): pins 1-3 GND, 4-6 IN, exposed thermal pad = GND
# (drawn as "7" in Figure 6-1, used here as pin 7).
TVS2200 = box("TVS2200_DRV", "TVS2200 22 V flat-clamp surge protection, WSON-6 2x2", [
    (4, "IN", "pas", "L"),
    (5, "IN", "pas", "L"),
    (6, "IN", "pas", "L"),
    (1, "GND", "pwr", "R"),
    (2, "GND", "pwr", "R"),
    (3, "GND", "pwr", "R"),
    (7, "EP", "pas", "R"),
], prefix="D", footprint="WSON6_DRV_2X2")

# ------------------------------------------------------------ USB-PD sink
# TI TPS25730D, REF package (WQFN-38 4x6), https://www.ti.com/lit/ds/symlink/tps25730.pdf
# (SLVSGP9, Oct 2023) Figure 5-1 (p.4) and Table 5-1 TPS25730D Pin Functions (p.5-6).
# Two thermal pads: GND pad = pin 39, DRAIN pad = pin 40 (numbering as in the
# datasheet's own Figure 9-3 example schematic, "GND_PAD 39" / "DRAIN_PAD 40").
# TPS25730ADREFR (A revision) is pin-compatible (BOM ALT row).
TPS25730D = box("TPS25730D_REF", "TPS25730D USB-C PD sink controller, 5 A integrated power path, WQFN-38 REF", [
    (23, "VBUS_IN", "pwr", "L"),
    (24, "VBUS_IN", "pwr", "L"),
    (25, "VBUS_IN", "pwr", "L"),
    (32, "VBUS", "pwr", "L"),
    (33, "VBUS", "pwr", "L"),
    ("", "", "pas", "L"),
    (38, "VIN_3V3", "pwr", "L"),
    (1, "LDO_3V3", "pas", "L"),
    (4, "LDO_1V5", "pas", "L"),
    ("", "", "pas", "L"),
    (2, "ADCIN1", "in", "L"),
    (3, "ADCIN2", "in", "L"),
    (5, "ADCIN3", "in", "L"),
    (7, "ADCIN4", "in", "L"),
    ("", "", "pas", "L"),
    (26, "RESERVED", "in", "L"),
    (27, "RESERVED", "in", "L"),
    (36, "RESERVED", "in", "L"),
    ("", "", "pas", "L"),
    (11, "GND", "pwr", "L"),
    (12, "GND", "pwr", "L"),
    (14, "GND", "pwr", "L"),
    (16, "GND", "pwr", "L"),
    (17, "GND", "pwr", "L"),
    (31, "GND", "pwr", "L"),
    (34, "GND", "pwr", "L"),
    (35, "GND", "pwr", "L"),
    (39, "GND_PAD", "pwr", "L"),
    (20, "PPHV", "pas", "R"),
    (21, "PPHV", "pas", "R"),
    (22, "PPHV", "pas", "R"),
    ("", "", "pas", "R"),
    (15, "DRAIN", "pas", "R"),
    (30, "DRAIN", "pas", "R"),
    (40, "DRAIN_PAD", "pas", "R"),
    ("", "", "pas", "R"),
    (28, "CC1", "io", "R"),
    (29, "CC2", "io", "R"),
    ("", "", "pas", "R"),
    (9, "I2Ct_SCL", "in", "R"),
    (8, "I2Ct_SDA", "io", "R"),
    ("", "", "pas", "R"),
    (18, "nFAULT_IN", "in", "R"),
    (19, "nSINK_EN", "oc", "R"),
    (6, "CAP_MIS", "oc", "R"),
    (37, "PLUG_EVENT", "oc", "R"),
    (13, "PLUG_FLIP", "oc", "R"),
    (10, "DBG_ACC", "oc", "R"),
], footprint="WQFN38_REF_4X6")

# ------------------------------------------------------------ 3.3 V buck
# TI LM61460 RJR (VQFN-HR-14 3.5x4), https://www.ti.com/lit/ds/symlink/lm61460.pdf
# (SNVSBD5D, Jul 2022) Figure 6-1 / Table 6-1 Pin Functions (p.3). No exposed
# pad on this HotRod package. LM61460AANRJRR = adjustable Vout, RT-set
# frequency, auto (PFM) light-load mode (Section 5 Device Comparison Table).
LM61460 = box("LM61460_RJR", "LM61460 36 V 6 A synchronous buck, adjustable, VQFN-HR-14 RJR", [
    (8, "VIN1", "pwr", "L"),
    (12, "VIN2", "pwr", "L"),
    ("", "", "pas", "L"),
    (7, "EN/SYNC", "in", "L"),
    (6, "RT", "pas", "L"),
    ("", "", "pas", "L"),
    (1, "BIAS", "pwr", "L"),
    (2, "VCC", "pas", "L"),
    ("", "", "pas", "L"),
    (3, "AGND", "pwr", "L"),
    (9, "PGND1", "pwr", "L"),
    (11, "PGND2", "pwr", "L"),
    (10, "SW", "pas", "R"),
    (14, "CBOOT", "pas", "R"),
    (13, "RBOOT", "pas", "R"),
    ("", "", "pas", "R"),
    (4, "FB", "in", "R"),
    (5, "PGOOD", "oc", "R"),
], footprint="VQFN-HR14_RJR_3P5X4")

# ------------------------------------------------------------ 5 V buck-boost
# TI TPS63070 RNM (VQFN-HR-15 2.5x3), https://www.ti.com/lit/ds/symlink/tps63070.pdf
# (SLVSC58B, Mar 2019) Section 6 Pin Configuration and Pin Functions table (p.3).
# No exposed pad. TPS63070 = adjustable output, no output discharge (Section 5).
TPS63070 = box("TPS63070_RNM", "TPS63070 2-16 V 3.6 A buck-boost, adjustable, VQFN-HR-15 RNM", [
    (12, "VIN", "pwr", "L"),
    (13, "VIN", "pwr", "L"),
    ("", "", "pas", "L"),
    (14, "EN", "in", "L"),
    (1, "PS/SYNC", "in", "L"),
    (15, "VSEL", "in", "L"),
    (3, "VAUX", "pas", "L"),
    ("", "", "pas", "L"),
    (4, "GND", "pwr", "L"),
    (10, "PGND", "pwr", "L"),
    (11, "L1", "pas", "R"),
    (9, "L2", "pas", "R"),
    ("", "", "pas", "R"),
    (7, "VOUT", "pas", "R"),
    (8, "VOUT", "pas", "R"),
    ("", "", "pas", "R"),
    (5, "FB", "in", "R"),
    (6, "FB2", "pas", "R"),
    (2, "PG", "oc", "R"),
], footprint="VQFN-HR15_RNM_2P5X3")

SYMBOLS = [TYPE_C_31_M_12, TVS2200, TPS25730D, LM61460, TPS63070]
