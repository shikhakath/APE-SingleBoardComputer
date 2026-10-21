"""Symbols for sheets 10 (HDMI), 11 (audio) and 12 (camera).

Every pin table below was read from the manufacturer document named above the
symbol (downloaded 2026-10-17, text extracted with pdftotext/PyMuPDF, pin
diagrams cross-checked against the pin tables). Thermal pads get the next free
pin number; connector shells/tabs are listed as pins so the footprint maps.
"""
from schgen import box

# ------------------------------------------------------------ HDMI (sheet 10)

# TI TFP410PAPR, HTQFP-64 PowerPAD (PAP).
# https://www.ti.com/lit/ds/symlink/tfp410.pdf (SLDS145D, Feb 2024)
# Figure 4-1 (pinout, top view) + Table 4-1 Pin Functions p.3-5. PowerPAD = pin 65
# (TI numbers it 65 in Figure 7-3). DATA[11:0] = pins 63..58, 55..50 (DATA0 = 63,
# DATA5 = 58, IDCK+ = 57, IDCK- = 56, DATA6 = 55, DATA11 = 50); DATA[23:12] =
# pins 36..47 (DATA23 = 36, DATA12 = 47). Split in two parts: A = video input and
# straps, B = supplies and DVI outputs.
TFP410 = box("TFP410_PAP", "TI TFP410 DVI 1.0 transmitter, 24-bit DPI in, HTQFP-64 PowerPAD", [
    # part A: pixel bus
    (63, "DATA0", "in", "L", 1), (62, "DATA1", "in", "L", 1), (61, "DATA2", "in", "L", 1),
    (60, "DATA3", "in", "L", 1), (59, "DATA4", "in", "L", 1), (58, "DATA5", "in", "L", 1),
    (55, "DATA6", "in", "L", 1), (54, "DATA7", "in", "L", 1), (53, "DATA8", "in", "L", 1),
    (52, "DATA9", "in", "L", 1), (51, "DATA10", "in", "L", 1), (50, "DATA11", "in", "L", 1),
    (47, "DATA12", "in", "L", 1), (46, "DATA13", "in", "L", 1), (45, "DATA14", "in", "L", 1),
    (44, "DATA15", "in", "L", 1), (43, "DATA16", "in", "L", 1), (42, "DATA17", "in", "L", 1),
    (41, "DATA18", "in", "L", 1), (40, "DATA19", "in", "L", 1), (39, "DATA20", "in", "L", 1),
    (38, "DATA21", "in", "L", 1), (37, "DATA22", "in", "L", 1), (36, "DATA23", "in", "L", 1),
    # part A: clock, sync, configuration
    (57, "IDCK+", "in", "R", 1), (56, "IDCK-", "in", "R", 1),
    (2, "DE", "in", "R", 1), (4, "HSYNC", "in", "R", 1), (5, "VSYNC", "in", "R", 1),
    ("", "", "pas", "R", 1),
    (13, "ISEL/RST", "in", "R", 1), (15, "BSEL/SCL", "in", "R", 1), (14, "DSEL/SDA", "io", "R", 1),
    (9, "EDGE/HTPLG", "in", "R", 1), (35, "DKEN", "in", "R", 1),
    (6, "A3/DK3", "in", "R", 1), (7, "CTL2/A2/DK2", "in", "R", 1), (8, "CTL1/A1/DK1", "in", "R", 1),
    (3, "VREF", "in", "R", 1), (10, "nPD", "in", "R", 1), (11, "MSEN/PO1", "oc", "R", 1),
    (34, "RESERVED", "in", "R", 1), (49, "NC", "pas", "R", 1),
    # part B: supplies
    (1, "DVDD", "pwr", "L", 2), (12, "DVDD", "pwr", "L", 2), (33, "DVDD", "pwr", "L", 2),
    (18, "PVDD", "pwr", "L", 2), (23, "TVDD", "pwr", "L", 2), (29, "TVDD", "pwr", "L", 2),
    ("", "", "pas", "L", 2),
    (16, "DGND", "pwr", "L", 2), (48, "DGND", "pwr", "L", 2), (64, "DGND", "pwr", "L", 2),
    (17, "PGND", "pwr", "L", 2), (20, "TGND", "pwr", "L", 2), (26, "TGND", "pwr", "L", 2),
    (32, "TGND", "pwr", "L", 2), (65, "EP", "pas", "L", 2),
    # part B: DVI outputs
    (25, "TX0+", "out", "R", 2), (24, "TX0-", "out", "R", 2),
    (28, "TX1+", "out", "R", 2), (27, "TX1-", "out", "R", 2),
    (31, "TX2+", "out", "R", 2), (30, "TX2-", "out", "R", 2),
    (22, "TXC+", "out", "R", 2), (21, "TXC-", "out", "R", 2),
    ("", "", "pas", "R", 2),
    (19, "TFADJ", "pas", "R", 2),
], part_count=2, footprint="HTQFP64_PAP_10X10")

# TI TPD12S016PWR, TSSOP-24 (PW), no thermal pad.
# https://www.ti.com/lit/ds/symlink/tpd12s016.pdf (SLLSE96F, Oct 2015)
# Section 5 Pin Configuration (PW top view) + Pin Functions table p.4, PW column.
TPD12S016 = box("TPD12S016_PW", "TI TPD12S016 HDMI companion: 5 V load switch, DDC/CEC/HPD level shift, 12-ch ESD, TSSOP-24", [
    (24, "VCCA", "pwr", "L"), (11, "VCC5V", "pwr", "L"),
    (12, "CT_HPD", "in", "L"), (5, "LS_OE", "in", "L"),
    ("", "", "pas", "L"),
    (2, "SCL_A", "io", "L"), (3, "SDA_A", "io", "L"), (4, "HPD_A", "out", "L"), (1, "CEC_A", "io", "L"),
    ("", "", "pas", "L"),
    (6, "GND", "pwr", "L"), (14, "GND", "pwr", "L"), (19, "GND", "pwr", "L"),
    (13, "5V_OUT", "pwr", "R"),
    ("", "", "pas", "R"),
    (8, "SCL_B", "io", "R"), (9, "SDA_B", "io", "R"), (10, "HPD_B", "in", "R"), (7, "CEC_B", "io", "R"),
    ("", "", "pas", "R"),
    (23, "D2+", "pas", "R"), (22, "D2-", "pas", "R"), (21, "D1+", "pas", "R"), (20, "D1-", "pas", "R"),
    (18, "D0+", "pas", "R"), (17, "D0-", "pas", "R"), (16, "CLK+", "pas", "R"), (15, "CLK-", "pas", "R"),
], footprint="TSSOP24_4.4X7.8_P0.65")

# XFCN HDMI-A-19F-S-D, HDMI type-A receptacle, 19 SMT contacts at 0.5 mm + 4 THT shell legs.
# Drawing via LCSC C5151728: https://www.lcsc.com/datasheet/C5151728.pdf (XFCN rev A1, 2025-11-19).
# The drawing does not number the contacts: pins 1..19 follow the HDMI 1.4 type-A
# numbering (same order as the SK J5 / Amphenol 10029449), shell legs = 20..23.
# Check the footprint pad numbers against this before layout.
HDMI_A = box("HDMI_A_RECEPT", "HDMI type-A receptacle, 19 pin + shell (XFCN HDMI-A-19F-S-D)", [
    (1, "TMDS_D2+", "pas", "L"), (2, "D2_SHIELD", "pas", "L"), (3, "TMDS_D2-", "pas", "L"),
    (4, "TMDS_D1+", "pas", "L"), (5, "D1_SHIELD", "pas", "L"), (6, "TMDS_D1-", "pas", "L"),
    (7, "TMDS_D0+", "pas", "L"), (8, "D0_SHIELD", "pas", "L"), (9, "TMDS_D0-", "pas", "L"),
    (10, "TMDS_CLK+", "pas", "L"), (11, "CLK_SHIELD", "pas", "L"), (12, "TMDS_CLK-", "pas", "L"),
    (13, "CEC", "pas", "L"), (14, "UTILITY", "pas", "L"), (15, "SCL", "pas", "L"), (16, "SDA", "pas", "L"),
    (17, "DDC/CEC_GND", "pas", "L"), (18, "+5V", "pas", "L"), (19, "HPD", "pas", "L"),
    (20, "SHELL", "pas", "R"), (21, "SHELL", "pas", "R"), (22, "SHELL", "pas", "R"), (23, "SHELL", "pas", "R"),
], prefix="J", footprint="HDMI_A_XFCN_19F_S_D")

# ------------------------------------------------------------ audio (sheet 11)

# TI TLV320AIC3104IRHBR, VQFN-32 5x5 (RHB).
# https://www.ti.com/lit/ds/symlink/tlv320aic3104.pdf (SLAS510G, Feb 2021)
# Figure 7-1 (RHB pinout) + Table 7-1 Pin Functions p.5-6. Thermal pad = pin 33,
# "connect device thermal pad to DRVSS" (Figure 7-1 note). No SELECT/MFP pins:
# the I2C address is fixed at 0011000 = 0x18 (section 10.5.1 I2C Control Interface).
AIC3104 = box("TLV320AIC3104_RHB", "TI TLV320AIC3104 low-power stereo codec, I2S + I2C, VQFN-32", [
    (1, "MCLK", "in", "L"), (2, "BCLK", "io", "L"), (3, "WCLK", "io", "L"),
    (4, "DIN", "in", "L"), (5, "DOUT", "out", "L"),
    ("", "", "pas", "L"),
    (8, "SCL", "io", "L"), (9, "SDA", "io", "L"), (31, "nRESET", "in", "L"),
    ("", "", "pas", "L"),
    (7, "IOVDD", "pwr", "L"), (32, "DVDD", "pwr", "L"), (25, "AVDD", "pwr", "L"),
    (18, "DRVDD", "pwr", "L"), (24, "DRVDD", "pwr", "L"),
    ("", "", "pas", "L"),
    (6, "DVSS", "pwr", "L"), (17, "AVSS1", "pwr", "L"), (26, "AVSS2", "pwr", "L"),
    (21, "DRVSS", "pwr", "L"), (33, "EP", "pas", "L"),
    (10, "MIC1LP/LINE1LP", "in", "R"), (11, "MIC1LM/LINE1LM", "in", "R"),
    (12, "MIC1RP/LINE1RP", "in", "R"), (13, "MIC1RM/LINE1RM", "in", "R"),
    (14, "MIC2L/LINE2L/MICDET", "in", "R"), (16, "MIC2R/LINE2R", "in", "R"),
    (15, "MICBIAS", "out", "R"),
    ("", "", "pas", "R"),
    (19, "HPLOUT", "out", "R"), (20, "HPLCOM", "out", "R"),
    (23, "HPROUT", "out", "R"), (22, "HPRCOM", "out", "R"),
    ("", "", "pas", "R"),
    (27, "LEFT_LOP", "out", "R"), (28, "LEFT_LOM", "out", "R"),
    (29, "RIGHT_LOP", "out", "R"), (30, "RIGHT_LOM", "out", "R"),
], footprint="VQFN32_RHB_5X5")

# SJK 3N12288G33YC, 12.288 MHz LVCMOS oscillator, SMD3225-4.
# https://www.lcsc.com/datasheet/C252334.pdf (SJK series 3N spec, p.3 "PAD FUNCTION").
# 1 = enable control (logic 1 or open = output on), 2 = GND, 3 = OUT, 4 = VDD.
OSC_3225 = box("OSC_3225_OE", "LVCMOS oscillator with output enable, 3.2x2.5 mm 4-pad", [
    (4, "VDD", "pwr", "L"), (1, "OE", "in", "L"), (2, "GND", "pwr", "L"),
    (3, "OUT", "out", "R"),
], prefix="Y", footprint="OSC_3225_4P")

# Korean Hroparts PJ-320DB-5A (drawing PJ-320DB, variant -A), 3.5 mm 4-pole SMD jack.
# https://www.lcsc.com/datasheet/C707225.pdf (single-sheet drawing, "Schematic" table + PCB layout).
# Contact roles read from the schematic and pad positions: pin 1 = sleeve (contact
# at the mouth, tab at the rear), 2 = tip (deepest spring), 3 = ring 1, 4 = ring 2,
# 5 = "dummy" (mechanical tab). Same numbering as the SK's CUI SJ-43514 (J12).
# No detect switch on this jack.
JACK_TRRS = box("JACK_TRRS_PJ320DB", "3.5 mm TRRS jack, SMD, no switch (PJ-320DB-5A)", [
    (2, "TIP", "pas", "L"), (3, "RING1", "pas", "L"), (4, "RING2", "pas", "L"), (1, "SLEEVE", "pas", "L"),
    (5, "DUMMY", "pas", "L"),
], prefix="J", footprint="JACK_HRO_PJ-320DB")

# ------------------------------------------------------------ camera (sheet 12)

# TE 1-1734248-5, 15-position 1.0 mm FPC, ZIF vertical, SMT (customer drawing C-1734248 rev E1,
# via LCSC C2922285: https://www.lcsc.com/datasheet/C2922285.pdf). Circuits 1..15 as marked
# "CIRCUIT NO.1" on the drawing. Each circuit has two SMT tails (two pad rows in the
# recommended PCB layout; the SK J19 calls them nA/nB); give both pads of circuit n the
# pad number n. Signal names = Raspberry Pi 15-pin camera connector (as SK J19).
FPC15_CSI = box("FPC15_RPI_CSI", "15-pin 1.0 mm FPC, Raspberry Pi camera pinout (TE 1-1734248-5)", [
    (1, "GND", "pas", "L"), (2, "CAM_D0_N", "pas", "L"), (3, "CAM_D0_P", "pas", "L"),
    (4, "GND", "pas", "L"), (5, "CAM_D1_N", "pas", "L"), (6, "CAM_D1_P", "pas", "L"),
    (7, "GND", "pas", "L"), (8, "CAM_CK_N", "pas", "L"), (9, "CAM_CK_P", "pas", "L"),
    (10, "GND", "pas", "L"), (11, "CAM_IO0", "pas", "L"), (12, "CAM_IO1", "pas", "L"),
    (13, "CAM_SCL", "pas", "L"), (14, "CAM_SDA", "pas", "L"), (15, "CAM_3V3", "pas", "L"),
], prefix="J", footprint="FPC_TE_1-1734248-5")

SYMBOLS = [TFP410, TPD12S016, HDMI_A, AIC3104, OSC_3225, JACK_TRRS, FPC15_CSI]
